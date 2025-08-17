import unittest

from classes.access import AccessControl
from database.current import create_bot_database, drop_bot_database
from database.databaseController import StaffDbTransactions, session


class TestStaffDatabaseOperations(unittest.TestCase) :
	guild_id = 395614061393477632
	user_id = 188647277181665280
	staff_controller= StaffDbTransactions()

	def setUp(self) :
		create_bot_database()

	def tearDown(self) :
		drop_bot_database()

	def test_add_staff(self):
		staff = self.staff_controller.add(self.user_id, "rep")
		self.assertEqual(staff.uid, self.user_id)
		self.assertEqual(staff.role, "rep")

	def test_get_staff(self):
		self.staff_controller.add(self.user_id, "rep")
		staff = self.staff_controller.get(self.user_id)
		self.assertIsNotNone(staff)
		self.assertEqual(staff.uid, self.user_id)
		self.assertEqual(staff.role, "rep")

	def test_get_all_staff(self):
		self.staff_controller.add(self.user_id, "rep")
		staff = self.staff_controller.get_all()
		self.assertIsNotNone(staff)
		self.assertEqual(staff[0].uid, self.user_id)
		self.assertEqual(staff[0].role, "rep")

	def test_delete_staff(self):
		self.staff_controller.add(self.user_id, "rep")
		self.staff_controller.delete(self.user_id)
		staff = self.staff_controller.get(self.user_id)
		self.assertIsNone(staff)


	def test_check_access(self):
		self.staff_controller.add(self.user_id, "rep")
		self.assertTrue(AccessControl().access_all(self.user_id), )
		self.assertFalse(AccessControl().access_dev(self.user_id), )
		self.assertTrue(AccessControl().access_owner(self.user_id), )
		self.assertFalse(AccessControl().access_owner(0))

		session.rollback()