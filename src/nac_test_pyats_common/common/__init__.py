"""Common base classes for nac-test-pyats-common.

This module provides architecture-agnostic base classes that can be extended
by architecture-specific implementations (ACI, SD-WAN, Catalyst Center, etc.).

Key Components:
    BaseDeviceResolver: Abstract base class for device inventory resolution
        using the Template Method pattern. Each architecture implements
        schema-specific navigation while the base class handles common
        logic like credential injection and inventory filtering.

Example:
    from nac_test_pyats_common.common import BaseDeviceResolver

    class ACIDeviceResolver(BaseDeviceResolver):
        def get_architecture_name(self) -> str:
            return "aci"

        def navigate_to_devices(self) -> list[dict[str, Any]]:
            return self.data_model.get("apic", {}).get("nodes", [])

        # ... implement other abstract methods
"""

from nac_test_pyats_common.common.base_device_resolver import BaseDeviceResolver

__all__ = [
    "BaseDeviceResolver",
]
