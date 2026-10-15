import discord
from discord_py_utilities.permissions import check_missing_channel_permissions, check_missing_guild_permissions

from classes.permissions_notice import PERMISSION_INFO, bot_role_name, humanize_permission
from classes.replies import reply

# Server-wide permissions Banwatch can't do its core job without.
REQUIRED_GUILD_PERMS = ["ban_members", "view_audit_log"]
# Server-wide permissions that only individual features need.
OPTIONAL_GUILD_PERMS = ["kick_members", "manage_messages", "manage_guild", "create_instant_invite"]
# A channel can't be used at all without these (we post embeds in every configured channel).
REQUIRED_CHANNEL_PERMS = ["view_channel", "send_messages", "embed_links"]
# Evidence images and updating/revoking older ban messages need these.
OPTIONAL_CHANNEL_PERMS = ["attach_files", "read_message_history"]


def channel_problems(channel) -> tuple[list[str], list[str]] :
	"""Returns (missing required, missing optional) permissions for the bot in ``channel``."""
	return (check_missing_channel_permissions(channel, REQUIRED_CHANNEL_PERMS),
	        check_missing_channel_permissions(channel, OPTIONAL_CHANNEL_PERMS))


class PermissionsCheck() :

	@staticmethod
	def _lines(perms: list[str], missing: list[str]) -> str :
		lines = []
		for perm in perms :
			if perm in missing :
				_, why = PERMISSION_INFO.get(perm, ("", ""))
				lines.append(f"❌ **{humanize_permission(perm)}**" + (f" — to {why}" if why else ""))
			else :
				lines.append(f"✅ {humanize_permission(perm)}")
		return "\n".join(lines)[:1024]

	@classmethod
	def build_report(cls, guild: discord.Guild, mod_channel=None, current_channel=None) -> discord.Embed :
		"""Builds the permission report: what's missing, whether it matters, and where to fix it."""
		missing_required = check_missing_guild_permissions(guild, REQUIRED_GUILD_PERMS)
		missing_optional = check_missing_guild_permissions(guild, OPTIONAL_GUILD_PERMS)

		channels = []
		if mod_channel is not None :
			channels.append(("Mod channel", mod_channel))
		if current_channel is not None and current_channel != mod_channel and isinstance(
				current_channel, (discord.abc.GuildChannel, discord.Thread)) :
			channels.append(("This channel", current_channel))
		channel_results = [(label, ch, *channel_problems(ch)) for label, ch in channels]

		mod_channel_broken = mod_channel is None or bool(channel_results[0][2])
		required_broken = bool(missing_required) or mod_channel_broken
		optional_broken = bool(missing_optional) or any(req or opt for _, _, req, opt in channel_results)

		if required_broken :
			colour, summary = discord.Colour.red(), "❌ Banwatch is missing permissions it needs to work."
		elif optional_broken :
			colour, summary = discord.Colour.orange(), "⚠️ Banwatch works, but some features are missing permissions."
		else :
			colour, summary = discord.Colour.green(), "✅ Banwatch has everything it needs."

		embed = discord.Embed(title="Permissions check", colour=colour, description=summary)
		embed.add_field(name="Required (server-wide)", value=cls._lines(REQUIRED_GUILD_PERMS, missing_required),
		                inline=False)
		embed.add_field(name="Optional (server-wide)", value=cls._lines(OPTIONAL_GUILD_PERMS, missing_optional),
		                inline=False)

		if mod_channel is None :
			embed.add_field(name="Mod channel",
			                value="❌ Not set, or the channel was deleted. Set one with `/config change option:Mod Channel channel:#your-mod-channel`.",
			                inline=False)
		for label, channel, req, opt in channel_results :
			# Only the mod channel matters for the bot to work; say so, or "This channel" reads as a requirement.
			suffix = "" if channel is mod_channel else " (only for commands whose results post here)"
			embed.add_field(
				name=f"{label}: #{channel.name}{suffix}",
				value=(cls._lines(REQUIRED_CHANNEL_PERMS, req) + "\n" + cls._lines(OPTIONAL_CHANNEL_PERMS, opt))[:1024],
				inline=False,
			)

		if required_broken or optional_broken :
			role = bot_role_name(guild)
			steps = [f"Server-wide: **Server Settings → Roles → {role}**, enable the ❌ permissions."]
			if any(req or opt for _, _, req, opt in channel_results) :
				steps.append(f"Channel: open the channel → **Edit Channel → Permissions**, add **{role}**, "
				             "enable the ❌ permissions.")
			steps.append("Run `/config permissioncheck` again to confirm.")
			embed.add_field(name="How to fix", value="\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1)),
			                inline=False)
		embed.set_footer(text=f"Server: {guild.name}"[:2048])
		return embed

	async def permission_check(self, interaction: discord.Interaction, mod_channel=None) :
		"""Replies privately with the report; ephemeral replies don't need any channel permissions.

		Pass ``mod_channel`` when it was just changed: the config cache still holds the old one.
		"""
		if mod_channel is None :
			# Lazy import: ConfigData pulls in the database layer at import time.
			from classes.configdata import ConfigData
			from data.config.mappings import Channels

			mod_channel_id = ConfigData().get_key_or_none(interaction.guild.id, Channels.MOD_CHANNEL)
			# get_key coerces unset values to False, and bool is a subclass of int.
			if isinstance(mod_channel_id, int) and not isinstance(mod_channel_id, bool) :
				mod_channel = interaction.guild.get_channel(mod_channel_id)
		embed = self.build_report(interaction.guild, mod_channel, interaction.channel)
		await reply(interaction, embed=embed)
