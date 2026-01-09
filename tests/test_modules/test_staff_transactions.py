import unittest

from database.current import create_bot_database, drop_bot_database, Staff
from database.transactions.StaffTransactions import StaffTransactions


class TestStaffDatabaseOperations(unittest.TestCase) :
	user_id = 188647277181665280

	def setUp(self) :
		create_bot_database()
		self.staff_controller = StaffTransactions()

	def tearDown(self) :
		drop_bot_database()

	def test_add_staff_positive_and_negative(self) :
		# Positive: Add a new staff member
		staff = self.staff_controller.add(self.user_id, "rep")
		self.assertIsInstance(staff, Staff)
		self.assertEqual(staff.uid, self.user_id)
		self.assertEqual(staff.role, "rep")

		# Negative: Add a duplicate staff member (should return None)
		duplicate_staff = self.staff_controller.add(self.user_id, "admin")
		self.assertIsNone(duplicate_staff)

	def test_get_staff_positive_and_negative(self) :
		# Positive: Get an existing staff member
		self.staff_controller.add(self.user_id, "rep")
		staff = self.staff_controller.get(self.user_id)
		self.assertIsNotNone(staff)
		self.assertEqual(staff.uid, self.user_id)

		# Negative: Get a non-existent staff member
		non_existent_staff = self.staff_controller.get(12345)
		self.assertIsNone(non_existent_staff)

	def test_get_all_staff_positive_and_negative(self) :
		# Positive: Get all staff members
		self.staff_controller.add(self.user_id, "rep")
		self.staff_controller.add(self.user_id + 1, "admin")
		all_staff = self.staff_controller.get_all()
		self.assertEqual(len(all_staff), 2)

		# Negative: Get all from an empty database
		self.tearDown()
		self.setUp()
		self.assertEqual(len(self.staff_controller.get_all()), 0)

	def test_delete_staff_positive_and_negative(self) :
		# Positive: Delete an existing staff member
		self.staff_controller.add(self.user_id, "rep")
		delete_success = self.staff_controller.delete(self.user_id)
		self.assertTrue(delete_success)
		self.assertIsNone(self.staff_controller.get(self.user_id))

		# Negative: Delete a non-existent staff member
		delete_fail = self.staff_controller.delete(12345)
		self.assertFalse(delete_fail)
