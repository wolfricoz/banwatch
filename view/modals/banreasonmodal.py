# python
import logging
import discord

class BanReasonCreateModal(discord.ui.Modal):
    custom_id = "BanReasonCreateModal"

    def __init__(self, confirmation: str, title: str = "Create Ban Reason"):
        super().__init__(timeout=None, title=title)
        self.confirmation = confirmation
        self.values: dict | None = None

    name = discord.ui.TextInput(
        label="Name",
        style=discord.TextStyle.short,
        placeholder="Display name (max 26 chars)",
        max_length=26,
        required=True,
    )

    description = discord.ui.TextInput(
        label="Description",
        style=discord.TextStyle.short,
        placeholder="Short description (max 100 chars)",
        max_length=100,
        required=False,
    )

    reason = discord.ui.TextInput(
        label="Reason",
        style=discord.TextStyle.long,
        placeholder="Detailed reason (max 512 chars)",
        max_length=512,
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        # capture submitted values for the caller
        self.values = {
            "name": self.name.value.strip(),
            "description": self.description.value.strip(),
            "reason": self.reason.value.strip(),
        }
        try:
            await interaction.response.send_message(self.confirmation, ephemeral=True)
        except discord.errors.HTTPException:
            pass
        finally:
            self.stop()

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        logging.exception(error)
        try:
            await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)
        except Exception:
            pass


async def send_banreason_modal(interaction: discord.Interaction, confirmation: str, title: str = "Create Ban Reason"):
    """
    Sends the BanReasonCreateModal, waits for submission, and returns a dict:
    { "name": str, "description": str, "reason": str } or None if cancelled.
    """
    view = BanReasonCreateModal(confirmation, title)
    await interaction.response.send_modal(view)
    await view.wait()
    return view.values