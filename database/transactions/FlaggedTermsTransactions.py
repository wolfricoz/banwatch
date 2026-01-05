import logging
from abc import abstractmethod

from sqlalchemy import Select

from database import current as db
from database.current import FlaggedTerms
from database.transactions.BanReasonTransactions import DatabaseTransactions


class FlaggedTermsTransactions(DatabaseTransactions) :

	
	
	def add(self, term: str, action: str, regex: bool = False) :
		with self.createsession() as session :

			"""Adds a term to the database"""
			if FlaggedTermsTransactions.exists(term) :
				logging.warning(f"Term '{term}' already exists.")
				return False
			term = db.FlaggedTerms(term=term.lower(), action=action.lower(), regex=regex)
			session.add(term)
			DatabaseTransactions().commit(session)
			return True

	
	
	def delete(self, term: str) :
		"""Deletes a term from the database"""
		with self.createsession() as session :

			term = FlaggedTermsTransactions.exists(term)
			if not term :
				return False
			session.delete(term)
			DatabaseTransactions().commit(session)
			return True

	
	
	def update(self, term: str, action: str, regex: bool = False) -> bool :
		"""Updates a term from the database"""
		with self.createsession() as session :

			term = FlaggedTermsTransactions.exists(term)
			if not term :
				return False
			term.action = action
			term.regex = regex
			DatabaseTransactions().commit(session)
			return True

	
	
	def get(self, term: str) :
		"""Gets a term from the database"""
		with self.createsession() as session :

			return session.scalar(Select(db.FlaggedTerms).where(db.FlaggedTerms.term == term))

	
	
	def exists(self, term: str) -> FlaggedTerms | None :
		"""Checks if a term exists in the database"""
		with self.createsession() as session :

			return session.scalar(Select(db.FlaggedTerms).where(db.FlaggedTerms.term == term))

	
	
	def get_all(self, action: str | None = None) :
		"""Gets all term from the database"""
		with self.createsession() as session :

			if action is None :
				return session.query(db.FlaggedTerms).all()
			return session.query(db.FlaggedTerms).where(db.FlaggedTerms.action == action.lower()).all()
