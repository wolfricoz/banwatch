import logging
from typing import Type

from sqlalchemy import Select, exists, and_, false, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.util import to_list

import database.current as db
from database.current import *
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
        return session.query(exists().where(Servers.id == guild_id)).scalar()

    def add(self, guild_id: int, owner: str, name: str, member_count: int, invite: str) -> Servers | bool:
        if self.exist(guild_id):
            # Call the update function
            return False
        guild = Servers(id=guild_id, owner=owner, name=name, member_count=member_count, invite=invite)
        session.add(guild)
        self.commit(session)
        return guild

    def update(self, guild_id: int, owner: str = None, name: str = None, member_count: int = None, invite: str = None, delete: bool = None) -> Servers | bool:
        guild = session.scalar(Select(Servers).where(Servers.id == guild_id))
        if not guild:
            return False
        updates = {
            'owner'       : owner,
            'name'        : name,
            'member_count': member_count,
            'invite'      : invite,
            'deleted_at'  : datetime.now() if delete else None if delete is False else guild.deleted_at,
            'updated_at'  : datetime.now()
        }

        for field, value in updates.items():
            if field == 'deleted_at':
                setattr(guild, field, value)
                continue
            if value is not None:
                setattr(guild, field, value)
        self.commit(session)
        return guild

    def get(self, guild_id: int) -> Type[Servers] | None:
        return session.scalar(Select(Servers).where(Servers.id == guild_id))

    def delete(self, guild_id: int) -> bool:
        guild = self.get(guild_id)
        if not guild:
            return False
        session.delete(guild)
        self.commit(session)
        return True

    def get_bans(self, guild_id: int, uid_only: bool = false()) -> list[type[Bans]] | list[int]:
        if uid_only:
            return [uid[0] for uid in session.query(Bans.uid).filter(and_(Bans.gid == guild_id, Bans.deleted_at.is_(None))).all()]

        return session.query(Bans).filter(and_(Bans.gid == guild_id, Bans.deleted_at.is_(None))).all()


class BanDbTransactions(DatabaseTransactions, Bans):

    def exist(self, ban_id: int, remove_deleted: bool = False) -> bool:
        ban = session.scalar(Select(Bans).where(Bans.ban_id == ban_id))
        if ban is not None and ban.deleted_at and remove_deleted:
            self.delete_permanent(ban_id)
            return False
        return session.scalar(Select(Bans).where(Bans.ban_id == ban_id))

    def add(self, uid: int, gid: int, reason: str, staff: str, approved: bool = False, verified: bool = False, hidden: bool = False, remove_deleted: bool = False) -> Bans | bool:
        logging.info(f"Adding ban {uid} in {gid}")
        if self.exist(uid + gid, remove_deleted=remove_deleted):
            return False
        ban = Bans(ban_id=uid + gid, uid=uid, gid=gid, reason=reason, approved=approved, verified=verified, hidden=hidden, staff=staff, deleted_at=None)
        session.add(ban)
        self.commit(session)
        return ban

    def get(self, ban_id: int = None, override: bool = False) -> Type[Bans] | None:
        if override:
            return session.scalar(Select(Bans).where(Bans.ban_id == ban_id))
        return session.query(Bans).join(Servers).filter(and_(Bans.ban_id == ban_id, Bans.deleted_at.is_(None), Servers.deleted_at.is_(None))).first()

    def get_all_user(self, user_id, override=False):
        if override:
            return session.scalars(Select(Bans).where(Bans.uid == user_id)).all()
        return session.query(Bans).join(Servers).filter(and_(Bans.uid == user_id, Bans.deleted_at.is_(None), Servers.deleted_at.is_(None))).all()

    def get_all(self):
        return session.scalars(Select(Bans).join(Servers).where(and_(Bans.deleted_at.is_(None), Servers.deleted_at.is_(None)))).all()

    def count_bans(self):
        return session.execute(text("SELECT count(*) FROM bans")).scalar()

    def delete_soft(self, ban_id: int) -> bool:
        logging.info(f"Ban soft removed {ban_id}. Will be removed permanently in 7 days.")
        ban = self.get(ban_id)
        if not ban or ban.deleted_at:
            return False
        ban.deleted_at = datetime.now()
        self.commit(session)
        return True

    def delete_permanent(self, ban_id: int) -> bool:
        logging.info(f"Hard removing ban {ban_id}")
        ban = self.get(ban_id, override=True)
        if not ban:
            return False
        session.delete(ban)
        self.commit(session)
        return True

    def update(self, ban_id: int,
               approved: bool = None,
               verified: bool = None,
               hidden: bool = None,
               deleted_at: bool = None
               ) -> Type[Bans] | bool:
        ban = self.get(ban_id)
        if not ban:
            return False
        updates = {
            'approved'  : approved,
            'verified'  : verified,
            'hidden'    : hidden,
            'updated_at': datetime.now(),
            'deleted_at': datetime.now() if deleted_at else None if deleted_at is False else ban.deleted_at
        }

        for field, value in updates.items():
            if value is not None:
                setattr(ban, field, value)
        self.commit(session)
        return ban

    def get_deleted_bans(self) -> list[type[Bans]]:
        return session.query(Bans).filter(Bans.deleted_at.isnot(None)).all()


class ProofDbTransactions(DatabaseTransactions):

    def exist(self, ban_id: int):
        return session.scalar(Select(Proof).where(Proof.ban_id == ban_id))

    def add(self, ban_id: int, user_id: int, proof: str, attachments: list[str]) -> Proof | bool:
        proof = Proof(ban_id=ban_id, uid=user_id, proof=proof, attachments=json.dumps(attachments))
        session.add(proof)
        self.commit(session)
        return proof

    def get(self, ban_id: str | int = None, user_id: int = None) -> list | None:
        if isinstance(ban_id, str):
            ban_id = int(ban_id)
        if user_id:
            return to_list(session.scalars(Select(Proof).join(Bans).where(Proof.uid == user_id)).all())
        return to_list(session.scalars(Select(Proof).join(Bans).where(Proof.ban_id == ban_id)).all())

    def delete(self, id: int) -> bool:
        entry = session.scalar(Select(Proof).where(Proof.id == id))
        if not entry:
            return False
        session.delete(entry)
        self.commit(session)
        return True

    # def update(self, ban_id: int,
    #            proof: str = None,
    #            attachments: list[str] = None
    #            ) -> Proof | bool:
    #     proof = self.get(ban_id)
    #     if not proof:
    #         return False
    #     updates = {
    #         'proof'      : proof,
    #         'attachments': attachments
    #     }
    #
    #     for field, value in updates.items():
    #         if value is not None:
    #             setattr(proof, field, value)
    #     self.commit(session)
    #     return proof


class StaffDbTransactions(DatabaseTransactions):

    def get(self, uid: int) -> Staff | None:
        return session.scalar(Select(Staff).where(Staff.uid == uid))

    def add(self, uid: int, role: str) -> Staff | None:
        if self.get(uid):
            return None
        new_staff = Staff(uid=uid, role=role.lower())
        session.add(new_staff)
        self.commit(session)
        return new_staff

    def get_all(self) -> list[Staff]:
        return to_list(session.scalars(Select(Staff)).all())

    def delete(self, uid: int) -> bool:
        staff = self.get(uid)
        if not staff:
            return False
        session.delete(staff)
        self.commit(session)
        return True
