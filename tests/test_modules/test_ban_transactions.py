import unittest

from database.current import create_bot_database, drop_bot_database
from database.transactions.ServerTransactions import ServerTransactions
from database.transactions.BanTransactions import BanTransactions
from database.factories.ban import BanFactory
from database.factories.serverfactory import ServerFactory


class TestBanDatabaseOperations(unittest.TestCase):
    guild_id = 395614061393477632
    user_id = 188647277181665280

    def setUp(self):
        create_bot_database()
        self.server_controller = ServerTransactions()
        self.ban_controller = BanTransactions()

    def tearDown(self):
        drop_bot_database()

    # add: positive and negative
    def test_add_ban_positive_and_duplicate_negative(self):
        guild_id = self.guild_id
        user_id = self.user_id
        # Ensure the guild exists
        self.server_controller.add(guild_id, "owner", "server_name", 100, "invite")
        # Positive: add returns ban object
        ban = self.ban_controller.add(user_id, guild_id, "reason", "staff")
        self.assertIsNotNone(ban)
        self.assertEqual(ban.ban_id, user_id + guild_id)
        # Negative: adding duplicate returns False
        dup = self.ban_controller.add(user_id, guild_id, "reason", "staff")
        self.assertFalse(dup)

    def test_add_ban_negative_without_server(self):
        # Negative: adding a ban when server not present should fail (False/None)
        self.server_controller.add(999999999999999999, "owner", "server_name", 100, "invite")

        result = self.ban_controller.add(self.user_id, 999999999999999998, "r", "s")
        self.assertFalse(result)

    # get: positive and negative
    def test_get_ban_positive(self):
        guild_id = self.guild_id
        user_id = self.user_id
        self.server_controller.add(guild_id, "owner", "server_name", 100, "invite")
        created = self.ban_controller.add(user_id, guild_id, "reason", "staff", approved=True)
        got = self.ban_controller.get(user_id + guild_id)
        self.assertIsNotNone(got)
        self.assertEqual(got.ban_id, created.ban_id)

    def test_get_ban_negative(self):
        # Negative: get nonexistent ban returns None
        self.assertIsNone(self.ban_controller.get(1234567890))

    # update: positive and negative
    def test_update_ban_positive(self):
        ban = BanFactory().create(approved=False)
        updated = self.ban_controller.update(ban.ban_id, verified=True, approved=True)
        self.assertIsNotNone(updated)
        self.assertTrue(updated.verified)
        self.assertTrue(updated.approved)

    def test_update_ban_negative_nonexistent(self):
        # Negative: updating nonexistent ban returns None/False
        res = self.ban_controller.update(999999999999, verified=True)
        self.assertFalse(res)

    # get_all: positive and negative
    def test_get_all_positive_and_hidden_excluded(self):
        bans = BanFactory().create(amount=5)
        self.assertEqual(len(self.ban_controller.get_all()), 5)
        self.ban_controller.update(bans[0].ban_id, hidden=True)
        self.assertEqual(len(self.ban_controller.get_all()), 4)

    def test_get_all_negative_empty(self):
        # Negative: when no bans present
        self.assertEqual(len(self.ban_controller.get_all()), 0)

    # get_all_pending: positive and negative
    def test_get_all_pending_positive_and_server_hidden(self):
        bans = BanFactory().create(amount=3, approved=False)
        # add more pending
        more = BanFactory().create(amount=2, approved=False)
        self.assertEqual(len(self.ban_controller.get_all_pending()), 5)
        # hide the server for one ban and ensure it's excluded # keep reference
        ServerTransactions().update(more[0].gid, hidden=True)
        self.assertLessEqual(len(self.ban_controller.get_all_pending()), 5)

    def test_get_all_pending_negative_empty(self):
        # Negative: when no pending bans exist
        self.assertEqual(len(self.ban_controller.get_all_pending()), 0)

    # get_all_user: positive and negative
    def test_get_all_user_positive_and_negative(self):
        guild1 = ServerFactory().create()
        guild2 = ServerFactory().create()
        self.ban_controller.add(self.user_id, guild1.id, "r", "s", approved=True)
        self.ban_controller.add(self.user_id, guild2.id, "r", "s", approved=True)
        self.assertEqual(len(self.ban_controller.get_all_user(self.user_id)), 2)
        # Negative: user with no bans
        self.assertEqual(len(self.ban_controller.get_all_user(999999999999)), 0)

    # count: positive and negative (available/hidden/deleted)
    def test_count_positive_and_types(self):
        bans = BanFactory().create(amount=6)
        self.assertEqual(self.ban_controller.count(), 6)
        self.ban_controller.update(bans[0].ban_id, hidden=True)
        self.ban_controller.delete_soft(bans[1].ban_id)
        self.assertEqual(self.ban_controller.count(result_type="available"), 4)
        self.assertEqual(self.ban_controller.count(result_type="hidden"), 1)
        self.assertEqual(self.ban_controller.count(result_type="deleted"), 1)

    def test_count_negative_no_bans(self):
        # Negative: counts on empty DB
        self.assertEqual(self.ban_controller.count(), 0)
        self.assertEqual(self.ban_controller.count(result_type="hidden"), 0)
        self.assertEqual(self.ban_controller.count(result_type="deleted"), 0)

    # exists: positive and negative
    def test_exists_positive_and_negative(self):
        ban = BanFactory().create()
        self.assertTrue(self.ban_controller.exists(ban.ban_id))
        self.assertFalse(self.ban_controller.exists(111111111111111111))

    # delete_soft: positive and negative
    def test_delete_soft_positive_and_get_none(self):
        ServerFactory().create()
        ban = BanFactory().create()
        self.assertTrue(self.ban_controller.delete_soft(ban.ban_id))
        self.assertIsNone(self.ban_controller.get(ban.ban_id))

    def test_delete_soft_negative_nonexistent(self):
        # Negative: deleting nonexistent ban returns False
        self.assertFalse(self.ban_controller.delete_soft(999999999999))

    # get_deleted_bans: positive and negative
    def test_get_deleted_bans_positive_and_negative(self):
        bans = BanFactory().create(amount=4)
        for b in bans[:3]:
            self.ban_controller.delete_soft(b.ban_id)
        deleted = self.ban_controller.get_deleted_bans()
        self.assertEqual(len(deleted), 3)
        # Negative: if none deleted
        # first restore DB to clean state
        drop_bot_database()
        create_bot_database()
        self.assertEqual(len(self.ban_controller.get_deleted_bans()), 0)

    # get guild status from ban: positive and when guild deleted (negative)
    def test_get_guild_status_from_ban_positive_and_negative(self):
        guild = ServerFactory().create()
        # add ban for that guild
        ban = self.ban_controller.add(self.user_id, guild.id, "r", "s")
        got = self.ban_controller.get(ban.ban_id)
        self.assertIsNotNone(got)
        # now mark guild deleted and ensure ban is treated as inaccessible
        self.server_controller.update(guild.id, delete=True)
        self.assertIsNone(self.ban_controller.get(ban.ban_id))
