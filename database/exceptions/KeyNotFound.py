class KeyNotFound(Exception) :
	"""Config item was not found or has not been added yet."""

	def __init__(self, key) :
		self.key = key
		self.message = f"`{key}` not found in Config, please add it using /Config"
		super().__init__(self.message)
