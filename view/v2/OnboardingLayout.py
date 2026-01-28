import os

import discord
from discord_py_utilities.messages import send_response

from classes.configsetup import ConfigSetup
from databases.transactions.ServerTransactions import ServerTransactions
from resources.data.config_variables import available_toggles, channelchoices, messagechoices, rolechoices


class OnboardingLayout(discord.ui.LayoutView) :
	"""This is the 2.0 embed layout for onboarding messages."""

	def __init__(self):
		super().__init__(timeout=None, )
	custom_id = "onboarding_layout"
	rolechoices = rolechoices
	channelchoices = channelchoices
	messagechoices = messagechoices
	available_toggles = available_toggles

	support_server = ServerTransactions().get(int(os.getenv("SUPPORTGUILD")))



	container = discord.ui.Container(

		discord.ui.TextDisplay(


			content="""## Thank you for inviting ageverifier! Let's get you started.
			
To get started with ageverifier there are a few ways to setup the bot:
1. Automatic Setup, this will setup the bot with the default settings, and create the required channels and roles for you. (Recommended for most servers)
2. Manual Setup (on discord), this will allow you to configure the bot manually using the `/config`
3. Dashboard Setup, this will allow you to configure the bot using the web dashboard. (recommended for easier manual setup)

Below you'll see a button for each setup method, they will start the respective setup process for you.
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
		status = await ConfigSetup().auto(interaction, self.channelchoices, self.rolechoices, self.messagechoices)
		if not status :
			await send_response(interaction,
				"Automatic setup failed, please try manual setup or use the dashboard to setup the bot.", ephemeral=True)
			return
		await ConfigSetup().check_channel_permissions(interaction.guild)
		await send_response(interaction, "Automatic setup completed successfully!", ephemeral=True)

	@actions.button(label="Manual Setup", style=discord.ButtonStyle.primary, custom_id="onboarding_manual_setup")
	async def onboarding_manual_setup(self, interaction: discord.Interaction, button: discord.ui.Button) :
		if not interaction.user.guild_permissions.manage_guild:
			await send_response(interaction, "You need to be an manage_guild to use manual setup.", ephemeral=True)
			return

		await ConfigSetup().manual(interaction.client, interaction, self.channelchoices, self.rolechoices, self.messagechoices)
		await ConfigSetup().check_channel_permissions(interaction.guild)
		await send_response(interaction, "Manual setup completed successfully!", ephemeral=True)
	links = discord.ui.ActionRow()
	links.add_item(discord.ui.Button(label="Dashboard Setup", style=discord.ButtonStyle.link, url=os.getenv("DASHBOARD_URL")))
	links.add_item(discord.ui.Button(label="Documentation", style=discord.ButtonStyle.link, url="https://wolfricoz.github.io/ageverifier/"))
	if support_server is not None:
		links.add_item(discord.ui.Button(label="Support Server", style=discord.ButtonStyle.link, url=support_server.invite))
