"""Creates a custom warning modal for the bot."""
import logging

import discord


class InputModal(discord.ui.Modal):
    custom_id = "InputModal"

    def __init__(self, confirmation, title):
        super().__init__(timeout=None, title=title)  # Set a timeout for the modal
        self.confirmation = confirmation
    reason = discord.ui.TextInput(label='What is the reason?', style=discord.TextStyle.long, placeholder='Type your reason here...', max_length=500)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            await self.send_message(interaction, self.confirmation)
        except discord.errors.HTTPException:
            pass

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        print(error)
        await self.send_message(interaction, f"An error occurred: {error}")

    async def send_message(self, interaction: discord.Interaction, message: str) -> None:
        """sends the message to the channel."""
        try:
            await interaction.response.send_message(message, ephemeral=True)
        except discord.errors.HTTPException:
            pass
        except Exception as e:
            logging.error(e)


async def send_modal(interaction: discord.Interaction, confirmation, title = 'Input Modal', max_length=500):
    """Sends the modal to the channel."""
    view = InputModal(confirmation, title)
    view.reason.max_length = max_length
    await interaction.response.send_modal(view)

    await view.wait()
    return view.reason
