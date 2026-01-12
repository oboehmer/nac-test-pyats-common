"""IOS-XE adapter module for NAC PyATS testing.

This module provides a generic IOS-XE test base class and resolver registry
for architecture-specific device resolvers. It supports SSH-based device-to-device
(D2D) testing across multiple architectures that manage IOS-XE devices (SD-WAN,
Meraki, Catalyst Center, etc.).

The module implements a plugin architecture where each controller type can register
its own device resolver while sharing common IOS-XE SSH testing capabilities.

Classes:
    IOSXETestBase: Base class for IOS-XE SSH/D2D tests with common functionality.
        Provides device iteration, command execution, and result processing.

Registry Functions:
    register_iosxe_resolver: Decorator for registering architecture-specific resolvers.
    get_resolver_for_controller: Get the appropriate resolver for a controller type.
    get_supported_controllers: List all registered controller types.

Example:
    For registering a new resolver:

    >>> from nac_test_pyats_common.iosxe import register_iosxe_resolver
    >>> from nac_test_pyats_common.common import BaseDeviceResolver
    >>>
    >>> @register_iosxe_resolver("SDWAN")
    ... class SDWANDeviceResolver(BaseDeviceResolver):
    ...     def get_architecture_name(self) -> str:
    ...         return "sdwan"
    ...     # ... implement other abstract methods

    For using in tests:

    >>> from nac_test_pyats_common.iosxe import IOSXETestBase
    >>>
    >>> class VerifyInterfaceStatus(IOSXETestBase):
    ...     @aetest.test
    ...     def verify_interfaces(self, steps, device):
    ...         # SSH-based verification on IOS-XE device
    ...         output = device.execute("show ip interface brief")
    ...         # ... process output
"""

from .registry import (
    get_resolver_for_controller,
    get_supported_controllers,
    register_iosxe_resolver,
)
from .test_base import IOSXETestBase

__all__ = [
    # Test base class
    "IOSXETestBase",
    # Registry functions
    "register_iosxe_resolver",
    "get_resolver_for_controller",
    "get_supported_controllers",
]
