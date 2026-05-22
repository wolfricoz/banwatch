from datetime import timedelta
from enum import StrEnum
from typing import Optional

import discord
from discord_py_utilities.messages import send_message

from classes.configdata import ConfigData
from data.config.mappings import Channels, WarningConfigs
from database.transactions.ServerTransactions import ServerTransactions
from database.transactions.WarningTransactions import WarningTransactions


class PunishmentOptions(StrEnum) :
	BAN = "BAN"
	KICK = "KICK"
	TIMEOUT = "TIMEOUT"


class Punishments :

	def __init__(self) :
		pass

	def load_warnings(self, guild_id: int, user_id: int) -> int :
		"""
		Gets a warning count from the guild and the user's id.
		:param guild_id:
		:param user_id:
		:return:
		"""
		return WarningTransactions().count_warnings(user_id, guild_id)

	async def check_punishments(self, guild: discord.Member, member: discord.Member) -> Optional[PunishmentOptions] :
		"""Checks the punishments the user should receive based on count."""
		result = None
		warning_count = self.load_warnings(guild.id, member.id)

		timeout_check = self._evaluate_threshold(guild.id, warning_count, WarningConfigs.TIMEOUT_WARNINGS,
		                                         PunishmentOptions.TIMEOUT)
		if timeout_check is not None :
			result: PunishmentOptions = timeout_check

		kick_check = self._evaluate_threshold(guild.id, warning_count, WarningConfigs.KICK_WARNINGS, PunishmentOptions.KICK)
		if kick_check is not None :
			result: PunishmentOptions = kick_check

		ban_check = self._evaluate_threshold(guild.id, warning_count, WarningConfigs.BAN_WARNINGS, PunishmentOptions.BAN)
		if ban_check is not None :
			result: PunishmentOptions = ban_check

		# --- Execute action here ---
		await self.execute_punishment(guild, member, result, warning_count)

	async def execute_punishment(self, guild: discord.Guild, user: discord.Member, result: PunishmentOptions,
	                             warning_count) -> None :
		"""Executes the determined action on the user."""
		reason_message = "Triggered by warning system, user has passed the warning threshold for this punishment."

		match result :
			case PunishmentOptions.TIMEOUT :
				print(f"Timing out {user.id} in guild {guild.id}")
				await user.timeout(timedelta(hours=24), reason=reason_message)

			case PunishmentOptions.KICK :
				server = ServerTransactions().get(guild.id)

				print(f"Kicking {user.id} from guild {guild.id}")
				reason_message = (
					f"You have been kicked from {guild.name} because your account has reached the maximum allowed threshold for warnings. You may rejoin the server, but please review the rules to avoid further moderation actions, as subsequent infractions will lead to a permanent ban."
					f"\n\n"
					f"You can rejoin here: {server.invite}")
				try :
					await user.send(reason_message)
				except discord.errors.Forbidden or discord.errors.NotFound :
					pass

				await user.kick(reason=reason_message)

			case PunishmentOptions.BAN :
				print(f"Banning {user.id} from guild {guild.id}")

				reason_message = f"You have been permanently banned from {guild.name} for repeatedly violating the server rules. Your account has reached the maximum threshold of warnings allowed ({warning_count} warnings). If you believe this is an error, please contact a member of the administration team."
				embed = discord.Embed(title=f"{user.name} ({user.id}) banned!", description=f"{reason_message}",
				                      color=discord.Color.red())
				embed.set_footer(text=f"Moderator: {user.name}, was the user informed? Yes")
				mod_channel = await ConfigData().get_channel(guild, Channels.MOD_CHANNEL)
				await send_message(mod_channel, embed=embed)
				try :
					await user.send(f"You have been banned from {guild.name} for `{reason_message}`")
				except discord.errors.Forbidden or discord.errors.NotFound :
					pass

			case _ :
				# Fallback for unexpected cases
				pass

	# === Helper functions ===

	@staticmethod
	def _evaluate_threshold(
			guild_id: int,
			warning_count: int,
			config_key: WarningConfigs,
			punishment: PunishmentOptions
	) -> Optional[PunishmentOptions] :
		"""Generic helper to evaluate warning thresholds against a configuration key."""
		conf = ConfigData().get_key(guild_id, config_key, None)
		if not conf :
			return None

		return punishment if warning_count >= int(conf) else None
