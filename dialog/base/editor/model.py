class EditorModel:
	"""Small common contract for models edited by a workspace view."""

	def validate(self):
		"""Raise a domain error when the current model cannot be applied."""
		return None

	def apply(self):
		"""Return the value produced when this model is applied."""
		self.validate()
		return self
