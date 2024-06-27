import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from migrator import MigrationManager


class TestMigrationManager(unittest.IsolatedAsyncioTestCase):

    @patch('migrator.AsyncIOMotorClient')
    async def test_apply_all_migrations(self, mock_motor_client):
        """
        Тест для проверки метода apply_all_migrations.

        Use-case:
        - Пользователь хочет применить все миграции из указанного модуля и папки.
        - Метод должен вызывать apply_migration для каждой миграции в правильном порядке.
        """
        # Arrange
        mock_settings = MagicMock()
        mock_settings.mongodb_uri = 'mongodb://localhost:27017'
        mock_settings.mongo_database_name = 'test_db'
        manager = MigrationManager(mock_settings)
        manager.migrations_collection = MagicMock()
        manager.apply_migration = AsyncMock()

        with patch('os.listdir', return_value=['0001_migration.py', '0002_migration.py']):
            with patch('os.path.exists', return_value=True):
                # Act
                await manager.apply_all_migrations('backend', 'migrations')

                # Assert
                self.assertEqual(manager.apply_migration.await_count, 2)
                manager.apply_migration.assert_awaited()

    @patch('migrator.AsyncIOMotorClient')
    async def test_apply_migration(self, mock_motor_client):
        """
        Тест для проверки метода apply_migration.

        Use-case:
        - Пользователь хочет применить одну конкретную миграцию.
        - Метод должен проверить, что предыдущая миграция была применена, и затем применить текущую миграцию.
        """
        mock_settings = MagicMock()
        mock_settings.mongodb_uri = 'mongodb://localhost:27017'
        mock_settings.mongo_database_name = 'test_db'
        manager = MigrationManager(mock_settings)
        manager.migrations_collection = MagicMock()
        manager.migrations_collection.find_one = AsyncMock(return_value=None)
        manager.migrations_collection.insert_one = AsyncMock()

        mock_migration_module = MagicMock()
        mock_migration_class = MagicMock()
        mock_migration_class.return_value.migrate = AsyncMock()
        mock_migration_module.Migration = mock_migration_class

        with patch('importlib.util.spec_from_file_location'), patch('importlib.util.module_from_spec',
                                                                    return_value=mock_migration_module):
            await manager.apply_migration('0001_migration', 'path/to/0001_migration.py')

            mock_migration_class.return_value.migrate.assert_awaited_once()
            manager.migrations_collection.insert_one.assert_awaited_once()

    @patch('migrator.AsyncIOMotorClient')
    async def test_rollback_migration(self, mock_motor_client):
        """
        Тест для проверки метода rollback_migration.

        Use-case:
        - Пользователь хочет откатить одну конкретную миграцию.
        - Метод должен выполнить откат миграции и удалить запись о ней из коллекции миграций.
        """
        # Arrange
        mock_settings = MagicMock()
        mock_settings.mongodb_uri = 'mongodb://localhost:27017'
        mock_settings.mongo_database_name = 'test_db'
        manager = MigrationManager(mock_settings)
        manager.migrations_collection = MagicMock()
        manager.migrations_collection.delete_one = AsyncMock()

        mock_migration_module = MagicMock()
        mock_migration_class = MagicMock()
        mock_migration_class.return_value.rollback_migration = AsyncMock()
        mock_migration_module.Migration = mock_migration_class

        with patch('importlib.util.spec_from_file_location'), patch('importlib.util.module_from_spec',
                                                                    return_value=mock_migration_module):
            await manager.rollback_migration('0001_migration', 'path/to/0001_migration.py')

            mock_migration_class.return_value.rollback_migration.assert_awaited_once()
            manager.migrations_collection.delete_one.assert_awaited_once()


if __name__ == '__main__':
    unittest.main()
