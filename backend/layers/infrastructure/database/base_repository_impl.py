"""
Base Repository Implementation - Enterprise Architecture
=====================================================
Concrete implementation of repository pattern with:
- PostgreSQL connection management
- Transaction support
- Soft delete functionality  
- Audit trail integration
- Performance optimization with connection pooling
- Error handling and logging

Follows Infrastructure layer responsibilities in Clean Architecture.
"""

from typing import TypeVar, Generic, List, Optional, Dict, Any, Union
from datetime import datetime
import logging
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from contextlib import asynccontextmanager

from ...domain.repositories.base_repository import (
    BaseRepository, AuditableRepository, CachingRepository, TransactionalRepository
)
from ...domain.entities.qc_entities import BaseQCEntity

T = TypeVar('T', bound=BaseQCEntity)
logger = logging.getLogger("qc.infrastructure.database")

# SQLAlchemy Base for database models
Base = declarative_base()

class DatabaseConfig:
    """Database configuration for enterprise deployment"""
    
    def __init__(
        self,
        database_url: str,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        echo: bool = False
    ):
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.echo = echo

class DatabaseManager:
    """Enterprise database connection manager"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.engine = None
        self.session_factory = None
        self.logger = logging.getLogger("qc.database.manager")
    
    async def initialize(self):
        """Initialize database engine and session factory"""
        self.engine = create_async_engine(
            self.config.database_url,
            pool_size=self.config.pool_size,
            max_overflow=self.config.max_overflow,
            pool_timeout=self.config.pool_timeout,
            echo=self.config.echo,
            future=True
        )
        
        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        self.logger.info("Database initialized successfully")
    
    @asynccontextmanager
    async def get_session(self):
        """Get database session with automatic commit/rollback"""
        if not self.session_factory:
            raise RuntimeError("Database not initialized")
        
        session = self.session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    async def close(self):
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()
            self.logger.info("Database connections closed")

class BaseRepositoryImpl(BaseRepository[T]):
    """Base repository implementation with PostgreSQL support"""
    
    def __init__(self, db_manager: DatabaseManager, model_class: type):
        self.db_manager = db_manager
        self.model_class = model_class
        self.logger = logging.getLogger(f"qc.repository.{model_class.__name__.lower()}")
    
    async def create(self, entity: T) -> T:
        """Create new entity"""
        async with self.db_manager.get_session() as session:
            try:
                # Convert entity to SQLAlchemy model
                db_model = self._entity_to_model(entity)
                session.add(db_model)
                await session.flush()
                await session.refresh(db_model)
                
                # Convert back to domain entity
                result = self._model_to_entity(db_model)
                self.logger.info(f"Created {self.model_class.__name__}: {result.id}")
                return result
                
            except Exception as e:
                self.logger.error(f"Failed to create {self.model_class.__name__}: {e}")
                raise
    
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get entity by ID"""
        async with self.db_manager.get_session() as session:
            try:
                result = await session.get(self.model_class, entity_id)
                if result:
                    return self._model_to_entity(result)
                return None
                
            except Exception as e:
                self.logger.error(f"Failed to get {self.model_class.__name__} by ID {entity_id}: {e}")
                raise
    
    async def get_all(
        self, 
        limit: int = 100, 
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[T]:
        """Get all entities with pagination and filtering"""
        async with self.db_manager.get_session() as session:
            try:
                query = sa.select(self.model_class)
                
                # Apply filters if provided
                if filters:
                    for key, value in filters.items():
                        if hasattr(self.model_class, key):
                            query = query.where(getattr(self.model_class, key) == value)
                
                # Apply pagination
                query = query.offset(offset).limit(limit)
                
                result = await session.execute(query)
                models = result.scalars().all()
                
                return [self._model_to_entity(model) for model in models]
                
            except Exception as e:
                self.logger.error(f"Failed to get all {self.model_class.__name__}: {e}")
                raise
    
    async def update(self, entity_id: str, updates: Dict[str, Any]) -> T:
        """Update entity by ID"""
        async with self.db_manager.get_session() as session:
            try:
                # Get existing entity
                model = await session.get(self.model_class, entity_id)
                if not model:
                    raise ValueError(f"Entity {entity_id} not found")
                
                # Apply updates
                for key, value in updates.items():
                    if hasattr(model, key):
                        setattr(model, key, value)
                
                # Always update updated_at timestamp
                model.updated_at = datetime.utcnow()
                
                await session.flush()
                await session.refresh(model)
                
                result = self._model_to_entity(model)
                self.logger.info(f"Updated {self.model_class.__name__}: {entity_id}")
                return result
                
            except Exception as e:
                self.logger.error(f"Failed to update {self.model_class.__name__} {entity_id}: {e}")
                raise
    
    async def delete(self, entity_id: str, soft_delete: bool = True) -> bool:
        """Delete entity by ID"""
        async with self.db_manager.get_session() as session:
            try:
                model = await session.get(self.model_class, entity_id)
                if not model:
                    return False
                
                if soft_delete:
                    # Soft delete - just mark as deleted
                    model.status = 'deleted'
                    model.updated_at = datetime.utcnow()
                    self.logger.info(f"Soft deleted {self.model_class.__name__}: {entity_id}")
                else:
                    # Hard delete
                    await session.delete(model)
                    self.logger.info(f"Hard deleted {self.model_class.__name__}: {entity_id}")
                
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to delete {self.model_class.__name__} {entity_id}: {e}")
                raise
    
    async def search(
        self, 
        query: str, 
        fields: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[T]:
        """Search entities by text"""
        async with self.db_manager.get_session() as session:
            try:
                # Build search query across specified fields
                search_conditions = []
                
                if not fields:
                    # Default search across string fields
                    fields = [name for name, field in self.model_class.__dict__.items()
                             if isinstance(field, sa.Column) and str(field.type) == 'VARCHAR']
                
                for field_name in fields:
                    if hasattr(self.model_class, field_name):
                        field = getattr(self.model_class, field_name)
                        search_conditions.append(field.ilike(f'%{query}%'))
                
                if not search_conditions:
                    return []
                
                # Combine conditions with OR
                query_stmt = sa.select(self.model_class).where(
                    sa.or_(*search_conditions)
                ).limit(limit)
                
                result = await session.execute(query_stmt)
                models = result.scalars().all()
                
                return [self._model_to_entity(model) for model in models]
                
            except Exception as e:
                self.logger.error(f"Failed to search {self.model_class.__name__}: {e}")
                raise
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities with optional filters"""
        async with self.db_manager.get_session() as session:
            try:
                query = sa.select(sa.func.count(self.model_class.id))
                
                if filters:
                    for key, value in filters.items():
                        if hasattr(self.model_class, key):
                            query = query.where(getattr(self.model_class, key) == value)
                
                result = await session.execute(query)
                count = result.scalar()
                return count
                
            except Exception as e:
                self.logger.error(f"Failed to count {self.model_class.__name__}: {e}")
                raise
    
    def _entity_to_model(self, entity: T):
        """Convert domain entity to SQLAlchemy model"""
        # This should be implemented by concrete repositories
        raise NotImplementedError("Subclasses must implement _entity_to_model")
    
    def _model_to_entity(self, model) -> T:
        """Convert SQLAlchemy model to domain entity"""
        # This should be implemented by concrete repositories
        raise NotImplementedError("Subclasses must implement _model_to_entity")

class AuditableRepositoryImpl(AuditableRepository[T], BaseRepositoryImpl[T]):
    """Repository implementation with audit trail support"""
    
    async def get_audit_trail(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get audit trail for entity"""
        async with self.db_manager.get_session() as session:
            try:
                # Query audit logs for this entity
                query = sa.select(AuditLog).where(
                    sa.and_(
                        AuditLog.entity_id == entity_id,
                        AuditLog.entity_type == self.model_class.__name__
                    )
                ).order_by(AuditLog.created_at.desc())
                
                result = await session.execute(query)
                audit_logs = result.scalars().all()
                
                return [self._audit_log_to_dict(log) for log in audit_logs]
                
            except Exception as e:
                self.logger.error(f"Failed to get audit trail for {entity_id}: {e}")
                raise
    
    async def create_with_audit(
        self, 
        entity: T, 
        created_by: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> T:
        """Create entity with audit trail"""
        async with self.db_manager.get_session() as session:
            try:
                # Set audit fields
                entity.created_by = created_by
                if metadata:
                    entity.metadata = metadata
                
                # Create entity
                result = await self.create(entity)
                
                # Create audit record
                await self._create_audit_record(
                    session=session,
                    entity_id=result.id,
                    action='CREATE',
                    performed_by=created_by,
                    old_values=None,
                    new_values=entity.dict(),
                    metadata=metadata
                )
                
                return result
                
            except Exception as e:
                self.logger.error(f"Failed to create entity with audit: {e}")
                raise
    
    async def update_with_audit(
        self,
        entity_id: str,
        updates: Dict[str, Any],
        updated_by: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> T:
        """Update entity with audit trail"""
        async with self.db_manager.get_session() as session:
            try:
                # Get old values for audit
                old_model = await session.get(self.model_class, entity_id)
                old_values = self._model_to_entity(old_model).dict() if old_model else None
                
                # Update entity
                result = await self.update(entity_id, updates)
                
                # Create audit record
                await self._create_audit_record(
                    session=session,
                    entity_id=entity_id,
                    action='UPDATE',
                    performed_by=updated_by,
                    old_values=old_values,
                    new_values=result.dict(),
                    metadata=metadata
                )
                
                return result
                
            except Exception as e:
                self.logger.error(f"Failed to update entity with audit: {e}")
                raise
    
    async def _create_audit_record(
        self,
        session: AsyncSession,
        entity_id: str,
        action: str,
        performed_by: str,
        old_values: Optional[Dict[str, Any]],
        new_values: Optional[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Create audit record"""
        try:
            audit_log = AuditLog(
                entity_id=entity_id,
                entity_type=self.model_class.__name__,
                action=action,
                performed_by=performed_by,
                old_values=old_values,
                new_values=new_values,
                metadata=metadata
            )
            session.add(audit_log)
            
        except Exception as e:
            self.logger.error(f"Failed to create audit record: {e}")
            # Don't raise - audit failure shouldn't break main operation
    
    def _audit_log_to_dict(self, audit_log) -> Dict[str, Any]:
        """Convert audit log to dictionary"""
        return {
            'id': audit_log.id,
            'entity_id': audit_log.entity_id,
            'entity_type': audit_log.entity_type,
            'action': audit_log.action,
            'performed_by': audit_log.performed_by,
            'created_at': audit_log.created_at,
            'old_values': audit_log.old_values,
            'new_values': audit_log.new_values,
            'metadata': audit_log.metadata
        }

# Audit log table for audit functionality
class AuditLog(Base):
    """Audit log table for tracking entity changes"""
    
    __tablename__ = 'audit_logs'
    
    id = sa.Column(sa.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_id = sa.Column(sa.String, nullable=False, index=True)
    entity_type = sa.Column(sa.String, nullable=False, index=True)
    action = sa.Column(sa.String, nullable=False)  # CREATE, UPDATE, DELETE
    performed_by = sa.Column(sa.String, nullable=False)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow, nullable=False, index=True)
    old_values = sa.Column(sa.JSON)
    new_values = sa.Column(sa.JSON)
    metadata = sa.Column(sa.JSON)

# Utility functions for repository setup
async def create_database_manager(config: DatabaseConfig) -> DatabaseManager:
    """Create and initialize database manager"""
    manager = DatabaseManager(config)
    await manager.initialize()
    return manager

async def create_tables(db_manager: DatabaseManager):
    """Create all database tables"""
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)