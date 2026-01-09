import unittest

from database.current import Appeals, create_bot_database, drop_bot_database
from database.factories.ban import BanFactory
from database.transactions.AppealsTransactions import AppealsDbTransactions


class TestAppealsDatabaseOperations(unittest.TestCase):
    guild_id = 395614061393477632
    user_id = 188647277181665280

    def setUp(self):
        create_bot_database()

    def tearDown(self):
        drop_bot_database()

    def test_add_appeal(self):
        appeal_controller = AppealsDbTransactions()
        ban = BanFactory().create()

        # Add first appeal -> should return Appeals instance
        appeal = appeal_controller.add(ban.ban_id, "reason")
        self.assertIsInstance(appeal, Appeals)
        self.assertEqual(appeal.ban_id, ban.ban_id)

        # Adding the same appeal again -> should return False (duplicate)
        appeal_dup = appeal_controller.add(ban.ban_id, "reason")
        self.assertFalse(appeal_dup)

    def test_change_status(self):
        appeal_controller = AppealsDbTransactions()
        ban = BanFactory().create()

        # Add an appeal first, then change status
        appeal_controller.add(ban.ban_id, "reason")
        result = appeal_controller.change_status(ban.ban_id, "approved")
        self.assertTrue(result)

        # Verify status persisted via get()
        appeal = appeal_controller.get(ban.ban_id)
        self.assertIsNotNone(appeal)
        self.assertEqual(appeal.status, "approved")

    def test_change_status_returns_false_if_not_exists(self):
        appeal_controller = AppealsDbTransactions()
        ban = BanFactory().create()

        result = appeal_controller.change_status(ban.ban_id, "approved")
        self.assertFalse(result)

    def test_exist_returns_appeal_if_exists(self):
        appeal_controller = AppealsDbTransactions()
        ban = BanFactory().create()

        appeal_controller.add(ban.ban_id, "reason")
        result = appeal_controller.exist(ban.ban_id)
        self.assertIsInstance(result, Appeals)

    def test_exist_returns_none_if_not_exists(self):
        appeal_controller = AppealsDbTransactions()
        ban = BanFactory().create()

        result = appeal_controller.exist(ban.ban_id)
        self.assertIsNone(result)

    def test_get_returns_appeal_if_exists(self):
        appeal_controller = AppealsDbTransactions()
        ban = BanFactory().create()

        appeal_controller.add(ban.ban_id, "reason")
        result = appeal_controller.get(ban.ban_id)
        self.assertIsInstance(result, Appeals)

    def test_get_returns_none_if_not_exists(self):
        appeal_controller = AppealsDbTransactions()
        ban = BanFactory().create()

        result = appeal_controller.get(ban.ban_id)
        self.assertIsNone(result)

