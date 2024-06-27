from mongo_migrator import BaseMigration


class Migration(BaseMigration):
    async def migrate(self, db):
        await db.your_collection.create_index(
            [("a", "text"), ("b", "text")]
        )

    async def rollback_migration(self, db):
        await db.your_collection.drop_index("a_text_b_text")
