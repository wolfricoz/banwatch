import logging
import re

from database.current import FlaggedTerms
from database.transactions.FlaggedTermsTransactions import FlaggedTermsTransactions


class TermsChecker:
	MAX_FOUND = 3


	def __init__(self, action:str, target: str):
		"""Select the action and the class will start to process it."""
		# Creating the variables to prevent cross contamination if the class is called again.
		self.target = target
		self.result = ""
		self.found = []
		self.action = action
		action = getattr(self, action.lower(), None)
		if action is None:
			raise ValueError("Action not found")
		self.terms = FlaggedTermsTransactions().get_all(self.action)
		if not self.terms or len(self.terms) == 0:
			logging.warning(f"No terms found for action {self.action}")
			return
		action()

	# Actions, these are called by the init.
	def review(self):
		self.checkTerms(first_stop=True)
		if len(self.found) > 0:
			self.result = "review"


	def block(self):
		self.checkTerms(first_stop=True)
		if len(self.found) > 0 :
			self.result = "block"

	def countreview(self):
		self.checkTerms()
		if len(self.found) >= self.MAX_FOUND :
			self.result = "review"

	def countblock(self):
		self.checkTerms()
		if len(self.found) >= self.MAX_FOUND :
			self.result = "block"

	# other functions.

	def checkTerms(self, first_stop: bool = False):
		term: FlaggedTerms
		for term in self.terms:
			if first_stop and len(self.found) > 0:
				return self.found
			if term.regex :
				matches = re.findall(term.term, self.target, flags=re.IGNORECASE)
				self.found.extend(matches)
				continue
			start = 0
			while True :
				idx = self.target.lower().find(term.term.lower(), start)
				if idx == -1 :
					break
				self.found.append(term.term)
				start = idx + 1
		return self.found



	def getResults(self):
		return self.result, self.found

	def getReviewStatus(self):
		return self.result