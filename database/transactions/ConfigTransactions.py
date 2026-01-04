import logging
from abc import ABC, abstractmethod

from sqlalchemy import Select

from database import current as db
from database.current import Config
from database.transactions.BanReasonTransactions import DatabaseTransactions


class ConfigDbTransactions(ABC) :

	@staticmethod
	@abstractmethod
	def config_update(guildid: int, key: str, value, overwrite=False) :
		if ConfigDbTransactions.key_exists_check(guildid, key) is False :
			return False
		exists = session.scalar(Select(db.Config).where(db.Config.guild == guildid, db.Config.key == key.upper()))
		exists.value = value
		DatabaseTransactions().commit(session)
		return True

	@staticmethod
	@abstractmethod
	def config_unique_add(guildid: int, key: str, value, overwrite=False) :
		# This function should check if the item already exists, if so it will override it or throw an error.

		value = str(value)
		if ConfigDbTransactions.key_exists_check(guildid, key, overwrite) is True and overwrite is False :
			logging.warning(
				f"Attempted to add unique key with data: {guildid}, {key}, {value}, and overwrite {overwrite}, but one already existed. No changes")
			return False
		if ConfigDbTransactions.key_exists_check(guildid, key, overwrite) is True :
			entries = session.scalars(
				Select(db.Config).where(db.Config.guild == guildid, db.Config.key == key.upper())).all()
			for entry in entries :
				session.delete(entry)
		item = db.Config(guild=guildid, key=key.upper(), value=value)
		session.add(item)
		DatabaseTransactions().commit(session)
		logging.info(f"Adding unique key with data: {guildid}, {key}, {value}, and overwrite {overwrite}")
		return True

	@staticmethod
	@abstractmethod
	def toggle_welcome(guildid: int, key: str, value) :
		# This function should check if the item already exists, if so it will override it or throw an error.
		value = str(value)
		guilddata = session.scalar(Select(Config).where(Config.guild == guildid, Config.key == key.upper()))
		if guilddata is None :
			ConfigDbTransactions.config_unique_add(guildid, key, value, overwrite=True)
			return
		guilddata.value = value
		DatabaseTransactions().commit(session)

		return True

	@staticmethod
	@abstractmethod
	def config_unique_get(guildid: int, key: str) :
		if ConfigDbTransactions.key_exists_check(guildid, key) is False :
			return
		exists = session.scalar(Select(db.Config).where(db.Config.guild == guildid, db.Config.key == key.upper()))
		return exists.value

	@staticmethod
	@abstractmethod
	def config_key_add(guildid: int, key: str, value, overwrite) :
		value = str(value)
		if ConfigDbTransactions.key_multiple_exists_check(guildid, key, value) is True :
			return False
		item = db.Config(guild=guildid, key=key.upper(), value=value)
		session.add(item)
		DatabaseTransactions().commit(session)

		return True

	@staticmethod
	@abstractmethod
	def key_multiple_exists_check(guildid: int, key: str, value) :
		exists = session.scalar(
			Select(db.Config).where(db.Config.guild == guildid, db.Config.key == key, db.Config.value == value))
		session.close()
		if exists is not None :
			return True
		return False

	@staticmethod
	@abstractmethod
	def config_key_remove(guildid: int, key: str, value) :
		if ConfigDbTransactions.key_multiple_exists_check(guildid, key, value) is False :
			return False
		exists = session.scalar(
			Select(db.Config).where(db.Config.guild == guildid, db.Config.key == key, db.Config.value == value))
		session.delete(exists)
		DatabaseTransactions().commit(session)

	@staticmethod
	@abstractmethod
	def config_unique_remove(guild_id: int, key: str) :
		if ConfigDbTransactions.key_exists_check(guild_id, key) is False :
			return False
		exists = session.scalar(
			Select(db.Config).where(db.Config.guild == guild_id, db.Config.key == key))
		session.delete(exists)
		DatabaseTransactions().commit(session)

	@staticmethod
	@abstractmethod
	def key_exists_check(guildid: int, key: str, overwrite=False) :
		exists = session.scalar(
			Select(db.Config).where(db.Config.guild == guildid, db.Config.key == key.upper()))
		if exists is None :
			session.close()
			return False
		if overwrite is False :
			return True
		session.delete(exists)
		DatabaseTransactions().commit(session)
		return True

	@staticmethod
	@abstractmethod
	def toggle_add(guildid, key, value=False) :
		if ConfigDbTransactions.key_exists_check(guildid, key.upper()) :
			item = session.query(db.Config).where(db.Config.guild == guildid, db.Config.key == key.upper()).first()
			item.value = value
			DatabaseTransactions().commit(session)
			from classes.configdata import ConfigData

			ConfigData().load_guild(guildid)
			return
		welcome = Config(guild=guildid, key=key.upper(), value=value)
		session.merge(welcome)
		logging.info(f"Added toggle '{key}' with value '{value}' in {guildid}")
		DatabaseTransactions().commit(session)
		from classes.configdata import ConfigData

		ConfigData().load_guild(guildid)

	@staticmethod
	@abstractmethod
	def server_config_get(guildid) :
		return session.scalars(Select(db.Config).where(db.Config.guild == guildid)).all()
