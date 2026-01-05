import logging

from sqlalchemy import Select

from database import current as db
from database.current import Config
from database.transactions.BanReasonTransactions import DatabaseTransactions


class ConfigDbTransactions(DatabaseTransactions) :

	
	
	def config_update(self, guildid: int, key: str, value, overwrite=False) :
		with self.createsession() as session :

			if ConfigDbTransactions.key_exists_check(guildid, key) is False :
				return False
			exists = session.scalar(Select(db.Config).where(db.Config.guild == guildid, db.Config.key == key.upper()))
			exists.value = value
			DatabaseTransactions().commit(session)
			return True

	
	
	def config_unique_add(self, guildid: int, key: str, value, overwrite=False) :
		# This function should check if the item already exists, if so it will override it or throw an error.
		with self.createsession() as session :

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


	
	def toggle_welcome(self, guildid: int, key: str, value) :
		# This function should check if the item already exists, if so it will override it or throw an error.
		with self.createsession() as session :

			value = str(value)
			guilddata = session.scalar(Select(Config).where(Config.guild == guildid, Config.key == key.upper()))
			if guilddata is None :
				ConfigDbTransactions.config_unique_add(guildid, key, value, overwrite=True)
				return
			guilddata.value = value
			DatabaseTransactions().commit(session)

			return True

	
	
	def config_unique_get(self, guildid: int, key: str) :
		with self.createsession() as session :

			if ConfigDbTransactions.key_exists_check(guildid, key) is False :
				return
			exists = session.scalar(Select(db.Config).where(db.Config.guild == guildid, db.Config.key == key.upper()))
			return exists.value

	
	
	def config_key_add(self, guildid: int, key: str, value, overwrite) :
		with self.createsession() as session :

			value = str(value)
			if ConfigDbTransactions.key_multiple_exists_check(guildid, key, value) is True :
				return False
			item = db.Config(guild=guildid, key=key.upper(), value=value)
			session.add(item)
			DatabaseTransactions().commit(session)

			return True

	
	
	def key_multiple_exists_check(self, guildid: int, key: str, value) :
		with self.createsession() as session :

			exists = session.scalar(
				Select(db.Config).where(db.Config.guild == guildid, db.Config.key == key, db.Config.value == value))
			session.close()
			if exists is not None :
				return True
			return False

	
	
	def config_key_remove(self, guildid: int, key: str, value) :
		with self.createsession() as session :

			if ConfigDbTransactions.key_multiple_exists_check(guildid, key, value) is False :
				return False
			exists = session.scalar(
				Select(db.Config).where(db.Config.guild == guildid, db.Config.key == key, db.Config.value == value))
			session.delete(exists)
			DatabaseTransactions().commit(session)

	
	
	def config_unique_remove(self, guild_id: int, key: str) :
		with self.createsession() as session :

			if ConfigDbTransactions.key_exists_check(guild_id, key) is False :
				return False
			exists = session.scalar(
				Select(db.Config).where(db.Config.guild == guild_id, db.Config.key == key))
			session.delete(exists)
			DatabaseTransactions().commit(session)

	
	
	def key_exists_check(self, guildid: int, key: str, overwrite=False) :
		with self.createsession() as session :

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

	
	
	def toggle_add(self, guildid, key, value=False) :
		with self.createsession() as session :

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

	
	
	def server_config_get(self, guildid) :
		with self.createsession() as session :

			return session.scalars(Select(db.Config).where(db.Config.guild == guildid)).all()
