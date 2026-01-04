class CommitError(Exception) :
	"""the commit failed."""

	def __init__(self, message="Commiting the data to the database failed and has been rolled back; please try again.") :
		self.message = message
		super().__init__(self.message)
