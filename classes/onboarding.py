import logging

import discord
from discord_py_utilities.permissions import find_first_accessible_text_channel

from classes.queue import queue
from view.v2.OnboardingLayout import OnboardingLayout


class Onboarding :
	"""This module handles onboarding new servers, helping them get started with the bot."""

	async def join_message(self, guild: discord.Guild) :
		queue().add(self.deliver_join_message(guild))

	@staticmethod
	async def deliver_join_message(guild: discord.Guild) -> bool :
		"""Posts the welcome layout in the first channel we can reach, else DMs it to the owner.

		A bot invited without channel permissions has nowhere to post, and the welcome is the only
		place a new owner learns how to set Banwatch up; so the owner DM also says why it came by DM.
		Returns True if the welcome was delivered somewhere. Never raises.
		"""
		channel = find_first_accessible_text_channel(guild)
		if channel is not None :
			try :
				await channel.send(view=OnboardingLayout())
				return True
			except (discord.Forbidden, discord.HTTPException) as e :
				logging.info(f"Could not post the welcome message in #{channel.name} of {guild.name}({guild.id}): {e}")

		owner = guild.owner
		if owner is None :
			logging.warning(f"No channel or owner to send the welcome message to in {guild.name}({guild.id}).")
			return False
		try :
			await owner.send(view=OnboardingLayout())
			await owner.send(
				f"⚠️ I couldn't post this welcome message in **{guild.name}**: I don't have **View Channel** and "
				"**Send Messages** in any of its text channels. Give my role those permissions in at least your "
				"moderators' channel, then run `/config permissioncheck` there to see what else I need.")
			return True
		except (discord.Forbidden, discord.HTTPException) as e :
			logging.warning(f"Could not deliver the welcome message for {guild.name}({guild.id}) anywhere: {e}")
			return False
