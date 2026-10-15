import logging

import discord
from discord_py_utilities.messages import await_message, send_response


async def ask_for_message(interaction: discord.Interaction, prompt: str) -> discord.Message | bool :
	"""
	Asks the user for a message (e.g. evidence) and waits up to 10 minutes for it.

	await_message() posts the prompt without answering the interaction, so the interaction is acknowledged
	first: one that isn't answered within 3 seconds can never be responded to again. A timeout is reported
	to the user and returned as False, the same as typing cancel, instead of raising (BANWATCH-GF, BANWATCH-BX).
	"""
	if not interaction.response.is_done() :
		try :
			await interaction.response.defer(ephemeral=True)
		except discord.HTTPException as e :
			logging.info(f"Could not defer the interaction for {interaction.user.id}: {e}")
	try :
		return await await_message(interaction, prompt)
	except TimeoutError :
		try :
			await send_response(interaction, "You did not respond in time, please try again.", ephemeral=True, error_mode="ignore")
		except discord.HTTPException as e :
			logging.info(f"Could not tell {interaction.user.id} their prompt timed out: {e}")
		return False
