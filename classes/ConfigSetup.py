import discord
from discord_py_utilities.messages import send_response, send_message
from discord_py_utilities.permissions import check_missing_channel_permissions

from view.multiselect.ChannelSelect import ChannelSelect
from view.multiselect.RolesSelect import RolesSelect


class ConfigSetup:

    async def automated_setup(self, interaction: discord.Interaction):
        await send_response(interaction, " ", view=ConfigView(select_type="auto"), ephemeral=True)

    async def manual_setup(self, interaction: discord.Interaction):
        await send_response(interaction, " ", view=ConfigView(select_type="manual"), ephemeral=True)

class ConfigView(discord.ui.View):
    def __init__(self, select_type="auto"):
        super().__init__(timeout=None)
        match select_type.lower():
            case "auto":
                self.add_item(RolesSelect())
            case "manual":
                self.add_item(ChannelSelect())

