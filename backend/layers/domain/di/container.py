"""
Dependency Injection Container - Enterprise Architecture
======================================================
Advanced dependency injection system supporting:
- Singleton and transient lifecycle management
- Interface-to-implementation mapping
- Circular dependency detection
- Configuration-based registration
- Runtime dependency resolution

Follows SOLID principles for loose coupling and testability.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Type, Dict, Any, Callable, List, Optional, Union
from functools import wraps
import inspect
import logging
from enum import Enum

logger = logging.getLogger("qc.di")

T = TypeVar('T')

class ServiceLifetime(str, Enum):
    """Service lifecycle options"""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"

class IDependencyContainer(ABC):
    """Interface for dependency injection container"""
    
    @abstractmethod
    def register_singleton(self, interface: Type[T], implementation: Type[T]) -> None:
        """Register singleton service"""
        pass
    
    @abstractmethod
    def register_transient(self, interface: Type[T], implementation: Type[T]) -> None:
        """Register transient service"""
        pass
    
    @abstractmethod
    def register_scoped(self, interface: Type[T], implementation: Type[T]) -> None:
        """Register scoped service"""
        pass
    
    @abstractmethod
    def register_instance(self, interface: Type[T], instance: T) -> None:
        """Register specific instance"""
        pass
    
    @abstractmethod
    def get(self, service_type: Type[T]) -> T:
        """Resolve service instance"""
        pass
    
    @abstractmethod
    def try_get(self, service_type: Type[T]) -> Optional[T]:
        """Try to resolve service, return None if not registered"""
        pass

class ServiceRegistration:
    """Service registration information"""
    
    def __init__(
        self,
        interface: Type,
        implementation: Type,
        lifetime: ServiceLifetime,
        instance: Optional[Any] = None,
        factory: Optional[Callable] = None
    ):
        self.interface = interface
        self.implementation = implementation
        self.lifetime = lifetime
        self.instance = instance
        self.factory = factory
        self.resolved_instances: Dict[str, Any] = {}

class DependencyContainer(IDependencyContainer):
    """Enterprise-grade dependency injection container"""
    
    def __init__(self):
        """Initialize dependency container"""
        self._registrations: Dict[Type, ServiceRegistration] = {}
        self._resolving_stack: List[Type] = []
        self._scoped_instances: Dict[str, Any] = {}
        self.logger = logging.getLogger("qc.di.container")
    
    def register_singleton(self, interface: Type[T], implementation: Type[T]) -> 'DependencyContainer':
        """Register singleton service"""
        self._validate_registration(interface, implementation)
        
        self._registrations[interface] = ServiceRegistration(
            interface=interface,
            implementation=implementation,
            lifetime=ServiceLifetime.SINGLETON
        )
        
        self.logger.debug(f"Registered singleton: {interface.__name__} -> {implementation.__name__}")
        return self
    
    def register_transient(self, interface: Type[T], implementation: Type[T]) -> 'DependencyContainer':
        """Register transient service"""
        self._validate_registration(interface, implementation)
        
        self._registrations[interface] = ServiceRegistration(
            interface=interface,
            implementation=implementation,
            lifetime=ServiceLifetime.TRANSIENT
        )
        
        self.logger.debug(f"Registered transient: {interface.__name__} -> {implementation.__name__}")
        return self
    
    def register_scoped(self, interface: Type[T], implementation: Type[T]) -> 'DependencyContainer':
        """Register scoped service"""
        self._validate_registration(interface, implementation)
        
        self._registrations[interface] = ServiceRegistration(
            interface=interface,
            implementation=implementation,
            lifetime=ServiceLifetime.SCOPED
        )
        
        self.logger.debug(f"Registered scoped: {interface.__name__} -> {implementation.__name__}")
        return self
    
    def register_instance(self, interface: Type[T], instance: T) -> 'DependencyContainer':
        """Register specific instance (treated as singleton)"""
        if not isinstance(instance, interface):
            raise TypeError(f"Instance must implement {interface.__name__}")
        
        self._registrations[interface] = ServiceRegistration(
            interface=interface,
            implementation=type(instance),
            lifetime=ServiceLifetime.SINGLETON,
            instance=instance
        )
        
        self.logger.debug(f"Registered instance: {interface.__name__} -> {type(instance).__name__}")
        return self
    
    def register_factory(self, interface: Type[T], factory: Callable[[], T], lifetime: ServiceLifetime = ServiceLifetime.SINGLETON) -> 'DependencyContainer':
        """Register service with factory function"""
        self._registrations[interface] = ServiceRegistration(
            interface=interface,
            implementation=None,  # Not used with factories
            lifetime=lifetime,
            factory=factory
        )
        
        self.logger.debug(f"Registered factory: {interface.__name__} -> {factory.__name__}")
        return self
    
    def get(self, service_type: Type[T]) -> T:
        """Resolve service instance"""
        if service_type not in self._registrations:
            raise ValueError(f"Service {service_type.__name__} is not registered")
        
        registration = self._registrations[service_type]
        
        # Check for circular dependencies
        if service_type in self._resolving_stack:
            cycle = " -> ".join([t.__name__ for t in self._resolving_stack[1:] + [service_type]])
            raise ValueError(f"Circular dependency detected: {cycle}")
        
        self._resolving_stack.append(service_type)
        
        try:
            # Handle factory registration
            if registration.factory:
                return self._resolve_factory(registration)
            
            # Handle different lifetimes
            if registration.lifetime == ServiceLifetime.SINGLETON:
                return self._resolve_singleton(registration)
            elif registration.lifetime == ServiceLifetime.SCOPED:
                return self._resolve_scoped(registration)
            else:  # TRANSIENT
                return self._resolve_transient(registration)
        
        finally:
            self._resolving_stack.pop()
    
    def try_get(self, service_type: Type[T]) -> Optional[T]:
        """Try to resolve service, return None if not registered"""
        try:
            return self.get(service_type)
        except ValueError:
            return None
    
    def _resolve_singleton(self, registration: ServiceRegistration) -> Any:
        """Resolve singleton service"""
        if registration.instance is not None:
            return registration.instance
        
        # Check if already resolved
        if not registration.resolved_instances:
            registration.resolved_instances['instance'] = self._create_instance(registration.implementation)
        
        return registration.resolved_instances['instance']
    
    def _resolve_scoped(self, registration: ServiceRegistration) -> Any:
        """Resolve scoped service"""
        scope_id = self._get_current_scope_id()
        
        if scope_id not in registration.resolved_instances:
            instance = self._create_instance(registration.implementation)
            registration.resolved_instances[scope_id] = instance
        
        return registration.resolved_instances[scope_id]
    
    def _resolve_transient(self, registration: ServiceRegistration) -> Any:
        """Resolve transient service (always create new instance)"""
        return self._create_instance(registration.implementation)
    
    def _resolve_factory(self, registration: ServiceRegistration) -> Any:
        """Resolve service using factory function"""
        if registration.lifetime == ServiceLifetime.SINGLETON:
            if not registration.resolved_instances:
                registration.resolved_instances['instance'] = registration.factory()
            return registration.resolved_instances['instance']
        else:
            return registration.factory()
    
    def _create_instance(self, implementation_type: Type) -> Any:
        """Create instance with constructor injection"""
        constructor = implementation_type.__init__
        
        # Get constructor parameters
        signature = inspect.signature(constructor)
        parameters = signature.parameters
        
        if not parameters or len(parameters) == 1:  # Only 'self' parameter
            return implementation_type()
        
        # Resolve dependencies for constructor parameters
        kwargs = {}
        for param_name, param in parameters.items():
            if param_name == 'self':
                continue
            
            if param.annotation and param.annotation != inspect.Parameter.empty:
                dependency = self.get(param.annotation)
                kwargs[param_name] = dependency
        
        return implementation_type(**kwargs)
    
    def _validate_registration(self, interface: Type, implementation: Type):
        """Validate registration parameters"""
        if not inspect.isclass(interface):
            raise TypeError(f"Interface {interface} must be a class")
        
        if not inspect.isclass(implementation):
            raise TypeError(f"Implementation {implementation} must be a class")
        
        if not issubclass(implementation, interface):
            raise TypeError(f"Implementation {implementation.__name__} must inherit from {interface.__name__}")
        
        if interface in self._registrations:
            existing = self._registrations[interface]
            self.logger.warning(f"Overriding existing registration: {interface.__name__} -> {existing.implementation.__name__}")
    
    def _get_current_scope_id(self) -> str:
        """Get current scope identifier (placeholder for scoped context)"""
        # This would be implemented with actual scoping mechanism
        return "default_scope"
    
    def create_scope(self) -> 'DependencyScope':
        """Create new dependency scope for scoped services"""
        return DependencyScope(self)
    
    def clear_scoped_instances(self, scope_id: Optional[str] = None):
        """Clear scoped instances"""
        if scope_id:
            # Clear specific scope
            for registration in self._registrations.values():
                if scope_id in registration.resolved_instances:
                    del registration.resolved_instances[scope_id]
        else:
            # Clear all scoped instances
            self._scoped_instances.clear()

class DependencyScope:
    """Dependency scope for managing scoped service lifetimes"""
    
    def __init__(self, container: DependencyContainer):
        self.container = container
        self.scope_id = f"scope_{id(self)}"
        self.is_disposed = False
    
    def get(self, service_type: Type[T]) -> T:
        """Get service within this scope"""
        if self.is_disposed:
            raise RuntimeError("Scope has been disposed")
        return self.container.get(service_type)
    
    def try_get(self, service_type: Type[T]) -> Optional[T]:
        """Try to get service within this scope"""
        if self.is_disposed:
            return None
        return self.container.try_get(service_type)
    
    def dispose(self):
        """Dispose scope and clear scoped instances"""
        if not self.is_disposed:
            self.container.clear_scoped_instances(self.scope_id)
            self.is_disposed = True
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dispose()

# Decorators for dependency injection
def inject(service_type: Type[T]) -> T:
    """Dependency injection decorator for properties"""
    def decorator(cls):
        if not hasattr(cls, '_container'):
            raise RuntimeError(f"Class {cls.__name__} must be created through DI container")
        
        # Inject property that resolves from container
        def getter(self):
            return cls._container.get(service_type)
        
        setter_name = f"_set_{service_type.__name__.lower()}"
        
        setattr(cls, service_type.__name__.lower(), property(getter))
        return cls
    return decorator

def auto_wire(cls: Type[T]) -> Type[T]:
    """Automatically wire constructor dependencies from container"""
    original_init = cls.__init__
    
    @wraps(original_init)
    def new_init(self, *args, **kwargs):
        # If no args provided, inject from container
        if not args:
            container = getattr(self, '_container', None)
            if container:
                signature = inspect.signature(original_init)
                parameters = signature.parameters
                
                injected_kwargs = {}
                for param_name, param in parameters.items():
                    if param_name == 'self':
                        continue
                    
                    if param.annotation and param.annotation != inspect.Parameter.empty:
                        dep = container.try_get(param.annotation)
                        if dep:
                            injected_kwargs[param_name] = dep
                
                kwargs.update(injected_kwargs)
        
        original_init(self, *args, **kwargs)
    
    cls.__init__ = new_init
    return cls

# Global container instance
_global_container: Optional[DependencyContainer] = None

def get_container() -> DependencyContainer:
    """Get global dependency container instance"""
    global _global_container
    if _global_container is None:
        _global_container = DependencyContainer()
    return _global_container

def configure_services(configurator: Callable[[DependencyContainer], None]) -> None:
    """Configure services with configurator function"""
    container = get_container()
    configurator(container)