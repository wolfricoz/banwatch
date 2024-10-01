from typing import Type

import database.current as db
from database.current import *
from sqlalchemy import Select, exists
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database.current import Servers

session = Session(bind=db.engine, expire_on_commit=False)


class ConfigNotFound(Exception):
    """config item was not found or has not been added yet."""

    def __init__(self, message="guild config has not been loaded yet or has not been created yet."):
        self.message = message
        super().__init__(self.message)


class CommitError(Exception):
    """the commit failed."""

    def __init__(self, message="Commiting the data to the database failed and has been rolled back; please try again."):
        self.message = message
        super().__init__(self.message)


class KeyNotFound(Exception):
    """config item was not found or has not been added yet."""

    def __init__(self, key):
        self.key = key
        self.message = f"`{key}` not found in config, please add it using /config"
        super().__init__(self.message)


class UserNotFound(Exception):
    """config item was not found or has not been added yet."""

    def __init__(self, key):
        self.key = key
        self.message = f"`{key}` not found in config, please add it using /config"
        super().__init__(self.message)


class DatabaseTransactions():

    def commit(self, session):
        try:
            session.commit()
        except SQLAlchemyError as e:
            print(e)
            session.rollback()
            raise CommitError()
        finally:
            session.close()


class ServerDbTransactions(DatabaseTransactions):

    def exist(self, guild_id: int):
        return session.query(exists().where(Servers.guild == guild_id)).scalar()

    def add(self, guild_id: int, owner: str, member_count: int, invite: str) -> Servers | bool:
        if self.exist(guild_id):
            # Call the update function
            return False
        guild = Servers(guild=guild_id, owner=owner, member_count=member_count, invite=invite)
        session.add(guild)
        self.commit(session)
        return guild

    def update(self, guild_id: int, owner: str = None, member_count: int = None, invite: str = None, active: bool = None) -> Servers | bool:
        guild = session.scalar(Select(Servers).where(Servers.guild == guild_id))
        if not guild:
            return False

        updates = {
            'owner'       : owner,
            'member_count': member_count,
            'invite'      : invite,
            'active'      : active
        }

        for field, value in updates.items():
            if value is not None:
                setattr(guild, field, value)
        self.commit(session)
        return guild

    def get(self, guild_id: int) -> Type[Servers] | None:
        return session.scalar(Select(Servers).where(Servers.guild == guild_id))

    def delete(self, guild_id: int) -> bool:
        guild = self.get(guild_id)
        if not guild:
            return False
        session.delete(guild)
        DatabaseTransactions().commit(session)
        return True

class BanDbTransactions(DatabaseTransactions):

    def exist(self, ban_id: int):
        return session.scalar(Select(Bans).where(Bans.ban_id == ban_id))

    def add(self, uid: int, gid: int, reason: str, staff: str, approved: bool = False, verified: bool = False, hidden: bool = False) -> Bans | bool:
        if self.exist(uid + gid):
            return False
        ban = Bans(ban_id=uid + gid, uid=uid, gid=gid, reason=reason, approved=approved, verified=verified, hidden=hidden, staff=staff)
        session.add(ban)
        self.commit(session)
        return ban

    def get(self, ban_id: int, override: bool = False) -> Type[Bans] | None:
        if override:
            return session.scalar(Select(Bans).where(Bans.ban_id == ban_id))
        return session.scalar(Select(Bans).join(Servers).where(Bans.ban_id == ban_id and Servers.active is True))