# This class is a collection of multiple tools, which can be called by the 'run' function.
import discord


class Toolbox():

	TOOLS_LIST = {
		"View guilds without ban permissions": "ListGuildsWithoutBanPerms"
	}

	async def run(self, interaction: discord.Interaction, tool: str, *args, **kwargs):
		# We get the function
		f = getattr(self, tool)
		if not f:
			raise AttributeError("Tool doesn't exist")
		# We fill in potential arguments, run the function and return the output. All functions must be async.
		return await f(interaction, *args, **kwargs)

	async def ListGuildsWithoutBanPerms(self, interaction: discord.Interaction, *args, **kwargs):
		"""
		"""
		missing = []
		# test for permission
		for guild in interaction.client.guilds:
			if guild.me.guild_permissions.ban_members:
				continue
			missing.append(guild)
		result = "Missing ban permissions: \n" + "\n".join([f"{g.name} ({g.id})" for g in missing])
		return result
