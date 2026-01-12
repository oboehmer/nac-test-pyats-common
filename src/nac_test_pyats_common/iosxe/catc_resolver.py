"""Catalyst Center device resolver placeholder for D2D testing.

This is a placeholder for the Catalyst Center resolver that will be implemented
when Catalyst Center D2D testing support is added. This resolver will handle
IOS-XE devices managed by Catalyst Center.

Expected environment variables:
    - CC_URL: Catalyst Center controller URL
    - CC_USERNAME: Catalyst Center username
    - CC_PASSWORD: Catalyst Center password
    - IOSXE_USERNAME: SSH username for devices
    - IOSXE_PASSWORD: SSH password for devices

"""

from typing import Any

from nac_test_pyats_common.common import BaseDeviceResolver

from .registry import register_iosxe_resolver


@register_iosxe_resolver("CC")
class CatalystCenterDeviceResolver(BaseDeviceResolver):
    """Placeholder resolver for Catalyst Center D2D testing.

    This resolver will be implemented when Catalyst Center D2D testing
    support is added. Currently a placeholder to reserve the CC registry slot.
    """

    def get_architecture_name(self) -> str:
        """Return architecture name."""
        return "catalyst_center"

    def get_schema_root_key(self) -> str:
        """Return data model root key."""
        return "catalyst_center"

    def navigate_to_devices(self) -> list[dict[str, Any]]:
        """Navigate to devices in data model."""
        raise NotImplementedError(
            "CatalystCenterDeviceResolver is not yet implemented. "
            "This placeholder reserves the CC registry slot for future use."
        )

    def extract_device_id(self, device_data: dict[str, Any]) -> str:
        """Extract device ID."""
        raise NotImplementedError("CatalystCenterDeviceResolver is not yet implemented")

    def extract_hostname(self, device_data: dict[str, Any]) -> str:
        """Extract hostname."""
        raise NotImplementedError("CatalystCenterDeviceResolver is not yet implemented")

    def extract_host_ip(self, device_data: dict[str, Any]) -> str:
        """Extract management IP."""
        raise NotImplementedError("CatalystCenterDeviceResolver is not yet implemented")

    def extract_os_type(self, device_data: dict[str, Any]) -> str:
        """Extract OS type."""
        raise NotImplementedError("CatalystCenterDeviceResolver is not yet implemented")

    def get_credential_env_vars(self) -> tuple[str, str]:
        """Return credential environment variable names."""
        return ("IOSXE_USERNAME", "IOSXE_PASSWORD")
