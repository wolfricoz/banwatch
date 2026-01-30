import os

import discord
from discord_py_utilities.messages import send_response

from classes.ConfigSetup import ConfigSetup
from database.transactions.ServerTransactions import ServerTransactions



class OnboardingLayout(discord.ui.LayoutView) :
	"""This is the 2.0 embed layout for onboarding messages."""

	def __init__(self):
		super().__init__(timeout=None, )
	custom_id = "onboarding_layout"
	support_server = ServerTransactions().get(int(os.getenv("GUILD")))



	container = discord.ui.Container(

		discord.ui.TextDisplay(


			content="""## Thank you for inviting Banwatch! Let's get you started.
			
To get started with Banwatch, you need to configure it. There are a few ways to do this:
1. **Automatic Setup**: This will create the necessary channels and roles with default settings. This is recommended for most servers to get up and running quickly.
2. **Manual Setup**: This allows you to configure the bot manually on Discord using the `/config` command for more granular control.
3. **Dashboard Setup**: Configure the bot through our web dashboard for an easy-to-use interface.

Please select one of the setup methods below to begin.
"""
		),
		discord.ui.Separator(visible=True),

		accent_colour=discord.Colour.purple()
	)


	actions = discord.ui.ActionRow()

	@actions.button(label="Automatic Setup", style=discord.ButtonStyle.primary, custom_id="onboarding_automatic_setup")
	async def onboarding_automatic_setup(self, interaction: discord.Interaction, button: discord.ui.Button) :
		if not interaction.user.guild_permissions.manage_guild:
			await send_response(interaction, "You need to be an manage_guild to use automatic setup.", ephemeral=True)
			return
		await ConfigSetup().automated_setup(interaction)

	@actions.button(label="Manual Setup", style=discord.ButtonStyle.primary, custom_id="onboarding_manual_setup")
	async def onboarding_manual_setup(self, interaction: discord.Interaction, button: discord.ui.Button) :
		if not interaction.user.guild_permissions.manage_guild:
			await send_response(interaction, "You need to be an manage_guild to use manual setup.", ephemeral=True)
			return

		await ConfigSetup().manual_setup(interaction)

	links = discord.ui.ActionRow()
	links.add_item(discord.ui.Button(label="Dashboard Setup", style=discord.ButtonStyle.link, url=os.getenv("DASHBOARD_URL")))
	links.add_item(discord.ui.Button(label="Documentation", style=discord.ButtonStyle.link, url="https://wolfricoz.github.io/banwatch/"))
	if support_server is not None:
		links.add_item(discord.ui.Button(label="Support Server", style=discord.ButtonStyle.link, url=support_server.invite))


