import discord


class CommandSelect(discord.ui.Select) :
	def __init__(self, reasons, view) :
		options = reasons
		super().__init__(
			placeholder="Select the command you want to know more about!",
			options=options,
			min_values=1,
			max_values=1
		)
		self.parent_view = view

	async def callback(self, interaction: discord.Interaction) :
		# 'interaction.view' is the HelpLayout instance
		# 'self.values[0]' is the selected command name (the label of the SelectOption)
		selected_command = self.values[0]

		# Access the command_docs from the parent view
		command_doc_content = self.parent_view.command_docs.get(
			selected_command,
			"Documentation not found for this command."
		)

		# Update the content of the TextDisplay in the container
		# The TextDisplay is the first item in the container
		self.parent_view.container.children[0].content = f"## {selected_command}\n\n{command_doc_content}"

		# Edit the original message to show the new content
		await interaction.response.edit_message(view=self.parent_view)
