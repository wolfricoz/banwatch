"""User-facing permission notices.

When the bot fails an action because it is missing a Discord permission, this module
turns that failure into a clear, actionable message for the people who can actually
fix it (server owner / staff): what is missing, why it matters, and the exact steps to
resolve it. Notices are rate-limited per problem so we never spam a server.

Ported from the ageverifier bot's PermissionNotice; adapted for Banwatch's config
(modchannel key), permission set (ban_members-centric) and docs.
"""
import logging
import time

import discord
from discord_py_utilities.permissions import check_missing_channel_permissions, find_first_accessible_text_channel

# The channel permissions the bot needs to operate in a mod / log channel.
DEFAULT_CHANNEL_PERMS = ["view_channel", "send_messages", "embed_links", "attach_files"]

# Documentation links surfaced on every notice.
BANWATCH_PERMISSIONS_DOCS = "https://wolfricoz.github.io/banwatch/permissions.html"
# Official Discord "Setting Up Permissions" help article.
DISCORD_PERMISSIONS_DOCS = "https://support.discord.com/hc/en-us/articles/206029707-Setting-Up-Permissions-FAQ"

# Friendly label + a short "so it can ..." explanation for each permission we care about.
PERMISSION_INFO = {
	"view_channel"          : ("View Channel", "see the channel so it can post and manage ban messages"),
	"send_messages"         : ("Send Messages", "post ban notifications in the mod channel"),
	"embed_links"           : ("Embed Links", "send ban and warning embeds"),
	"attach_files"          : ("Attach Files", "attach evidence images to ban and warning messages"),
	"read_message_history"  : ("Read Message History", "find previous ban messages when updating or revoking them"),
	"manage_messages"       : ("Manage Messages", "clean up and revoke ban messages"),
	"ban_members"           : ("Ban Members", "apply shared bans to your server"),
	"kick_members"          : ("Kick Members", "remove users as part of warning punishments"),
	"manage_guild"          : ("Manage Server", "read invite data for the dashboard"),
	"create_instant_invite" : ("Create Invite", "generate an invite link for the dashboard"),
	"view_audit_log"        : ("View Audit Log", "read ban reasons from the audit log"),
}


def humanize_permission(perm: str) -> str:
	"""Return the Discord-facing label for a permission key (e.g. 'ban_members' -> 'Ban Members')."""
	label, _ = PERMISSION_INFO.get(perm, (perm.replace("_", " ").title(), ""))
	return label


class PermissionNotice :
	"""Builds and delivers actionable permission notices, with per-problem rate limiting."""

	# guild_id -> {dedupe_key: last_sent_monotonic}
	# NOTE: this cache is in-memory only: it resets on restart (a notice can re-send once after
	#   each deploy) and grows unbounded across guilds/problems over time. Fine for current scale;
	#   revisit (TTL eviction, or persist) if memory or duplicate notices matter.
	_last_sent: dict[int, dict[str, float]] = {}
	# Don't nag about the same missing permissions in the same channel more than once an hour.
	_COOLDOWN_SECONDS = 3600

	@classmethod
	def _should_send(cls, guild_id: int, dedupe_key: str) -> bool :
		now = time.monotonic()
		guild_map = cls._last_sent.setdefault(guild_id, {})
		last = guild_map.get(dedupe_key, 0.0)
		if now - last < cls._COOLDOWN_SECONDS :
			return False
		guild_map[dedupe_key] = now
		return True

	@staticmethod
	def build_embed(guild: discord.Guild, *, channel=None, missing: list[str] | None = None,
	                purpose: str | None = None) -> discord.Embed :
		"""Compose the notice embed: what is missing, why it matters, and how to fix it."""
		missing = missing or []
		is_channel = isinstance(channel, (discord.abc.GuildChannel, discord.Thread))
		# Always name the server (and channel, when known). This is often DM'd to an owner who
		# runs several servers, so "your server" is useless and a channel mention won't even
		# render outside the guild — spell it out in plain text.
		location = f"**{guild.name}**"
		if is_channel :
			location = f"channel **#{channel.name}** in **{guild.name}**"

		embed = discord.Embed(
			title="⚠️ Banwatch is missing permissions",
			colour=discord.Colour.orange(),
		)
		# set_author puts the server name + icon at the very top of the embed as a second signal.
		embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
		reason = f" (needed so I can {purpose})" if purpose else ""
		embed.description = (
			f"I'm missing permissions in {location}{reason}. "
			"Until they're granted, that action will keep failing."
		)

		if missing :
			lines = []
			for perm in missing :
				label, why = PERMISSION_INFO.get(perm, (humanize_permission(perm), ""))
				lines.append(f"• **{label}**" + (f" — to {why}" if why else ""))
			embed.add_field(name="Missing permissions", value="\n".join(lines)[:1024], inline=False)

		# Tailor the fix steps to whether this is a channel-level or hierarchy-level problem.
		needs_hierarchy = any(p in ("ban_members", "kick_members") for p in missing)
		steps = []
		if is_channel :
			steps.append(
				f"Open **{channel.name}** → **Edit Channel → Permissions**, add the **Banwatch** role "
				"(or the bot itself), and enable the permissions listed above."
			)
		steps.append(
			"Or grant them server-wide: **Server Settings → Roles → Banwatch**, then toggle the "
			"permissions above **on**."
		)
		if needs_hierarchy :
			steps.append(
				"To ban or kick members, drag the **Banwatch** role **above** the members it needs to act on "
				"(**Server Settings → Roles**) — a bot can only ban/kick users whose highest role sits below its own."
			)
		steps.append("When you're done, trigger the action again (or re-run setup) — this notice will clear on its own.")
		embed.add_field(
			name="How to fix",
			value="\n".join(f"{i}. {s}" for i, s in enumerate(steps, start=1))[:1024],
			inline=False,
		)
		embed.add_field(
			name="📖 Guides",
			value=(
				f"• [Banwatch permissions guide]({BANWATCH_PERMISSIONS_DOCS})\n"
				f"• [Discord: setting up permissions]({DISCORD_PERMISSIONS_DOCS})"
			),
			inline=False,
		)
		embed.timestamp = discord.utils.utcnow()
		embed.set_footer(text=f"Server: {guild.name} • Sent to you because you manage this server.")
		return embed

	@staticmethod
	def _can_embed(target) -> bool :
		"""Whether ``target`` can render an embed. DMs always can; a guild channel can only if the
		bot has embed_links there."""
		if isinstance(target, (discord.abc.GuildChannel, discord.Thread)) :
			return not check_missing_channel_permissions(target, ["embed_links"])
		return True

	@staticmethod
	def _links_view() -> discord.ui.View :
		"""A view with link buttons to the docs. Link buttons render even when the target is
		missing embed_links, so the guides stay reachable in the worst case."""
		view = discord.ui.View()
		view.add_item(discord.ui.Button(label="Banwatch: Permissions", style=discord.ButtonStyle.link,
		                                url=BANWATCH_PERMISSIONS_DOCS))
		view.add_item(discord.ui.Button(label="Discord: Permissions Help", style=discord.ButtonStyle.link,
		                                url=DISCORD_PERMISSIONS_DOCS))
		return view

	@classmethod
	async def notify(cls, guild: discord.Guild, *, channel=None, missing: list[str] | None = None,
	                 purpose: str | None = None, user=None, throttle: bool = True) -> bool :
		"""Deliver a permission notice for ``guild``.

		If ``missing`` is not supplied and a channel is given, the missing channel permissions are
		computed automatically.

		Delivery prefers a place staff can see and act on fast: the configured mod channel, then any
		accessible text channel, then a DM to ``user`` (whoever triggered the action), then a DM to
		the guild owner.

		``throttle`` controls the anti-spam cooldown: pass ``True`` (default) for
		loops/events/background sends so the same problem is reported at most once an hour, and
		``False`` for command-driven checks so the user gets a fresh answer every time they ask.

		Returns True if a notice was sent. Never raises — it is safe to call from an exception
		handler.
		"""
		try :
			if guild is None :
				return False

			if missing is None and isinstance(channel, (discord.abc.GuildChannel, discord.Thread)) :
				missing = check_missing_channel_permissions(channel, DEFAULT_CHANNEL_PERMS)
			missing = [m for m in (missing or []) if m]
			if not missing :
				return False

			# Commands (throttle=False) always report; loops/events are rate-limited per problem.
			if throttle :
				channel_id = getattr(channel, "id", "guild")
				dedupe_key = f"{channel_id}:{','.join(sorted(missing))}:{purpose or ''}"
				if not cls._should_send(guild.id, dedupe_key) :
					logging.debug(f"Permission notice for {guild.id} ({dedupe_key}) suppressed by cooldown.")
					return False

			embed = cls.build_embed(guild, channel=channel, missing=missing, purpose=purpose)
			# Plain-text fallback used only for targets that can't render embeds (a channel missing
			# `embed_links` — often the very permission that's missing). Like the embed, it always
			# names the server (and channel) since it may land in a DM to an owner who runs several
			# servers.
			if isinstance(channel, (discord.abc.GuildChannel, discord.Thread)) :
				location_text = f"#{channel.name} in {guild.name}"
			else :
				location_text = guild.name
			perms_text = ', '.join(humanize_permission(p) for p in missing)
			fallback = (
				f"⚠️ **Banwatch is missing permissions in {location_text}**\n"
				f"Missing: {perms_text}"
				+ (f" — needed so I can {purpose}" if purpose else "") + "\n"
				f"How to fix: enable these for the **Banwatch** role (**Server Settings → Roles**, "
				f"or the channel's permissions), then trigger the action again.\n"
				f"Guide: <{BANWATCH_PERMISSIONS_DOCS}>"
			)

			# Delivery cascade, in order of how quickly staff can act on it: mod channel -> any
			# accessible channel -> the triggering user's DMs -> the owner's DMs. Never target the
			# broken channel itself. ConfigData is lazy-imported to avoid a circular import at
			# module load (it pulls in singleton/transactions which may import back here).
			from classes.configdata import ConfigData
			from data.config.mappings import Channels

			targets = []
			mod_channel_id = ConfigData().get_key_or_none(guild.id, Channels.MOD_CHANNEL)
			# get_key coerces unset/"false"/"0" values to the boolean False, and bool is a subclass
			# of int, so guard against both before treating it as a channel id.
			if isinstance(mod_channel_id, int) and not isinstance(mod_channel_id, bool) :
				mod_channel = guild.get_channel(mod_channel_id)
				if mod_channel is not None and mod_channel != channel :
					targets.append(mod_channel)
			accessible = find_first_accessible_text_channel(guild)
			if accessible is not None and accessible != channel and accessible not in targets :
				targets.append(accessible)
			if user is not None and user not in targets :
				targets.append(user)
			if guild.owner is not None and guild.owner not in targets :
				targets.append(guild.owner)

			for target in targets :
				try :
					# Use the embed where it will render; fall back to plain text only where the
					# target can't show embeds (channel missing embed_links). Fresh view per send:
					# link buttons carry no state, but avoid reusing one View across messages.
					if cls._can_embed(target) :
						await target.send(embed=embed, view=cls._links_view())
					else :
						await target.send(content=fallback, view=cls._links_view())
					logging.info(f"Sent permission notice to {getattr(target, 'name', target)} in {guild.name} ({guild.id}).")
					return True
				except (discord.Forbidden, discord.HTTPException) as e :
					logging.debug(f"Permission notice delivery to {target} failed: {e}")
					continue

			logging.warning(f"Could not deliver permission notice for {guild.name} ({guild.id}); no reachable target.")
			return False
		except Exception as e :
			logging.error(f"Failed to build/send permission notice for guild {getattr(guild, 'id', '?')}: {e}", exc_info=True)
			return False
