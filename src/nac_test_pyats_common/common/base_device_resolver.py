"""Base device resolver for SSH/D2D testing.

Provides the Template Method pattern for device inventory resolution.
Architecture-specific resolvers extend this class and implement the
abstract methods for schema navigation and credential retrieval.
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Any

import yaml
from nac_test.utils.file_discovery import find_data_file

logger = logging.getLogger(__name__)


class BaseDeviceResolver(ABC):
    """Abstract base class for architecture-specific device resolvers.

    This class implements the Template Method pattern for device inventory
    resolution. It handles common logic (inventory loading, credential
    injection, device dict construction) while delegating schema-specific
    work to abstract methods.

    Subclasses MUST implement:
        - get_architecture_name(): Return architecture identifier (e.g., "sdwan")
        - get_schema_root_key(): Return the root key in data model (e.g., "sdwan")
        - navigate_to_devices(): Navigate schema to get iterable of device data
        - extract_device_id(): Extract unique device identifier from device data
        - extract_hostname(): Extract hostname from device data
        - extract_host_ip(): Extract management IP from device data
        - extract_os_type(): Extract OS type from device data
        - get_credential_env_vars(): Return (username_env_var, password_env_var)

    Subclasses MAY override:
        - get_inventory_filename(): Return inventory filename (default: "test_inventory.yaml")
        - build_device_dict(): Customize device dict construction
        - _load_inventory(): Customize inventory loading

    Attributes:
        data_model: The merged NAC data model dictionary.
        test_inventory: The test inventory dictionary (devices to test).

    Example:
        >>> class SDWANDeviceResolver(BaseDeviceResolver):
        ...     def get_architecture_name(self) -> str:
        ...         return "sdwan"
        ...
        ...     def get_schema_root_key(self) -> str:
        ...         return "sdwan"
        ...
        ...     # ... implement other abstract methods ...
        >>>
        >>> resolver = SDWANDeviceResolver(data_model)
        >>> devices = resolver.get_resolved_inventory()
    """

    def __init__(
        self,
        data_model: dict[str, Any],
        test_inventory: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the device resolver.

        Args:
            data_model: The merged NAC data model containing all architecture
                data with resolved variables.
            test_inventory: Optional test inventory specifying which devices
                to test. If not provided, will attempt to load from file.
        """
        self.data_model = data_model
        self.test_inventory = test_inventory or self._load_inventory()
        logger.debug(
            f"Initialized {self.get_architecture_name()} resolver with "
            f"{len(self.test_inventory.get('devices', []))} devices in inventory"
        )

    def get_resolved_inventory(self) -> list[dict[str, Any]]:
        """Get resolved device inventory ready for SSH connection.

        This is the main entry point. It:
        1. Navigates the data model to find device data
        2. Matches devices against test inventory (if provided)
        3. Extracts hostname, IP, OS from each device
        4. Injects SSH credentials from environment variables
        5. Returns list of device dicts ready for nac-test

        Returns:
            List of device dictionaries with all required fields:
            - hostname (str)
            - host (str)
            - os (str)
            - username (str)
            - password (str)
            - Plus any architecture-specific fields

        Raises:
            ValueError: If credential environment variables are not set.
        """
        logger.info(f"Resolving device inventory for {self.get_architecture_name()}")

        resolved_devices: list[dict[str, Any]] = []
        devices_to_test = self._get_devices_to_test()

        for device_data in devices_to_test:
            try:
                device_dict = self.build_device_dict(device_data)

                # Validate extracted fields
                if not device_dict.get("hostname"):
                    raise ValueError("hostname is empty or missing")
                if not device_dict.get("host"):
                    raise ValueError("host (IP address) is empty or missing")
                if not device_dict.get("os"):
                    raise ValueError("os type is empty or missing")
                if not device_dict.get("device_id"):
                    raise ValueError("device_id is empty or missing")

                resolved_devices.append(device_dict)
                logger.debug(
                    f"Resolved device: {device_dict['hostname']} "
                    f"({device_dict['host']}, {device_dict['os']})"
                )
            except (KeyError, ValueError) as e:
                device_id = self._safe_extract_device_id(device_data)
                logger.warning(f"Skipping device {device_id}: {e}")
                continue

        # Inject credentials (fail fast if missing)
        self._inject_credentials(resolved_devices)

        logger.info(
            f"Resolved {len(resolved_devices)} devices for "
            f"{self.get_architecture_name()} D2D testing"
        )
        return resolved_devices

    def build_device_dict(self, device_data: dict[str, Any]) -> dict[str, Any]:
        """Build a device dictionary from raw device data.

        Override this method to customize device dict construction
        for your architecture.

        Args:
            device_data: Raw device data from the data model.

        Returns:
            Device dictionary with hostname, host, os, device_id fields,
            plus any test-relevant fields like connection_options.
            Credentials are injected separately.

        Raises:
            ValueError: If any required field extraction fails.
        """
        hostname = self.extract_hostname(device_data)
        host = self.extract_host_ip(device_data)
        os_type = self.extract_os_type(device_data)
        device_id = self.extract_device_id(device_data)

        # Validate all extracted values are non-empty strings
        if not isinstance(hostname, str) or not hostname:
            raise ValueError(f"Invalid hostname: {hostname!r}")
        if not isinstance(host, str) or not host:
            raise ValueError(f"Invalid host IP: {host!r}")
        if not isinstance(os_type, str) or not os_type:
            raise ValueError(f"Invalid OS type: {os_type!r}")
        if not isinstance(device_id, str) or not device_id:
            raise ValueError(f"Invalid device ID: {device_id!r}")

        # Start with required fields
        result = {
            "hostname": hostname,
            "host": host,
            "os": os_type,
            "device_id": device_id,
        }

        # Preserve connection_options from test_inventory if present
        # This allows specifying custom SSH ports, protocols, etc.
        if "connection_options" in device_data:
            result["connection_options"] = device_data["connection_options"]

        return result

    # -------------------------------------------------------------------------
    # Private helper methods
    # -------------------------------------------------------------------------

    def _load_inventory(self) -> dict[str, Any]:
        """Load test inventory from file.

        Searches for the inventory file using the generic file discovery
        utility. Subclasses can override this to customize loading behavior.

        Returns:
            Test inventory dictionary, or empty dict if not found.
        """
        filename = self.get_inventory_filename()
        inventory_path = find_data_file(filename)

        if inventory_path is None:
            logger.warning(
                f"Test inventory file '{filename}' not found for "
                f"{self.get_architecture_name()}. Using empty inventory."
            )
            return {}

        logger.info(f"Loading test inventory from {inventory_path}")
        try:
            with open(inventory_path) as f:
                raw_data = yaml.safe_load(f) or {}

            # Support both nested and flat formats:
            # Nested: {arch: {test_inventory: {...}}}
            # Flat: {test_inventory: {...}}
            arch_key = self.get_schema_root_key()
            if arch_key in raw_data and "test_inventory" in raw_data[arch_key]:
                return raw_data[arch_key]["test_inventory"]  # type: ignore[no-any-return]
            elif "test_inventory" in raw_data:
                return raw_data["test_inventory"]  # type: ignore[no-any-return]
            else:
                return raw_data

        except yaml.YAMLError as e:
            logger.error(f"Failed to parse test inventory YAML: {e}")
            return {}
        except OSError as e:
            logger.error(f"Failed to read test inventory file: {e}")
            return {}

    def _get_devices_to_test(self) -> list[dict[str, Any]]:
        """Get the list of device data dicts to process.

        If test_inventory specifies devices, filter to only those.
        Otherwise, return all devices from the data model.

        Returns:
            List of device data dictionaries from the data model.
        """
        all_devices = list(self.navigate_to_devices())
        logger.debug(f"Found {len(all_devices)} total devices in data model")

        # If no test inventory, test all devices
        inventory_devices = self.test_inventory.get("devices", [])
        if not inventory_devices:
            logger.debug("No test inventory devices specified, testing all devices")
            return all_devices

        # Build index for efficient lookup
        device_index = self._build_device_index(all_devices)

        # Filter to devices in test inventory
        devices_to_test: list[dict[str, Any]] = []
        for inventory_entry in inventory_devices:
            device_id = self._get_device_id_from_inventory(inventory_entry)
            if device_id in device_index:
                # Merge inventory entry data with device data
                merged = {**device_index[device_id], **inventory_entry}
                devices_to_test.append(merged)
                logger.debug(f"Added device {device_id} from test inventory")
            else:
                logger.warning(
                    f"Device '{device_id}' from test_inventory not found in "
                    f"{self.get_architecture_name()} data model"
                )

        logger.debug(f"Filtered to {len(devices_to_test)} devices from test inventory")
        return devices_to_test

    def _build_device_index(self, devices: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """Build a lookup index of devices by their ID.

        Args:
            devices: List of device data dictionaries.

        Returns:
            Dictionary mapping device ID to device data.
        """
        device_index: dict[str, dict[str, Any]] = {}
        for device_data in devices:
            device_id = self._safe_extract_device_id(device_data)
            if device_id:
                device_index[device_id] = device_data
        return device_index

    def _get_device_id_from_inventory(self, inventory_entry: dict[str, Any]) -> str:
        """Extract device ID from a test inventory entry.

        Override this if your inventory uses a different field name.

        Args:
            inventory_entry: Entry from test_inventory.devices[]

        Returns:
            Device identifier string.
        """
        # Common patterns across architectures
        for key in ["chassis_id", "device_id", "node_id", "hostname", "name"]:
            if key in inventory_entry:
                return str(inventory_entry[key])

        logger.warning(f"Could not extract device ID from inventory entry: {inventory_entry}")
        return ""

    def _safe_extract_device_id(self, device_data: dict[str, Any]) -> str:
        """Safely extract device ID, returning empty string on failure."""
        try:
            return self.extract_device_id(device_data)
        except (KeyError, ValueError):
            return "<unknown>"

    def _inject_credentials(self, devices: list[dict[str, Any]]) -> None:
        """Inject SSH credentials from environment variables.

        Args:
            devices: List of device dicts to update in place.

        Raises:
            ValueError: If required credential environment variables are not set.
        """
        username_var, password_var = self.get_credential_env_vars()
        username = os.environ.get(username_var)
        password = os.environ.get(password_var)

        # FAIL FAST - raise error if credentials missing
        missing_vars: list[str] = []
        if not username:
            missing_vars.append(username_var)
        if not password:
            missing_vars.append(password_var)

        if missing_vars:
            raise ValueError(
                f"Missing required credential environment variables: {', '.join(missing_vars)}. "
                f"These are required for {self.get_architecture_name()} D2D testing."
            )

        logger.debug(f"Injecting credentials from {username_var} and {password_var}")
        for device in devices:
            device["username"] = username
            device["password"] = password

    # -------------------------------------------------------------------------
    # Abstract methods - MUST be implemented by subclasses
    # -------------------------------------------------------------------------

    @abstractmethod
    def get_architecture_name(self) -> str:
        """Return the architecture identifier.

        Used for logging and error messages.

        Returns:
            Architecture name (e.g., "sdwan", "aci", "catc").
        """
        ...

    @abstractmethod
    def get_schema_root_key(self) -> str:
        """Return the root key in the data model for this architecture.

        Used when loading test inventory and navigating the schema.

        Returns:
            Root key (e.g., "sdwan", "apic", "cc").
        """
        ...

    @abstractmethod
    def navigate_to_devices(self) -> list[dict[str, Any]]:
        """Navigate the data model to find all devices.

        This is where architecture-specific schema navigation happens.
        Implement this to traverse your NAC schema structure.

        Returns:
            Iterable of device data dictionaries from the data model.

        Example (SD-WAN):
            >>> def navigate_to_devices(self):
            ...     devices = []
            ...     for site in self.data_model.get("sdwan", {}).get("sites", []):
            ...         devices.extend(site.get("routers", []))
            ...     return devices
        """
        ...

    @abstractmethod
    def extract_device_id(self, device_data: dict[str, Any]) -> str:
        """Extract unique device identifier from device data.

        This ID is used to match test_inventory entries with data model devices.

        Args:
            device_data: Device data dict from navigate_to_devices().

        Returns:
            Unique device identifier string.

        Example (SD-WAN):
            >>> def extract_device_id(self, device_data):
            ...     return device_data["chassis_id"]
        """
        ...

    @abstractmethod
    def extract_hostname(self, device_data: dict[str, Any]) -> str:
        """Extract device hostname from device data.

        Args:
            device_data: Device data dict from navigate_to_devices().

        Returns:
            Device hostname string.

        Example (SD-WAN):
            >>> def extract_hostname(self, device_data):
            ...     return device_data["device_variables"]["system_hostname"]
        """
        ...

    @abstractmethod
    def extract_host_ip(self, device_data: dict[str, Any]) -> str:
        """Extract management IP address from device data.

        Should handle any IP formatting (e.g., strip CIDR notation).

        Args:
            device_data: Device data dict from navigate_to_devices().

        Returns:
            IP address string (e.g., "10.1.1.100").

        Example (SD-WAN):
            >>> def extract_host_ip(self, device_data):
            ...     ip_var = device_data.get("management_ip_variable", "mgmt_ip")
            ...     ip = device_data["device_variables"].get(ip_var, "")
            ...     return ip.split("/")[0] if "/" in ip else ip
        """
        ...

    @abstractmethod
    def extract_os_type(self, device_data: dict[str, Any]) -> str:
        """Extract operating system type from device data.

        Args:
            device_data: Device data dict from navigate_to_devices().

        Returns:
            OS type string (e.g., "iosxe", "nxos", "iosxr").

        Example (SD-WAN):
            >>> def extract_os_type(self, device_data):
            ...     return device_data.get("os", "iosxe")
        """
        ...

    @abstractmethod
    def get_credential_env_vars(self) -> tuple[str, str]:
        """Return environment variable names for SSH credentials.

        Each architecture uses different env vars for device credentials.
        These are separate from controller credentials.

        Returns:
            Tuple of (username_env_var, password_env_var).

        Example (SD-WAN D2D uses IOS-XE devices):
            >>> def get_credential_env_vars(self):
            ...     return ("IOSXE_USERNAME", "IOSXE_PASSWORD")

        Example (ACI D2D uses NX-OS switches):
            >>> def get_credential_env_vars(self):
            ...     return ("NXOS_SSH_USERNAME", "NXOS_SSH_PASSWORD")
        """
        ...

    # -------------------------------------------------------------------------
    # Optional overrides
    # -------------------------------------------------------------------------

    def get_inventory_filename(self) -> str:
        """Return the test inventory filename.

        Override to use a different filename.

        Returns:
            Filename (default: "test_inventory.yaml").
        """
        return "test_inventory.yaml"
