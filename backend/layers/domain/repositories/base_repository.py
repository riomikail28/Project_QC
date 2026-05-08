"""
Base Repository Interface - Enterprise Architecture
==================================================
Abstract base repository defining standard CRUD operations
and query patterns for clean architecture implementation.

This follows SOLID principles:
- Single Responsibility: Each repository handles one entity type
- Open/Closed: Open for extension, closed for modification  
- Liskov Substitution: Subtypes can replace base types
- Interface Segregation: Small, focused interfaces
- Dependency Inversion: Depends on abstractions, not concretions
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

# Generic type for entities
EntityType = TypeVar('EntityType', bound=BaseModel)

class BaseRepository(ABC, Generic[EntityType]):
    """
    Abstract base repository implementing standard CRUD operations.
    
    Enterprise Features:
    - Generic typing support with TypeVar
    - Async/await support for scalability
    - Error handling and logging
    - Transaction support
    - Audit trails
    - Soft delete support
    """
    
    @abstractmethod
    async def create(self, entity: EntityType) -> EntityType:
        """
        Create a new entity
        
        Args:
            entity: Entity to create
            
        Returns:
            Created entity with generated fields
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[EntityType]:
        """
        Get entity by ID
        
        Args:
            entity_id: Unique identifier
            
        Returns:
            Entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_all(
        self, 
        limit: int = 100, 
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[EntityType]:
        """
        Get all entities with pagination and filtering
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            filters: Optional filter criteria
            
        Returns:
            List of entities
        """
        pass
    
    @abstractmethod
    async def update(self, entity_id: str, updates: Dict[str, Any]) -> EntityType:
        """
        Update entity by ID
        
        Args:
            entity_id: Unique identifier
            updates: Fields to update
            
        Returns:
            Updated entity
        """
        pass
    
    @abstractmethod
    async def delete(self, entity_id: str, soft_delete: bool = True) -> bool:
        """
        Delete entity by ID
        
        Args:
            entity_id: Unique identifier
            soft_delete: Perform soft delete if True
            
        Returns:
            True if deleted successfully
        """
        pass
    
    @abstractmethod
    async def search(
        self, 
        query: str, 
        fields: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[EntityType]:
        """
        Search entities by text
        
        Args:
            query: Search query
            fields: Specific fields to search in
            limit: Maximum results
            
        Returns:
            List of matching entities
        """
        pass
    
    @abstractmethod
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count entities with optional filters
        
        Args:
            filters: Optional filter criteria
            
        Returns:
            Count of entities
        """
        pass


class ReadOnlyRepository(BaseRepository[EntityType]):
    """
    Read-only repository interface for services that only need
    to read data without modification capabilities.
    """
    
    @abstractmethod
    async def create(self, entity: EntityType) -> EntityType:
        raise NotImplementedError("Create operation not allowed on read-only repository")
    
    @abstractmethod  
    async def update(self, entity_id: str, updates: Dict[str, Any]) -> EntityType:
        raise NotImplementedError("Update operation not allowed on read-only repository")
    
    @abstractmethod
    async def delete(self, entity_id: str, soft_delete: bool = True) -> bool:
        raise NotImplementedError("Delete operation not allowed on read-only repository")


class AuditableRepository(BaseRepository[EntityType]):
    """
    Repository with audit trail support for critical business entities.
    Tracks creation, modification, and access for compliance requirements.
    """
    
    @abstractmethod
    async def get_audit_trail(self, entity_id: str) -> List[Dict[str, Any]]:
        """
        Get audit trail for entity
        
        Args:
            entity_id: Unique identifier
            
        Returns:
            List of audit events
        """
        pass
    
    @abstractmethod
    async def create_with_audit(
        self, 
        entity: EntityType, 
        created_by: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> EntityType:
        """
        Create entity with audit trail
        
        Args:
            entity: Entity to create
            created_by: User/entity performing creation
            metadata: Additional audit metadata
            
        Returns:
            Created entity
        """
        pass
    
    @abstractmethod
    async def update_with_audit(
        self,
        entity_id: str,
        updates: Dict[str, Any],
        updated_by: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> EntityType:
        """
        Update entity with audit trail
        
        Args:
            entity_id: Unique identifier
            updates: Fields to update
            updated_by: User/entity performing update
            metadata: Additional audit metadata
            
        Returns:
            Updated entity
        """
        pass


class CachingRepository(BaseRepository[EntityType]):
    """
    Repository with caching support for frequently accessed entities.
    Implements cache-aside pattern for performance optimization.
    """
    
    @abstractmethod
    async def invalidate_cache(self, entity_id: str) -> None:
        """
        Invalidate cache for specific entity
        
        Args:
            entity_id: Entity to invalidate from cache
        """
        pass
    
    @abstractmethod
    async def refresh_cache(self, entity_id: str) -> EntityType:
        """
        Refresh cache for specific entity
        
        Args:
            entity_id: Entity to refresh in cache
            
        Returns:
            Fresh entity data
        """
        pass
    
    @abstractmethod
    async def clear_all_cache(self) -> None:
        """
        Clear all cached entities
        """
        pass


class TransactionalRepository(BaseRepository[EntityType]):
    """
    Repository with transaction support for complex operations.
    Ensures data consistency across multiple operations.
    """
    
    @abstractmethod
    async def begin_transaction(self) -> Any:
        """
        Begin database transaction
        
        Returns:
            Transaction handle
        """
        pass
    
    @abstractmethod
    async def commit_transaction(self, transaction: Any) -> None:
        """
        Commit transaction
        
        Args:
            transaction: Transaction handle
        """
        pass
    
    @abstractmethod
    async def rollback_transaction(self, transaction: Any) -> None:
        """
        Rollback transaction
        
        Args:
            transaction: Transaction handle
        """
        pass
    
    @abstractmethod
    async def execute_in_transaction(
        self, 
        operations: List[callable]
    ) -> List[Any]:
        """
        Execute multiple operations in a transaction
        
        Args:
            operations: List of operations to execute
            
        Returns:
            Results of all operations
        """
        pass


# Utility decorators and context managers
def with_transaction(func):
    """Decorator to automatically handle transaction lifecycle"""
    async def wrapper(self, *args, **kwargs):
        transaction = await self.begin_transaction()
        try:
            result = await func(self, *args, **kwargs)
            await self.commit_transaction(transaction)
            return result
        except Exception:
            await self.rollback_transaction(transaction)
            raise
    return wrapper


def cache_result(key_prefix: str, ttl: int = 3600):
    """Decorator to cache repository operation results"""
    def decorator(func):
        async def wrapper(self, *args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            cached = await self.get_from_cache(cache_key)
            if cached:
                return cached
            
            # Execute function and cache result
            result = await func(self, *args, **kwargs)
            await self.set_cache(cache_key, result, ttl)
            return result
        return wrapper
    return decorator