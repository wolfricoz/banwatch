"""Replying to an interaction without depending on channel permissions.

Interaction responses and followups are delivered through the interaction webhook, so they work
even when the bot can't view or post in the channel the command was run in. Anything that has to
reach the user who ran a command (errors especially) should go through here rather than
``interaction.channel.send``, which fails silently in exactly the channels where things go wrong.
"""
import logging

import discord


async def reply(interaction: discord.Interaction, content: str | None = None, *, embed: discord.Embed | None = None,
                ephemeral: bool = True) -> bool :
	"""Answer ``interaction``: the initial response if it's still open, otherwise a followup.

	Falls back to a plain channel message if both fail (e.g. the interaction token expired).
	Returns True if something was delivered. Never raises.
	"""
	kwargs = {"content" : content, "ephemeral" : ephemeral}
	if embed is not None :
		kwargs["embed"] = embed
	try :
		if not interaction.response.is_done() :
			await interaction.response.send_message(**kwargs)
		else :
			await interaction.followup.send(**kwargs)
		return True
	except (discord.HTTPException, discord.InteractionResponded) as e :
		logging.debug(f"Interaction reply failed, falling back to the channel: {e}")
	try :
		if interaction.channel is not None :
			if embed is not None :
				await interaction.channel.send(content, embed=embed)
			else :
				await interaction.channel.send(content)
			return True
	except Exception as e :
		logging.info(f"Could not deliver reply for interaction {getattr(interaction, 'id', '?')}: {e}")
	return False
