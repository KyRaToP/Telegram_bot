import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class AllowlistTests(unittest.TestCase):
    def test_empty_allowlist_rejects_everyone(self) -> None:
        with patch.dict(os.environ, {"ALLOWED_TELEGRAM_IDS": ""}, clear=False):
            from app.services.access import is_allowed

            self.assertFalse(is_allowed(1))
            self.assertFalse(is_allowed(1001))

    def test_listed_ids_are_allowed(self) -> None:
        with patch.dict(os.environ, {"ALLOWED_TELEGRAM_IDS": "1, 42"}, clear=False):
            from app.services.access import is_allowed

            self.assertTrue(is_allowed(1))
            self.assertTrue(is_allowed(42))
            self.assertFalse(is_allowed(99))


class OwnerIsolationTests(unittest.TestCase):
    def test_mutate_requires_owner(self) -> None:
        asyncio.run(self._mutate_requires_owner())

    async def _mutate_requires_owner(self) -> None:
        handle, raw_path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        db_path = Path(raw_path)
        try:
            import app.db.database as database

            with patch.object(database, "DB_PATH", db_path):
                await database.init_db()
                owner_task = await database.add_task(
                    1001, "Owner task", "desc", "18.08.2026 12:00"
                )
                await database.add_task(
                    2002, "Other task", "desc", "18.08.2026 13:00"
                )

                self.assertIsNone(await database.get_owned_task(owner_task, 2002))
                self.assertIsNotNone(await database.get_owned_task(owner_task, 1001))
                self.assertFalse(
                    await database.update_task(owner_task, 2002, title="hacked")
                )
                self.assertIsNone(await database.toggle_task_status(owner_task, 2002))
                self.assertFalse(await database.delete_task(owner_task, 2002))
                self.assertFalse(await database.reactivate_task(owner_task, 2002))

                owned = await database.get_owned_task(owner_task, 1001)
                self.assertEqual(owned["title"], "Owner task")
        finally:
            db_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
