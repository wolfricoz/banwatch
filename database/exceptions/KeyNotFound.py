class KeyNotFound(Exception) :
	"""config item was not found or has not been added yet."""

	def __init__(self, key) :
		self.key = key
		self.message = f"`{key}` not found in config, please add it using /config"
		super().__init__(self.message)
