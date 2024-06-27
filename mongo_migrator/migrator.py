import argparse
import asyncio
import importlib.util
import logging
import os

from motor.motor_asyncio import AsyncIOMotorClient

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MigrationManager:
    """
    Class for managing database migrations.

    Attributes:
        client (AsyncIOMotorClient): Asynchronous MongoDB client.
        db (AsyncIOMotorDatabase): MongoDB database.
        migrations_collection (AsyncIOMotorCollection): Collection for storing migration information.

    Examples:
        - Run all migrations: `python migrate.py migrate backend`
        - Run one specific migration: `python migrate.py migrate-one backend 0001_migration`
        - Run one specific migration without module: `python migrate.py migrate-one 0001_migration`
        - Rollback a specific migration: `python migrate.py rollback backend.migrations.0001_migration`
    """

    def __init__(self, mongo_settings):
        """
        Initialize the migration manager.

        Args:
            mongo_settings (MongoSettings): MongoDB settings object.
        """
        self.client = AsyncIOMotorClient(mongo_settings.mongodb_uri)
        self.db = self.client[mongo_settings.mongo_database_name]
        self.migrations_collection = self.db["migrations"]

    async def apply_all_migrations(self, module_name, migrations_dir):
        """
        Applies all migrations from the specified module and folder in the correct order.

        Args:
            module_name (str): The name of the module containing the migrations folder.
            migrations_dir (str): The name of the migrations folder.
        """
        if module_name:
            migrations_path = os.path.join(os.getcwd(), module_name.replace('.', os.sep), migrations_dir)
        else:
            migrations_path = os.path.join(os.getcwd(), migrations_dir)

        if not os.path.exists(migrations_path):
            raise FileNotFoundError(f"Migrations directory not found at {migrations_path}")

        migration_files = sorted(
            [
                f
                for f in os.listdir(migrations_path)
                if f.endswith(".py") and not f.startswith("__")
            ],
            key=lambda x: int(x.split("_")[0]),
        )

        for filename in migration_files:
            migration_module_name = filename[:-3]
            migration_path = os.path.join(migrations_path, filename)
            await self.apply_migration(migration_module_name, migration_path)

    async def apply_migration(self, migration_module_name, migration_path):
        """
        Applies a single migration.

        Args:
            migration_module_name (str): The name of the migration module.
            migration_path (str): The path to the migration file.

        Raises:
            Exception: If the previous migration has not been applied.
        """
        spec = importlib.util.spec_from_file_location(migration_module_name, migration_path)
        migration_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration_module)
        migration_class = getattr(migration_module, "Migration")
        migration = migration_class()
        migration_name = migration.__class__.__name__
        migration_order = int(migration_module_name.split("_")[0])

        if migration_order > 1:
            previous_migration_order = migration_order - 1
            previous_migration = await self.migrations_collection.find_one(
                {"order": previous_migration_order}
            )
            if not previous_migration:
                raise Exception(
                    f"Previous migration with order {previous_migration_order} has not been applied."
                )

        if not await self.migrations_collection.find_one({"name": migration_name}):
            logger.info(f"Applying migration {migration_name}...")
            await migration.migrate(self.db)
            await self.migrations_collection.insert_one(
                {"name": migration_name, "order": migration_order, "applied": True}
            )
            logger.info(f"Migration {migration_name} applied successfully.")

    async def rollback_migration(self, migration_module_name, migration_path):
        """
        Rolls back a single migration.

        Args:
            migration_module_name (str): The name of the migration module.
            migration_path (str): The path to the migration file.
        """
        spec = importlib.util.spec_from_file_location(migration_module_name, migration_path)
        migration_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration_module)
        migration_class = getattr(migration_module, "Migration")
        migration = migration_class()
        migration_name = migration.__class__.__name__
        logger.info(f"Rolling back migration {migration_name}...")
        await migration.rollback_migration(self.db)
        await self.migrations_collection.delete_one({"name": migration_name})
        logger.info(f"Migration {migration_name} rolled back successfully.")


def __import_settings():
    """
    Dynamically imports the settings module from the project root.

    Returns:
        module: The imported settings module.
    """
    project_root = os.getcwd()
    settings_path = os.path.join(project_root, "settings.py")

    if not os.path.exists(settings_path):
        raise FileNotFoundError(f"Settings file not found at {settings_path}")

    spec = importlib.util.spec_from_file_location("settings", settings_path)
    settings = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(settings)
    return settings


async def main(args):
    """
    Main function to manage migrations via the command line.

    Args:
        args (argparse.Namespace): Command line arguments.
    """
    settings = __import_settings()
    mongo_settings = settings.mongo_settings
    manager = MigrationManager(mongo_settings)
    if args.command == "migrate":
        await manager.apply_all_migrations(args.module, "migrations")
    elif args.command == "migrate-one":
        if args.module:
            migration_path = os.path.join(os.getcwd(), args.module.replace('.', os.sep), "migrations",
                                          f"{args.migration}.py")
        else:
            migration_path = os.path.join(os.getcwd(), "migrations", f"{args.migration}.py")
        await manager.apply_migration(args.migration, migration_path)
    elif args.command == "rollback":
        if args.module:
            migration_path = os.path.join(os.getcwd(), args.module.replace('.', os.sep), "migrations",
                                          f"{args.migration}.py")
        else:
            migration_path = os.path.join(os.getcwd(), "migrations", f"{args.migration}.py")
        await manager.rollback_migration(args.migration, migration_path)


def entry_point():
    parser = argparse.ArgumentParser(description="Manage database migrations.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    apply_parser = subparsers.add_parser("migrate", help="Apply all migrations.")
    apply_parser.add_argument(
        "module", type=str, help="The module containing the migrations directory."
    )

    apply_one_parser = subparsers.add_parser(
        "migrate-one", help="Apply one specific migration."
    )
    apply_one_parser.add_argument(
        "module", nargs="?", type=str, help="The module containing the migrations directory."
    )
    apply_one_parser.add_argument(
        "migration", type=str, help="The migration module to apply."
    )

    rollback_parser = subparsers.add_parser("rollback", help="Rollback a migration.")
    rollback_parser.add_argument(
        "module", nargs="?", type=str, help="The module containing the migrations directory."
    )
    rollback_parser.add_argument(
        "migration", type=str, help="The migration module to rollback."
    )

    args = parser.parse_args()
    asyncio.run(main(args))


if __name__ == "__main__":
    entry_point()
