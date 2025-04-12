import discord
from discord.ui import View
from discord_py_utilities.messages import send_message, send_response

from classes.access import AccessControl
from classes.configer import Configer
from database.databaseController import ServerDbTransactions


class ServerInfo(View) :

	def __init__(self) :
		super().__init__(timeout=None)

	async def send(self, channel, guild: discord.Guild) :
		embed = discord.Embed(title=f"{guild.name}'s info")
		server_info = ServerDbTransactions().get(guild.id)
		guild_data = {
			"Owner"         : f"{guild.owner}({guild.owner.id})",
			"User count"    : len([m for m in guild.members if not m.bot]),
			"Bot count"     : len([m for m in guild.members if m.bot]),
			"Channel count" : len(guild.channels),
			"Role count"    : len(guild.roles),
			"Created at"    : guild.created_at.strftime("%m/%d/%Y"),
			"bans"          : len(ServerDbTransactions().get_bans(guild.id)),
			"MFA level"     : guild.mfa_level,
			"invite"        : server_info.invite
		}
		for key, value in guild_data.items() :
			embed.add_field(name=key, value=value, inline=False)
		embed.set_footer(text=guild.id)
		await send_message(channel, embed=embed, view=self)

	@discord.ui.button(label="Approve", style=discord.ButtonStyle.success, custom_id="approve")
	async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button) :
		if not AccessControl().access_dev(interaction.user.id) :
			return await send_response(interaction, "Only developers may use this button")
		await send_response(interaction, "Approved Server")
		await interaction.message.delete()

	@discord.ui.button(label="Leave", style=discord.ButtonStyle.success, custom_id="Leave")
	async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button) :
		if not AccessControl().access_dev(interaction.user.id) :
			return await send_response(interaction, "Only developers may use this button")
		embed = interaction.message.embeds[0]
		guild = interaction.client.get_guild(int(embed.footer.text))
		await send_response(interaction, f"Leaving {guild.name}")
		await guild.leave()
		await interaction.message.delete()

	@discord.ui.button(label="Leave & Blacklist", style=discord.ButtonStyle.success, custom_id="Leave_blacklist")
	async def blacklist_button(self, interaction: discord.Interaction, button: discord.ui.Button) :
		if not AccessControl().access_dev(interaction.user.id) :
			return await send_response(interaction, "Only developers may use this button")
		embed = interaction.message.embeds[0]
		guild = interaction.client.get_guild(int(embed.footer.text))
		await send_response(interaction, f"Leaving {guild.name} and adding it to the blacklist.")
		await Configer.add_to_blacklist(guild.id)
		await guild.leave()
		await interaction.message.delete()
