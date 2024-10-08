import unittest

import database.databaseController
from database.current import create_bot_database, drop_bot_database
from database.databaseController import session


class TestDatabaseOperations(unittest.TestCase):
    guild_id = 395614061393477632
    user_id = 188647277181665280

    def setUp(self):
        create_bot_database()

    def tearDown(self):
        drop_bot_database()

    # Testing the servers table
    def test_add_server(self):
        guild_id = self.guild_id
        server_controller = database.databaseController.ServerDbTransactions()
        server_success = server_controller.add(guild_id, "owner", 100, "invite")
        self.assertEqual(server_success.id, guild_id)
        server_failed = server_controller.add(guild_id, "owner", 100, "invite")
        self.assertFalse(server_failed)
        session.delete(server_success)
        session.rollback()

    def test_update_server(self):
        guild_id = self.guild_id
        server_controller = database.databaseController.ServerDbTransactions()
        server_controller.add(guild_id, "owner", 100, "invite")
        server = server_controller.update(guild_id, owner="new_owner", member_count=200, invite="new_invite")
        self.assertEqual(server.owner, "new_owner")
        self.assertEqual(server.member_count, 200)
        self.assertEqual(server.invite, "new_invite")
        self.assertIsNone(server.deleted_at)
        session.rollback()

    def test_remove_server(self):
        guild_id = self.guild_id
        user_id = self.user_id
        server_controller = database.databaseController.ServerDbTransactions()
        ban_controller = database.databaseController.BanDbTransactions()

        # Ensure the guild exists in the servers table
        server = server_controller.add(guild_id, "owner", 100, "invite")

        # Now add the ban
        ban = ban_controller.add(user_id, guild_id, "reason", "staff")
        self.assertTrue(server)
        server = server_controller.delete(guild_id)
        self.assertIsNone(ban_controller.get(ban.ban_id))

    def test_leave_server(self):
        guild_id = self.guild_id
        server_controller = database.databaseController.ServerDbTransactions()
        server_controller.add(guild_id, "owner", 100, "invite")
        server = server_controller.update(guild_id, delete=True)
        self.assertIsNotNone(server.deleted_at)
        server = server_controller.update(guild_id, delete=False)
        self.assertIsNone(server.deleted_at)

    # Testing the bans table
    def test_add_ban(self):
        guild_id = self.guild_id
        user_id = self.user_id
        server_controller = database.databaseController.ServerDbTransactions()
        ban_controller = database.databaseController.BanDbTransactions()

        # Ensure the guild exists in the servers table
        server_controller.add(guild_id, "owner", 100, "invite")

        # Now add the ban
        ban = ban_controller.add(user_id, guild_id, "reason", "staff")
        self.assertEqual(ban.ban_id, user_id + guild_id)
        ban = ban_controller.add(user_id, guild_id, "reason", "staff")
        self.assertFalse(ban)
        session.rollback()

    def test_get_ban(self):
        guild_id = self.guild_id
        user_id = self.user_id
        server_controller = database.databaseController.ServerDbTransactions()
        ban_controller = database.databaseController.BanDbTransactions()

        # Ensure the guild exists in the servers table
        server_controller.add(guild_id, "owner", 100, "invite")

        # Now add the ban
        ban = ban_controller.add(user_id, guild_id, "reason", "staff")
        self.assertEqual(ban_controller.get(ban.ban_id).ban_id, user_id + guild_id)
        session.rollback()

    def test_delete_ban(self):
        guild_id = self.guild_id
        user_id = self.user_id
        server_controller = database.databaseController.ServerDbTransactions()
        ban_controller = database.databaseController.BanDbTransactions()

        # Ensure the guild exists in the servers table
        server_controller.add(guild_id, "owner", 100, "invite")

        # Now add the ban
        ban = ban_controller.add(user_id, guild_id, "reason", "staff")
        self.assertTrue(ban_controller.delete(ban.ban_id))
        self.assertIsNone(ban_controller.get(ban.ban_id))
        session.rollback()

    def test_get_guild_status_from_ban(self):
        guild_id = self.guild_id
        user_id = self.user_id
        server_controller = database.databaseController.ServerDbTransactions()
        ban_controller = database.databaseController.BanDbTransactions()

        # Ensure the guild exists in the servers table
        guild = server_controller.add(guild_id, "owner", 100, "invite")

        # Now add the ban
        ban = ban_controller.add(user_id, guild_id, "reason", "staff")
        self.assertEqual(ban_controller.get(ban.ban_id).guild.deleted_at, None)
        server_controller.update(guild.id, delete=True)
        self.assertIsNone(ban_controller.get(ban.ban_id))

    def test_update_ban(self):
        guild_id = self.guild_id
        user_id = self.user_id
        server_controller = database.databaseController.ServerDbTransactions()
        ban_controller = database.databaseController.BanDbTransactions()

        # Ensure the guild exists in the servers table
        server_controller.add(guild_id, "owner", 100, "invite")

        # Now add the ban
        ban = ban_controller.add(user_id, guild_id, "reason", "staff")
        self.assertFalse(ban.verified)
        self.assertFalse(ban.hidden)
        ban = ban_controller.update(ban.ban_id, verified=True, hidden=True)
        self.assertTrue(ban.verified)
        self.assertTrue(ban.hidden)

        session.rollback()

    # proof table
    #
    def test_add_proof(self):
        guild_id = self.guild_id
        user_id = self.user_id
        server_controller = database.databaseController.ServerDbTransactions()
        ban_controller = database.databaseController.BanDbTransactions()
        proof_controller = database.databaseController.ProofDbTransactions()

        # Ensure the guild exists in the servers table
        server_controller.add(guild_id, "owner", 100, "invite")

        # Now add the ban
        ban = ban_controller.add(user_id, guild_id, "reason", "staff")
        proof = proof_controller.add(ban.ban_id, "proof", ["https://google.com"])
        self.assertEqual(proof.ban_id, ban.ban_id)
        self.assertEqual(proof.proof, "proof")
        self.assertEqual(proof.attachments, ["https://google.com"])
        print(proof.attachments)
