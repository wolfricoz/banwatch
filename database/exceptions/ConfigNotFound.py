class ConfigNotFound(Exception) :
	"""Config item was not found or has not been added yet."""

	def __init__(self, message="guild Config has not been loaded yet or has not been created yet.") :
		self.message = message
		super().__init__(self.message)
