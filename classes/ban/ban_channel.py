"""Resolving the channel Banwatch talks to a server in, and what to do when there isn't one.

Every ban message a server sees goes to its configured mod channel. When that channel is
never set, has been deleted, or the bot cannot post in it, the ban flow used to end in a DM
to the owner - which is dropped silently whenever the owner has DMs closed - or in nothing
at all. The server then has no way of knowing that its bans are not being handled.

Instead, we post a warning into a random channel we *can* post in. The fallback channel is
chosen because it is reachable, not because it is private: it may well be a channel the
whole server can read. The warning therefore never names the banned user, the ban reason or
anything else about the ban - it only says that Banwatch has nowhere to talk and how to fix
that. Ban details go to the mod channel or nowhere.
"""
import logging
import random
import time

import discord
from discord_py_utilities.permissions import check_missing_channel_permissions

from classes.configdata import ConfigData
from data.config.mappings import Channels

# The bare minimum needed to deliver a message. Embeds are nice-to-have; see _can_embed.
SEND_PERMISSIONS = ["view_channel", "send_messages"]

CONFIGURATION_DOCS = "https://wolfricoz.github.io/banwatch/configuration.html"

# Why the mod channel is unusable. Only affects the wording of the warning.
UNSET = "unset"
UNREACHABLE = "unreachable"

# Default anti-spam window, used for things the server itself just did: a server that bans ten
# people in a row should be told once, not ten times.
DEFAULT_COOLDOWN = 3600
# For background paths the server did not trigger - the two-hourly ban sweep, and bans arriving
# from other servers - once a day is plenty. Without this, a busy network would warn a
# mod-channel-less guild every few minutes.
SLOW_COOLDOWN = 86400
# guild_id -> {source: last warning, time.monotonic()}. In-memory only: it resets on
# restart, which at worst re-sends one warning per deploy.
_last_warning: dict[int, dict[str, float]] = {}


# ============================================================
def can_send(channel) -> bool :
	"""Whether the bot can actually post in ``channel`` right now."""
	if not isinstance(channel, (discord.TextChannel, discord.Thread)) :
		return False
	try :
		return not check_missing_channel_permissions(channel, SEND_PERMISSIONS)
	except Exception as e :
		# permissions_for needs guild.me; if the member cache is cold, treat it as unusable
		# rather than letting a permission lookup break the ban flow.
		logging.debug(f"Could not read permissions for channel {getattr(channel, 'id', '?')}: {e}")
		return False


# ============================================================
def pick_fallback_channel(guild: discord.Guild, exclude=None) -> discord.TextChannel | None :
	"""Pick a random text channel the bot can post in, or None if there is no such channel.

	Random rather than first-match on purpose: the first channel in the list is usually
	#rules or #announcements, and always shouting into the same one is worse than spreading
	the warnings around."""
	exclude_id = getattr(exclude, "id", None)
	candidates = [c for c in guild.text_channels if c.id != exclude_id and can_send(c)]
	if not candidates :
		return None
	return random.choice(candidates)


# ============================================================
async def resolve_ban_channel(guild: discord.Guild) -> discord.TextChannel | None :
	"""The guild's configured mod channel, but only if we can post in it.

	Returns None when the channel is unset, deleted, or unusable - callers should treat that
	as "there is nowhere to send ban information" and warn via
	:func:`warn_missing_ban_channel`."""
	# optional=True: get_channel's own "no channel set" notice would otherwise fire alongside
	# ours. We want a single, ban-flow-specific warning.
	channel = await ConfigData().get_channel(guild, Channels.MOD_CHANNEL, optional=True)
	if channel is None :
		return None
	if not can_send(channel) :
		missing = check_missing_channel_permissions(channel, SEND_PERMISSIONS)
		logging.info(
			f"Cannot post in the configured mod channel #{channel.name} of {guild.name}({guild.id}): "
			f"missing {', '.join(missing)}")
		return None
	return channel


# ============================================================
def _should_warn(guild_id: int, source: str, cooldown: int) -> bool :
	now = time.monotonic()
	guild_map = _last_warning.setdefault(guild_id, {})
	last = guild_map.get(source)
	# "never warned" has to be None, not 0.0: monotonic() counts from an arbitrary point (on
	# Windows, system boot), so `now - 0.0 < cooldown` silently swallows the very first warning
	# whenever the host has been up for less than the cooldown.
	if last is not None and now - last < cooldown :
		return False
	guild_map[source] = now
	return True


# ============================================================
def _can_embed(channel) -> bool :
	try :
		return not check_missing_channel_permissions(channel, ["embed_links"])
	except Exception :
		return False


# ============================================================
def _fix_steps(problem: str) -> list[str] :
	steps = []
	if problem == UNSET :
		steps.append("Run `/config change` and pick **Mod Channel**, then choose the channel your staff use.")
	else :
		steps.append(
			"Give Banwatch **View Channel** and **Send Messages** (and ideally **Embed Links**) in your mod "
			"channel, or run `/config change` → **Mod Channel** to point it at a channel it can use.")
	steps.append("Run `/config permissioncheck` to confirm Banwatch has everything it needs.")
	steps.append(
		"Banwatch rescans every server every couple of hours, so bans made while it had nowhere to post are "
		"picked up on the next scan once this is fixed.")
	return steps


# ============================================================
def _warning_embed(guild: discord.Guild, problem: str) -> discord.Embed :
	embed = discord.Embed(
		title="⚠️ Banwatch has nowhere to post ban information",
		colour=discord.Colour.orange(),
	)
	if problem == UNSET :
		embed.description = (
			f"**{guild.name}** has no moderation channel set, so Banwatch cannot show ban notifications or ask "
			"your staff whether a ban should be shared. **Bans made here are not being shared with the Banwatch "
			"network, and bans from other servers are not being reported to you.**"
		)
	else :
		embed.description = (
			f"Banwatch cannot post in the moderation channel configured for **{guild.name}** - it was either "
			"deleted or Banwatch is missing permissions there. **Bans made here are not being shared with the "
			"Banwatch network, and bans from other servers are not being reported to you.**"
		)
	embed.add_field(
		name="How to fix",
		value="\n".join(f"{i}. {s}" for i, s in enumerate(_fix_steps(problem), start=1))[:1024],
		inline=False,
	)
	embed.add_field(name="📖 Guide", value=f"[Configuring Banwatch]({CONFIGURATION_DOCS})", inline=False)
	embed.timestamp = discord.utils.utcnow()
	embed.set_footer(text=f"Posted here because Banwatch has no usable moderation channel in {guild.name}.")
	return embed


# ============================================================
def _warning_text(guild: discord.Guild, problem: str) -> str :
	opening = (
		f"⚠️ **{guild.name} has no moderation channel set**"
		if problem == UNSET else
		f"⚠️ **Banwatch cannot post in the moderation channel configured for {guild.name}**"
	)
	steps = "\n".join(f"{i}. {s}" for i, s in enumerate(_fix_steps(problem), start=1))
	return (
		f"{opening}\n"
		"Bans made here are not being shared with the Banwatch network, and bans from other servers are not "
		f"being reported to you.\n{steps}\n"
		f"Guide: <{CONFIGURATION_DOCS}>\n"
		f"-# Posted here because Banwatch has no usable moderation channel in {guild.name}."
	)


# ============================================================
async def warn_missing_ban_channel(guild: discord.Guild, *, problem: str = UNSET, source: str = "ban",
                                   cooldown: int = DEFAULT_COOLDOWN, exclude=None) -> bool :
	"""Warn a server, in a random channel, that Banwatch has nowhere to post ban information.

	:param problem: ``UNSET`` (no mod channel configured) or ``UNREACHABLE`` (configured but
		deleted / not writable). Only changes the wording.
	:param source: what triggered the warning ("ban", "sweep", "broadcast"). Warnings are
		rate limited per guild *per source*, so a slow background sweep cannot mute the
		warning a live ban would produce.
	:param cooldown: seconds before this guild/source pair may warn again.
	:param exclude: a channel to never pick - normally the broken mod channel itself.

	The message deliberately contains no ban details; the fallback channel may be public.
	Returns True if a warning was delivered. Never raises: it is called from the ban path and
	must not be able to break it.
	"""
	try :
		if guild is None :
			return False
		if not _should_warn(guild.id, source, cooldown) :
			logging.debug(f"Missing-ban-channel warning for {guild.id} ({source}) suppressed by cooldown.")
			return False

		channel = pick_fallback_channel(guild, exclude=exclude)
		if channel is None :
			# No channel at all is writable. The owner's DMs are the only thing left; this is
			# the fallback's fallback, not the primary path.
			logging.warning(
				f"No channel available to warn {guild.name}({guild.id}) about its missing mod channel, "
				f"trying the owner's DMs.")
			if guild.owner is None :
				return False
			try :
				await guild.owner.send(embed=_warning_embed(guild, problem))
				return True
			except (discord.Forbidden, discord.HTTPException) as e :
				logging.warning(f"Could not DM the owner of {guild.name}({guild.id}) either: {e}")
				return False

		try :
			if _can_embed(channel) :
				await channel.send(embed=_warning_embed(guild, problem))
			else :
				await channel.send(_warning_text(guild, problem))
			logging.info(
				f"Warned {guild.name}({guild.id}) in #{channel.name} that its mod channel is {problem} "
				f"(source: {source}).")
			return True
		except (discord.Forbidden, discord.HTTPException) as e :
			# can_send() read the cached permissions; the send is the only real test. Let the
			# cooldown stand so a broken guild cannot make us hammer the API every ban.
			logging.warning(f"Failed to warn {guild.name}({guild.id}) in #{channel.name}: {e}")
			return False
	except Exception as e :
		logging.error(f"Failed to warn guild {getattr(guild, 'id', '?')} about its ban channel: {e}", exc_info=True)
		return False
