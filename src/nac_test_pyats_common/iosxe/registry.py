"""Registry for IOS-XE device resolvers.

This module implements a plugin architecture for registering and retrieving
device resolvers for different controller types that manage IOS-XE devices.
Each architecture (SD-WAN, Meraki, Catalyst Center, etc.) can register its
own resolver while sharing common IOS-XE functionality.

The registry pattern allows for:
- Decoupled architecture implementations
- Runtime discovery of available resolvers
- Easy extension with new controller types
- Type-safe resolver registration and retrieval

Global Variables:
    _IOSXE_RESOLVER_REGISTRY: Dictionary mapping controller types to resolver classes.

Functions:
    register_iosxe_resolver: Decorator for registering a resolver class.
    get_resolver_for_controller: Retrieve a resolver for a specific controller type.
    get_supported_controllers: List all registered controller types.
"""

import logging
from collections.abc import Callable
from typing import TypeVar

from nac_test_pyats_common.common import BaseDeviceResolver

# Type variable for the resolver class type
T = TypeVar("T", bound=BaseDeviceResolver)

logger = logging.getLogger(__name__)

# Global registry for IOS-XE device resolvers
_IOSXE_RESOLVER_REGISTRY: dict[str, type[BaseDeviceResolver]] = {}


def register_iosxe_resolver(controller_type: str) -> Callable[[type[T]], type[T]]:
    """Decorator to register an IOS-XE device resolver for a controller type.

    This decorator registers a device resolver class with the global registry,
    associating it with a specific controller type. The resolver must extend
    BaseDeviceResolver and implement all required abstract methods.

    Args:
        controller_type: The controller type identifier (e.g., "SDWAN", "MERAKI",
            "CATALYST_CENTER"). Should be uppercase by convention.

    Returns:
        A decorator function that registers the class and returns it unchanged.

    Raises:
        ValueError: If a resolver is already registered for the controller type.
        TypeError: If the class doesn't extend BaseDeviceResolver.

    Example:
        >>> @register_iosxe_resolver("SDWAN")
        ... class SDWANDeviceResolver(BaseDeviceResolver):
        ...     def get_architecture_name(self) -> str:
        ...         return "sdwan"
        ...     # ... implement other abstract methods
        >>>
        >>> # The resolver is now registered and can be retrieved
        >>> resolver_class = get_resolver_for_controller("SDWAN")
    """

    def decorator(cls: type[T]) -> type[T]:
        """Register the resolver class and return it unchanged.

        Args:
            cls: The resolver class to register.

        Returns:
            The same class, unchanged.

        Raises:
            ValueError: If a resolver is already registered for the controller type.
            TypeError: If the class doesn't extend BaseDeviceResolver.
        """
        # Validate the class extends BaseDeviceResolver
        if not issubclass(cls, BaseDeviceResolver):
            raise TypeError(f"Resolver class {cls.__name__} must extend BaseDeviceResolver")

        # Check for duplicate registration
        if controller_type in _IOSXE_RESOLVER_REGISTRY:
            existing_class = _IOSXE_RESOLVER_REGISTRY[controller_type]
            raise ValueError(
                f"A resolver is already registered for controller type '{controller_type}': "
                f"{existing_class.__module__}.{existing_class.__name__}"
            )

        # Register the resolver
        _IOSXE_RESOLVER_REGISTRY[controller_type] = cls
        logger.debug(
            f"Registered IOS-XE resolver {cls.__name__} for controller type '{controller_type}'"
        )

        return cls

    return decorator


def get_resolver_for_controller(controller_type: str) -> type[BaseDeviceResolver] | None:
    """Get the device resolver class for a specific controller type.

    Retrieves the registered resolver class for the specified controller type.
    Returns None if no resolver is registered for that type.

    Args:
        controller_type: The controller type identifier (e.g., "SDWAN", "MERAKI").

    Returns:
        The resolver class if registered, None otherwise.

    Example:
        >>> resolver_class = get_resolver_for_controller("SDWAN")
        >>> if resolver_class:
        ...     resolver = resolver_class(data_model)
        ...     devices = resolver.get_resolved_inventory()
        ... else:
        ...     print("No resolver found for SDWAN")
    """
    resolver_class = _IOSXE_RESOLVER_REGISTRY.get(controller_type)

    if resolver_class:
        logger.debug(
            f"Found resolver {resolver_class.__name__} for controller type '{controller_type}'"
        )
    else:
        logger.debug(
            f"No resolver registered for controller type '{controller_type}'. "
            f"Available types: {', '.join(get_supported_controllers())}"
        )

    return resolver_class


def get_supported_controllers() -> list[str]:
    """Get a list of all registered controller types.

    Returns a sorted list of controller type identifiers for which
    resolvers have been registered. This is useful for validation,
    documentation, and user feedback.

    Returns:
        Sorted list of registered controller type strings.

    Example:
        >>> controllers = get_supported_controllers()
        >>> print(f"Supported controllers: {', '.join(controllers)}")
        Supported controllers: CATALYST_CENTER, MERAKI, SDWAN
    """
    return sorted(_IOSXE_RESOLVER_REGISTRY.keys())
