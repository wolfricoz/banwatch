import discord
from discord_py_utilities.messages import send_message

from classes.queue import queue
from view.v2.OnboardingLayout import OnboardingLayout


class Onboarding :
	"""This module handles onboarding new servers, helping them get started with the bot."""

	async def join_message(self, channel: discord.TextChannel | discord.Member) :
		queue().add(send_message(channel,
		                         f" ", view=OnboardingLayout()))
