import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext.commands import Bot, GroupCog
from discord_py_utilities.messages import send_response

from classes.configer import Configer
from database.transactions.ServerTransactions import ServerTransactions
from project.data import CONTACT_EMAIL, DOCUMENTATION, VERSION

# ============================================================
# Bot-specific settings. This cog is shared between ageverifier, banwatch and thread-weaver;
# everything below the next divider is identical in each bot, only this block differs.
BOT_NAME = "Banwatch"
DOCS_URL = DOCUMENTATION
PRIVACY_URL = "https://wolfricoz.github.io/banwatch/publicprivacy"


def support_invite() -> str | None :
	"""Returns the support server's invite, or None if it isn't available."""
	try :
		server = ServerTransactions().get(int(os.getenv("GUILD")))
		if server is not None and server.invite :
			return server.invite
	except Exception as e :
		logging.warning(f"Could not resolve the support server invite: {e}")
	return None


async def is_blacklisted(user_id: int) -> bool :
	try :
		return bool(await Configer.is_user_blacklisted(user_id))
	except Exception as e :
		logging.warning(f"Could not check the user blacklist: {e}")
		return False


# ============================================================
# Shared support cog code.

SUPPORT_FORUM = "SUPPORT_FORUM"
SUGGESTION_FORUM = "SUGGESTION_FORUM"
COOLDOWN = timedelta(minutes=10)
# Permissions listed as missing in the diagnostics of a ticket, so staff don't have to ask for them.
DIAGNOSTIC_PERMISSIONS = ["view_channel", "send_messages", "embed_links", "attach_files", "read_message_history",
                          "manage_messages", "manage_roles", "manage_channels", "manage_threads", "kick_members",
                          "ban_members", "create_instant_invite"]

_cooldowns: dict[tuple[int, str], datetime] = {}
_started = datetime.now(tz=timezone.utc)


@dataclass(frozen=True)
class TicketKind :
	name: str
	forum_env: str
	color: discord.Color
	diagnostics: bool = False
	vote: bool = False


KINDS = {
	"Help"       : TicketKind("Help", SUPPORT_FORUM, discord.Color.blue(), diagnostics=True),
	"Feedback"   : TicketKind("Feedback", SUPPORT_FORUM, discord.Color.green()),
	"Bug"        : TicketKind("Bug", SUPPORT_FORUM, discord.Color.red(), diagnostics=True),
	"Report"     : TicketKind("Report", SUPPORT_FORUM, discord.Color.orange(), diagnostics=True),
	"Suggestion" : TicketKind("Suggestion", SUGGESTION_FORUM, discord.Color.purple(), vote=True),
}


async def reply(interaction: discord.Interaction, message: str, **kwargs) :
	"""Ephemeral reply that works whether or not the interaction has already been responded to."""
	if interaction.response.is_done() :
		return await interaction.followup.send(message, ephemeral=True, **kwargs)
	return await interaction.response.send_message(message, ephemeral=True, **kwargs)


def contact_line() -> str :
	routes = []
	if invite := support_invite() :
		routes.append(f"join our support server: {invite}")
	if CONTACT_EMAIL :
		routes.append(f"email us at {CONTACT_EMAIL}")
	return f"You can also {' or '.join(routes)}." if routes else ""


async def get_forum(bot: discord.Client, env_key: str) -> discord.ForumChannel | None :
	try :
		channel_id = int(os.getenv(env_key))
	except (TypeError, ValueError) :
		logging.warning(f"{env_key} is not set, support tickets can't be delivered")
		return None
	try :
		channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
	except discord.HTTPException as e :
		logging.error(f"Could not fetch the support forum {channel_id}: {e}")
		return None
	if not isinstance(channel, discord.ForumChannel) :
		logging.error(f"{env_key} ({channel_id}) is not a forum channel")
		return None
	return channel


def find_tags(forum: discord.ForumChannel, *names: str) -> list[discord.ForumTag] :
	wanted = {name.lower() for name in names if name}
	return [tag for tag in forum.available_tags if tag.name.lower() in wanted][:5]


def diagnostics(interaction: discord.Interaction) -> str :
	lines = [f"Version: {VERSION}"]
	guild = interaction.guild
	me = getattr(guild, "me", None)
	if me is None :
		return "\n".join(lines)
	permissions = me.guild_permissions
	if permissions.administrator :
		lines.append("Permissions: Administrator")
	else :
		missing = [name.replace("_", " ").title() for name in DIAGNOSTIC_PERMISSIONS if not getattr(permissions, name)]
		lines.append(f"Missing permissions: {', '.join(missing) if missing else 'none'}")
	lines.append(f"Top role: {me.top_role.name} (position {me.top_role.position} of {len(guild.roles)})")
	return "\n".join(lines)


def ticket_details(message: discord.Message) -> tuple[int | None, str, str] :
	"""Reads the user id, kind and title back from a ticket's embed footer, so no database is needed."""
	if not message.embeds :
		return None, "", ""
	embed = message.embeds[0]
	parts = dict(part.split(": ", 1) for part in (embed.footer.text or "").split(" | ") if ": " in part)
	try :
		user_id = int(parts.get("User ID"))
	except (TypeError, ValueError) :
		user_id = None
	return user_id, parts.get("Kind", ""), embed.title or ""


async def can_submit(interaction: discord.Interaction, kind: str) -> bool :
	if await is_blacklisted(interaction.user.id) :
		await reply(interaction, f"You are not able to submit tickets to the {BOT_NAME} team.")
		return False
	expires = _cooldowns.get((interaction.user.id, kind))
	if expires and expires > datetime.now(tz=timezone.utc) :
		await reply(interaction,
		            f"You have recently submitted a {kind.lower()} ticket, you can submit another {discord.utils.format_dt(expires, 'R')}.")
		return False
	return True


async def submit_ticket(interaction: discord.Interaction, kind: str, title: str,
                        fields: list[tuple[str, str]]) :
	"""Posts a ticket in the matching support forum and lets the user know how it went."""
	settings = KINDS[kind]
	user = interaction.user
	await interaction.response.defer(ephemeral=True, thinking=True)
	forum = await get_forum(interaction.client, settings.forum_env)
	if forum is None :
		return await reply(interaction, f"Sorry, we could not deliver your {kind.lower()} ticket. {contact_line()}")

	embed = discord.Embed(title=f"{kind}: {title}"[:256], color=settings.color, timestamp=datetime.now(tz=timezone.utc))
	embed.set_author(name=f"{user} ({user.id})", icon_url=user.display_avatar.url)
	for name, value in fields :
		if value :
			embed.add_field(name=name, value=str(value)[:1024], inline=False)
	embed.add_field(name="Submitted by", value=f"{user.mention} `{user}` ({user.id})")
	guild = interaction.guild
	embed.add_field(name="Server",
	                value=f"{guild.name} ({guild.id}), {guild.member_count} members" if guild and guild.name else "Direct message")
	if settings.diagnostics :
		embed.add_field(name="Diagnostics", value=diagnostics(interaction), inline=False)
	embed.set_footer(text=f"User ID: {user.id} | Kind: {kind} | Bot: {BOT_NAME}")

	try :
		created = await forum.create_thread(name=f"[{BOT_NAME}] {kind}: {title}"[:100], embed=embed,
		                                    view=TicketControls(), applied_tags=find_tags(forum, BOT_NAME, kind))
	except discord.HTTPException as e :
		logging.error(f"Could not create a {kind} ticket for {user.id} in {forum.id}: {e}", exc_info=True)
		return await reply(interaction, f"Sorry, we could not deliver your {kind.lower()} ticket. {contact_line()}")

	if settings.vote :
		for emoji in ("👍", "👎") :
			try :
				await created.message.add_reaction(emoji)
			except discord.HTTPException :
				break

	_cooldowns[(user.id, kind)] = datetime.now(tz=timezone.utc) + COOLDOWN
	await reply(interaction,
	            f"Thank you! Your {kind.lower()} ticket has been sent to the {BOT_NAME} team. "
	            f"When staff reply, you will receive a direct message from me, so keep your DMs open. {contact_line()}")


class TicketModal(discord.ui.Modal) :
	"""A form for one ticket kind; `context` holds values collected from slash command options."""

	def __init__(self, kind: str, inputs: list[discord.ui.TextInput], title_input: discord.ui.TextInput | None = None,
	             context: list[tuple[str, str]] | None = None, ticket_title: str | None = None) :
		super().__init__(title=f"{BOT_NAME} {kind}"[:45])
		self.kind = kind
		self.inputs = inputs
		self.title_input = title_input
		self.context = context or []
		self.ticket_title = ticket_title
		for item in inputs :
			self.add_item(item)

	async def on_submit(self, interaction: discord.Interaction) :
		fields = [(item.label, item.value) for item in self.inputs if item is not self.title_input]
		if self.title_input :
			title = self.title_input.value
		else :
			title = self.ticket_title or next((value for _, value in fields if value), self.kind)
		await submit_ticket(interaction, self.kind, title.replace("\n", " ")[:80], self.context + fields)

	async def on_error(self, interaction: discord.Interaction, error: Exception) :
		logging.error(f"Error in the {self.kind} support form: {error}", exc_info=True)
		await reply(interaction, f"Something went wrong while sending your ticket. {contact_line()}")


class ReplyModal(discord.ui.Modal, title="Reply to ticket") :
	answer = discord.ui.TextInput(label="Reply", style=discord.TextStyle.paragraph, max_length=2000)

	def __init__(self, message: discord.Message) :
		super().__init__()
		self.message = message

	async def on_submit(self, interaction: discord.Interaction) :
		user_id, kind, title = ticket_details(self.message)
		await interaction.response.defer(ephemeral=True)
		delivered = False
		if user_id :
			embed = discord.Embed(title=f"Reply from the {BOT_NAME} team", description=self.answer.value,
			                      color=discord.Color.blue(), timestamp=datetime.now(tz=timezone.utc))
			embed.add_field(name="Your ticket", value=title[:1024] or kind)
			embed.set_footer(text="Replies to this message are not read. Use /support to follow up.")
			try :
				user = interaction.client.get_user(user_id) or await interaction.client.fetch_user(user_id)
				await user.send(embed=embed)
				delivered = True
			except discord.HTTPException as e :
				logging.info(f"Could not DM support reply to {user_id}: {e}")

		record = discord.Embed(description=self.answer.value, color=discord.Color.blue())
		record.set_author(name=f"Reply by {interaction.user}", icon_url=interaction.user.display_avatar.url)
		record.set_footer(text="Delivered by DM" if delivered else "Could not DM the user, their DMs may be closed")
		await self.message.channel.send(embed=record)
		await reply(interaction, "Reply sent." if delivered else "The user could not be reached by DM, the reply was only posted here.")

	async def on_error(self, interaction: discord.Interaction, error: Exception) :
		logging.error(f"Error while replying to a support ticket: {error}", exc_info=True)
		await reply(interaction, "Something went wrong while sending the reply.")


class TicketControls(discord.ui.View) :
	"""Staff controls on every ticket. Persistent: the ticket's user is read back from the embed footer."""

	def __init__(self) :
		super().__init__(timeout=None)

	async def interaction_check(self, interaction: discord.Interaction) -> bool :
		if isinstance(interaction.user, discord.Member) and interaction.channel.permissions_for(interaction.user).manage_threads :
			return True
		await reply(interaction, "Only support staff can use these buttons.")
		return False

	@discord.ui.button(label="Reply", emoji="✉️", style=discord.ButtonStyle.primary, custom_id="support:reply")
	async def reply_button(self, interaction: discord.Interaction, button: discord.ui.Button) :
		await interaction.response.send_modal(ReplyModal(interaction.message))

	@discord.ui.button(label="Resolve", emoji="✅", style=discord.ButtonStyle.success, custom_id="support:resolve")
	async def resolve_button(self, interaction: discord.Interaction, button: discord.ui.Button) :
		thread = interaction.channel
		user_id, kind, title = ticket_details(interaction.message)
		await interaction.response.send_message(f"Ticket resolved by {interaction.user.mention}.",
		                                        allowed_mentions=discord.AllowedMentions.none())
		if user_id :
			try :
				user = interaction.client.get_user(user_id) or await interaction.client.fetch_user(user_id)
				await user.send(f"Your {BOT_NAME} ticket **{title}** has been marked as resolved. Thank you for reaching out!")
			except discord.HTTPException as e :
				logging.info(f"Could not DM ticket resolution to {user_id}: {e}")
		if not isinstance(thread, discord.Thread) :
			return
		try :
			tags = list(thread.applied_tags)
			if isinstance(thread.parent, discord.ForumChannel) :
				tags += [tag for tag in find_tags(thread.parent, "Resolved") if tag not in tags]
			await thread.edit(archived=True, applied_tags=tags[:5])
		except discord.HTTPException as e :
			logging.warning(f"Could not archive resolved ticket {thread.id}: {e}")


class Support(GroupCog, name="support", description="Contact the developers: ask for help, give feedback or report a problem.") :
	"""
	Reach the developers without leaving your server.
	Ask for help, send feedback, report a bug or abuse, or suggest a feature. Your ticket is posted in our support
	server and staff replies are sent to you by direct message, so keep your DMs open.
	"""

	def __init__(self, bot: Bot) :
		self.bot = bot

	async def cog_load(self) :
		self.bot.add_view(TicketControls())

	@app_commands.command(name="help", description="Ask the developers for help with the bot.")
	async def support_help(self, interaction: discord.Interaction) :
		"""
		Asks the developers for help. Your question is posted in our support server together with basic information
		about your server (such as missing bot permissions), and staff will reply to you by direct message.

		**Permissions:**
		- None required for the user.
		"""
		if not await can_submit(interaction, "Help") :
			return
		topic = discord.ui.TextInput(label="Topic", placeholder="e.g. Setting up the verification", max_length=80)
		question = discord.ui.TextInput(label="What do you need help with?", style=discord.TextStyle.paragraph,
		                                max_length=1024)
		await interaction.response.send_modal(TicketModal("Help", [topic, question], topic))

	@app_commands.command(name="feedback", description="Tell the developers what you think of the bot.")
	@app_commands.describe(rating="How would you rate the bot, from 1 to 5?")
	async def feedback(self, interaction: discord.Interaction, rating: app_commands.Range[int, 1, 5] = None) :
		"""
		Sends your feedback to the developers. Tell us what you like, what could be better, or anything else on your mind.

		**Permissions:**
		- None required for the user.
		"""
		if not await can_submit(interaction, "Feedback") :
			return
		text = discord.ui.TextInput(label="Your feedback", style=discord.TextStyle.paragraph, max_length=1024)
		context = [("Rating", "⭐" * rating)] if rating else []
		await interaction.response.send_modal(TicketModal("Feedback", [text], context=context))

	@app_commands.command(name="bug", description="Report a bug in the bot.")
	@app_commands.describe(severity="How badly does this bug affect you?")
	@app_commands.choices(severity=[
		app_commands.Choice(name="Low: minor annoyance", value="Low"),
		app_commands.Choice(name="Medium: a feature doesn't work", value="Medium"),
		app_commands.Choice(name="High: the bot is barely usable", value="High"),
		app_commands.Choice(name="Critical: the bot doesn't work at all", value="Critical"),
	])
	async def bug(self, interaction: discord.Interaction, severity: app_commands.Choice[str]) :
		"""
		Reports a bug to the developers. Describe what happened, how to make it happen again and what you expected instead.
		Basic information about your server is added automatically.

		**Permissions:**
		- None required for the user.
		"""
		if not await can_submit(interaction, "Bug") :
			return
		title = discord.ui.TextInput(label="Short description", max_length=80)
		happened = discord.ui.TextInput(label="What happened?", style=discord.TextStyle.paragraph, max_length=1024)
		steps = discord.ui.TextInput(label="Steps to reproduce", style=discord.TextStyle.paragraph, max_length=1024,
		                             required=False)
		expected = discord.ui.TextInput(label="What did you expect to happen?", style=discord.TextStyle.paragraph,
		                                max_length=1024, required=False)
		await interaction.response.send_modal(
			TicketModal("Bug", [title, happened, steps, expected], title, context=[("Severity", severity.value)]))

	@app_commands.command(name="report", description="Report a user or server abusing the bot.")
	@app_commands.describe(user="The user you are reporting", server_id="The ID of the server you are reporting")
	async def report(self, interaction: discord.Interaction, user: discord.User = None, server_id: str = None) :
		"""
		Reports a user or server that is abusing the bot to the developers. Include as much evidence as you can,
		such as message links or screenshot links. For problems with the bot itself, use the bug command instead.

		**Permissions:**
		- None required for the user.
		"""
		if not await can_submit(interaction, "Report") :
			return
		context = []
		if user :
			context.append(("Reported user", f"{user.mention} `{user}` ({user.id})"))
		if server_id :
			context.append(("Reported server", server_id[:30]))
		reason = discord.ui.TextInput(label="What happened?", style=discord.TextStyle.paragraph, max_length=1024)
		evidence = discord.ui.TextInput(label="Evidence (message or screenshot links)", style=discord.TextStyle.paragraph,
		                                max_length=1024, required=False)
		title = f"{user}" if user else f"server {server_id[:30]}" if server_id else None
		await interaction.response.send_modal(TicketModal("Report", [reason, evidence], context=context, ticket_title=title))

	@app_commands.command(name="suggest", description="Suggest a new feature for the bot.")
	async def suggest(self, interaction: discord.Interaction) :
		"""
		Suggests a new feature. Your suggestion is posted in our feature suggestions forum, where others can vote on it.

		**Permissions:**
		- None required for the user.
		"""
		if not await can_submit(interaction, "Suggestion") :
			return
		title = discord.ui.TextInput(label="Title", max_length=80)
		idea = discord.ui.TextInput(label="Describe your idea", style=discord.TextStyle.paragraph, max_length=1024)
		why = discord.ui.TextInput(label="How would it help you?", style=discord.TextStyle.paragraph, max_length=1024,
		                           required=False)
		await interaction.response.send_modal(TicketModal("Suggestion", [title, idea, why], title))

	@app_commands.command(name="info", description="Support server, documentation and bot status.")
	async def info(self, interaction: discord.Interaction) :
		"""
		Shows links to the support server, documentation and privacy policy, along with the bot's version, latency and uptime.

		**Permissions:**
		- None required for the user.
		"""
		embed = discord.Embed(title=f"{BOT_NAME} support", color=discord.Color.blurple(),
		                      description="Need a hand? Use `/support help`, or join the support server below.")
		embed.add_field(name="Version", value=VERSION)
		embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)} ms")
		embed.add_field(name="Online since", value=discord.utils.format_dt(_started, "R"))
		embed.add_field(name="Servers", value=str(len(self.bot.guilds)))
		if CONTACT_EMAIL :
			embed.add_field(name="Email", value=CONTACT_EMAIL)
		view = discord.ui.View()
		for label, url in (("Support server", support_invite()), ("Documentation", DOCS_URL), ("Privacy policy", PRIVACY_URL)) :
			if url :
				view.add_item(discord.ui.Button(label=label, url=url))
		await send_response(interaction, " ", embed=embed, view=view, ephemeral=True)


async def setup(bot: Bot) :
	await bot.add_cog(Support(bot))
