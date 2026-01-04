import unittest

from classes.TermsChecker import TermsChecker
from database.current import create_bot_database, drop_bot_database
from database.FlaggedTermsTransactions import FlaggedTermsTransactions


class TestTermsDatabaseOperations(unittest.TestCase) :
	guild_id = 395614061393477632
	user_id = 188647277181665280
	Terms_controller = FlaggedTermsTransactions()
	termsToAdd = {
		"test"  : {
			"term"   : "test",
			"action" : "review",
			"regex"  : False
		},
		"test2" : {
			"term"   : "t.st2",
			"action" : "block",
			"regex"  : True
		},
		"test3" : {
			"term"   : "test3",
			"action" : "countreview",
			"regex"  : False
		},
		"test4" : {
			"term"   : "t.st4",
			"action" : "countblock",
			"regex"  : True
		}

	}

	def setUp(self) :
		create_bot_database()

	def tearDown(self) :
		drop_bot_database()

	def test_add_term(self) :
		terms = self.termsToAdd

		for term in terms :
			self.assertEqual(self.Terms_controller.add(terms[term]["term"], terms[term]["action"], terms[term]["regex"]), True)
			term_data = self.Terms_controller.get(terms[term]["term"])
			self.assertIsNotNone(term_data, f"Term {term} not found in database")
			self.assertEqual(term_data.term, terms[term]["term"], f"Term {term} has wrong value")
			self.assertEqual(term_data.action, terms[term]["action"], f"Term {term} has wrong action")
			self.assertEqual(term_data.regex, terms[term]["regex"], f"Term {term} has wrong regex value")


	def test_delete_term(self) :
		terms = self.termsToAdd
		for term in terms :
			self.Terms_controller.add(terms[term]["term"], terms[term]["action"], terms[term]["regex"])
			self.Terms_controller.delete(term)
			term_data = self.Terms_controller.get(term)
			self.assertIsNone(term_data, f"Term {term} was not removed from database")

	def test_get_all_terms(self) :
		terms = self.termsToAdd
		for term in terms :
			self.Terms_controller.add(terms[term]["term"], terms[term]["action"], terms[term]["regex"])
		all_terms = self.Terms_controller.get_all()
		self.assertEqual(len(all_terms), len(terms), "Not all terms were added to the database")
		for term in all_terms :
			self.assertIn(term.term, [terms[t]["term"] for t in terms], f"Term {term.term} not found in added terms")

	def test_get_term(self) :
		terms = self.termsToAdd
		for term in terms :
			self.Terms_controller.add(terms[term]["term"], terms[term]["action"], terms[term]["regex"])
			term_data = self.Terms_controller.get(terms[term]["term"])
			self.assertIsNotNone(term_data, f"Term {terms[term]['term']} not found in database")
			self.assertEqual(term_data.term, terms[term]["term"], f"Term {terms[term]['term']} has wrong value")
			self.assertEqual(term_data.action, terms[term]["action"], f"Term {terms[term]['term']} has wrong action")
			self.assertEqual(term_data.regex, terms[term]["regex"], f"Term {terms[term]['term']} has wrong regex value")

	def test_update_term(self) :
		terms = self.termsToAdd
		for term in terms :
			self.Terms_controller.add(terms[term]["term"], terms[term]["action"], terms[term]["regex"])
			new_action = "block" if terms[term]["action"] == "review" else "review"
			self.Terms_controller.update(terms[term]["term"], new_action, not terms[term]["regex"])
			term_data = self.Terms_controller.get(terms[term]["term"])
			self.assertIsNotNone(term_data, f"Term {terms[term]['term']} not found in database after update")
			self.assertEqual(term_data.action, new_action, f"Term {terms[term]['term']} action was not updated correctly")
			self.assertEqual(term_data.regex, not terms[term]["regex"], f"Term {terms[term]['term']} regex was not updated correctly")

	def test_perform_action(self) :
		terms = self.termsToAdd
		for term in terms :
			self.Terms_controller.add(terms[term]["term"], terms[term]["action"], terms[term]["regex"])
		checker = TermsChecker("review", "This text should be flagged because it has test in here")
		self.assertEqual(checker.result, "review")
		checker1 = TermsChecker("block", "This text should be flagged because it has tast2 in here")
		self.assertEqual(checker1.result, "block")
		checker2 = TermsChecker("review", "This text should not be flagged because it is clean")
		self.assertEqual(checker2.result, "")
		checker3 = TermsChecker("countreview", "This text should be flagged because it has test3 test3 test3 test3 in here")
		self.assertEqual(checker3.result, "review")
		checker4 = TermsChecker("countreview", "This text should not be flagged because it has test3 test3 in here")
		self.assertEqual(checker4.result, "")
		checker5 = TermsChecker("countblock", "This text should be flagged because it has test4 tist4 tost4 tast4 in here")
		self.assertEqual(checker5.result, "block")
		checker6 = TermsChecker("countblock", "This text should not be flagged because it has test4 tist4 in here")
		self.assertEqual(checker6.result, "")




