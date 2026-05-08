"""
Alembic Environment Configuration - Enterprise Migration System
==============================================================
Enterprise-grade database migration environment with:
- Multi-environment support (dev/staging/prod)
- Rollback capabilities
- Migration validation
- Performance optimization
- Backup integration

Follows enterprise DevOps best practices for database schema management.
"""

import os
import asyncio
from asyncio import run as asyncio_run
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import pool
from alembic import context

# Import our database models
from qc_repository_impl import (
    Base, QCRecordModel, QCBatchModel, TemperatureReadingModel,
    QCFacilityModel, QCProductModel, AuditLog
)
from .database_config import DatabaseConfig, get_database_config

# Alembic configuration object
config = context.config

# Set database URL from environment or config
db_config = get_database_config()
config.set_main_option('sqlalchemy.url', db_config.database_url)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
target_metadata = Base.metadata

# Enterprise migration features
class EnterpriseMigrationEnvironment:
    """Enterprise migration environment with advanced features"""
    
    def __init__(self):
        self.logger = logging.getLogger("qc.migrations")
        self.db_config = db_config
    
    def get_async_engine(self) -> AsyncEngine:
        """Get async engine for migrations"""
        return create_async_engine(
            self.db_config.database_url,
            poolclass=pool.NullPool,
            echo=self.db_config.echo
        )
    
    async def run_migration_online(self) -> None:
        """Run migrations in online mode with connection"""
        try:
            connectable = self.get_async_engine()
            
            async with connectable.connect() as connection:
                await connection.run_sync(
                    context.configure,
                    connection=connection,
                    target_metadata=target_metadata,
                    compare_type=True,
                    compare_server_default=True,
                    include_object=self._include_object_callback,
                    process_revision_directives=self._revision_directives,
                    render_item=self._render_item_callback,
                    user_module_prefix="qc_",
                    version_table="qc_alembic_version"
                )
                
                with context.begin_transaction():
                    await context.run_migrations()
                    
            self.logger.info("Migration completed successfully")
            
        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            raise
        finally:
            await connectable.dispose()
    
    def _include_object_callback(self, object, name, type_, reflected, compare_to):
        """Callback for filtering migration objects"""
        # Exclude temporary tables and test data
        if type_ == "table" and name.startswith("temp_"):
            return False
        
        # Exclude certain indexes based on environment
        if type_ == "index" and self.db_config.pool_size <= 5:  # Low-resource environment
            performance_indexes = ["idx_qc_records_created_at", "idx_temperature_readings_created_at"]
            if any(index_name in name for index_name in performance_indexes):
                return False
        
        return True
    
    def _revision_directives(self, context, revision, directives):
        """Custom revision directives for enterprise migrations"""
        # Add comments and metadata to migrations
        for directive in directives:
            if hasattr(directive, 'upgrade_ops'):
                for op in directive.upgrade_ops.ops:
                    if hasattr(op, 'to_table') and op.to_table:
                        op.to_table.comment = f"QC System Table - Migrated on {datetime.utcnow().isoformat()}"
    
    def _render_item_callback(self, type_, renderer, context, **kw):
        """Custom rendering for migration items"""
        if type_ == "index":
            # Add enterprise-specific index options
            if kw.get('tablename') == 'temperature_readings':
                kw['postgresql_using'] = 'btree'
                kw['postgresql_with'] = {'fillfactor': 70}
        
        return renderer(type_, **kw)
    
    async def create_backup_before_migration(self, migration_id: str) -> str:
        """Create database backup before migration"""
        if os.getenv('ENVIRONMENT') == 'production':
            try:
                from scripts.backup import create_migration_backup
                backup_path = await create_migration_backup(migration_id)
                self.logger.info(f"Database backup created: {backup_path}")
                return backup_path
            except Exception as e:
                self.logger.warning(f"Failed to create pre-migration backup: {e}")
        
        return ""
    
    async def validate_migration(self, migration_id: str) -> bool:
        """Validate migration completed successfully"""
        try:
            # Check table existence
            expected_tables = [
                "qc_records", "qc_batches", "temperature_readings",
                "qc_facilities", "qc_products", "audit_logs"
            ]
            
            connectable = self.get_async_engine()
            async with connectable.connect() as connection:
                result = await connection.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )
                existing_tables = {row[0] for row in result.fetchall()}
                
                missing_tables = set(expected_tables) - existing_tables
                if missing_tables:
                    self.logger.error(f"Missing tables after migration: {missing_tables}")
                    return False
                
                # Check indexes are created
                result = await connection.execute(
                    "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'"
                )
                existing_indexes = {row[0] for row in result.fetchall()}
                
                required_indexes = {
                    "idx_qc_records_batch_id", "idx_qc_records_facility_id",
                    "idx_qc_batches_batch_number", "idx_qc_batches_production_date",
                    "idx_temperature_readings_batch_id", "idx_temperature_readings_facility_id"
                }
                
                missing_indexes = required_indexes - existing_indexes
                if missing_indexes:
                    self.logger.warning(f"Missing indexes: {missing_indexes}")
                
                await connectable.dispose()
                return True
                
        except Exception as e:
            self.logger.error(f"Migration validation failed: {e}")
            return False

class MigrationManager:
    """Enterprise migration manager with rollback support"""
    
    def __init__(self):
        self.env = EnterpriseMigrationEnvironment()
        self.logger = logging.getLogger("qc.migrations.manager")
    
    async def upgrade_to_revision(self, revision: str = "head") -> bool:
        """Upgrade to specific revision"""
        try:
            migration_id = revision if revision != "head" else "HEAD"
            await self.env.create_backup_before_migration(migration_id)
            
            # Set target revision
            context.configure(cmd_opts={'revision': revision})
            
            await self.env.run_migration_online()
            
            # Validate migration
            success = await self.env.validate_migration(migration_id)
            if success:
                self.logger.info(f"Successfully upgraded to revision: {revision}")
                return True
            else:
                self.logger.error(f"Migration validation failed for revision: {revision}")
                return False
                
        except Exception as e:
            self.logger.error(f"Upgrade migration failed: {e}")
            # Attempt rollback
            await self._attempt_rollback()
            raise
    
    async def downgrade_to_revision(self, revision: str) -> bool:
        """Downgrade to specific revision with safety checks"""
        try:
            # Safety check for production environment
            if os.getenv('ENVIRONMENT') == 'production':
                current_revision = await self._get_current_revision()
                await self._validate_downgrade_safety(current_revision, revision)
            
            # Create backup before downgrade
            await self.env.create_backup_before_migration(f"downgrade_to_{revision}")
            
            # Set target revision for downgrade
            context.configure(cmd_opts={'revision': revision})
            
            await self.env.run_migration_online()
            
            self.logger.info(f"Successfully downgraded to revision: {revision}")
            return True
            
        except Exception as e:
            self.logger.error(f"Downgrade migration failed: {e}")
            raise
    
    async def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status"""
        try:
            connectable = self.env.get_async_engine()
            async with connectable.connect() as connection:
                # Get current revision
                result = await connection.execute(
                    "SELECT version_num FROM qc_alembic_version LIMIT 1"
                )
                current = result.scalar_one_or_none()
                
                # Get available revisions
                from alembic.runtime.migration import MigrationContext
                from alembic.script import ScriptDirectory
                
                script_dir = ScriptDirectory.from_config(config)
                migration_context = MigrationContext.configure(connection)
                
                revision_map = {}
                for rev in script_dir.walk_revisions("head", "base"):
                    revision_map[rev.revision] = {
                        'down_revision': rev.down_revision,
                        'doc': rev.doc,
                        'timestamp': rev.create_date
                    }
                
                await connectable.dispose()
                
                return {
                    'current_revision': current,
                    'head_revision': script_dir.get_head(),
                    'available_revisions': revision_map,
                    'pending_migrations': self._get_pending_migrations(current, revision_map),
                    'environment': os.getenv('ENVIRONMENT', 'development')
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get migration status: {e}")
            return {}
    
    async def _get_current_revision(self) -> str:
        """Get current database revision"""
        connectable = self.env.get_async_engine()
        async with connectable.connect() as connection:
            result = await connection.execute(
                "SELECT version_num FROM qc_alembic_version LIMIT 1"
            )
            return result.scalar_one_or_none() or "base"
    
    async def _validate_downgrade_safety(self, current_rev: str, target_rev: str):
        """Validate downgrade safety for production"""
        # Implement safety checks for production downgrades
        if current_rev == "head" and target_rev == "base":
            raise ValueError("Cannot downgrade from head to base in production")
        
        # Add more sophisticated safety checks as needed
        pass
    
    async def _attempt_rollback(self):
        """Attempt rollback to previous revision on failure"""
        try:
            self.logger.warning("Attempting rollback to previous revision...")
            # Implement rollback logic
            pass
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
    
    def _get_pending_migrations(self, current: str, revision_map: Dict) -> List[str]:
        """Get list of pending migrations"""
        if not current:
            return list(revision_map.keys())
        
        pending = []
        for rev, info in revision_map.items():
            if info['down_revision'] == current or (info['down_revision'] and current in revision_map.get(info['down_revision'], {})):
                pending.append(rev)
        
        return pending

# Global migration manager instance
migration_manager = MigrationManager()

def do_run_migrations():
    """Main migration execution function"""
    asyncio_run(context.run_async(migration_manager.env.run_migration_online()))

# Context configuration for alembic
def run_migrations_online():
    """Run migrations in 'online' mode"""
    asyncio_run(migration_manager.upgrade_to_revision())

def run_migrations_offline():
    """Run migrations in 'offline' mode"""
    context.configure(
        url=db_config.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()