from abc import ABC, abstractmethod


class BaseMigration(ABC):
    @abstractmethod
    async def migrate(self, db):
        pass

    @abstractmethod
    async def rollback_migration(self, db):
        pass
