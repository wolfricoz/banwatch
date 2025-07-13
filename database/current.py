import json
import os
from datetime import datetime
from typing import List

import pymysql
from dotenv import load_dotenv
from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.sql import func
from sqlalchemy_utils import create_database, database_exists

pymysql.install_as_MySQLdb()
load_dotenv('main.env')
if os.path.exists("main.env") is False :
	load_dotenv("tests/main.env")
DB = os.getenv('DB')

engine = create_engine(f"{DB}?charset=utf8mb4", poolclass=NullPool, echo=False, isolation_level="READ COMMITTED")
if not database_exists(engine.url) :
	create_database(engine.url)

conn = engine.connect()


class Base(DeclarativeBase) :
	pass


class Staff(Base) :
	__tablename__ = "staff"
	id: Mapped[int] = mapped_column(primary_key=True)
	uid: Mapped[int] = mapped_column(BigInteger)
	role: Mapped[str] = mapped_column(String(128))

	def __int__(self) :
		return self.id


class Bans(Base) :
	__tablename__ = "bans"
	ban_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
	uid: Mapped[int] = mapped_column(BigInteger)
	gid: Mapped[int] = mapped_column(BigInteger, ForeignKey("servers.id"))
	reason: Mapped[str] = mapped_column(String(4096, collation='utf8mb4_unicode_ci'), default="")
	message: Mapped[int] = mapped_column(BigInteger, nullable=True)
	approved: Mapped[bool] = mapped_column(Boolean, default=True)
	verified: Mapped[bool] = mapped_column(Boolean, default=False)
	hidden: Mapped[bool] = mapped_column(Boolean, default=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
	staff: Mapped[str] = mapped_column(String(1024, collation='utf8mb4_unicode_ci'))
	proof: Mapped[List["Proof"]] = relationship("Proof", back_populates="ban",
	                                            cascade="all, save-update, merge, delete, delete-orphan")
	appeals: Mapped[List["Appeals"]] = relationship("Appeals", back_populates="ban",
	                                                cascade="all, save-update, merge, delete, delete-orphan")
	guild: Mapped["Servers"] = relationship("Servers", back_populates="bans")
	deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None, nullable=True)

	def __int__(self) :
		return self.ban_id


class Proof(Base) :
	__tablename__ = "proof"
	id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
	ban_id: Mapped[int] = mapped_column(ForeignKey("bans.ban_id"))
	uid: Mapped[int] = mapped_column(BigInteger)
	proof: Mapped[str] = mapped_column(String(4096, collation='utf8mb4_unicode_ci'))
	attachments: Mapped[str] = mapped_column(String(10000, collation='utf8mb4_unicode_ci'))
	ban: Mapped["Bans"] = relationship("Bans", back_populates="proof", )

	def get_attachments(self) :
		return json.loads(self.attachments)

	def __int__(self) :
		return self.id


class Servers(Base) :
	__tablename__ = "servers"
	id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
	owner: Mapped[str] = mapped_column(String(1024, collation='utf8mb4_unicode_ci'))
	name: Mapped[str] = mapped_column(String(1024, collation='utf8mb4_unicode_ci'))
	member_count: Mapped[int] = mapped_column(BigInteger)
	hidden: Mapped[bool] = mapped_column(Boolean, default=False)
	invite: Mapped[str] = mapped_column(String(256, collation='utf8mb4_unicode_ci'), default="")
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
	deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=None, nullable=True)
	active: Mapped[bool] = mapped_column(Boolean, default=True)
	bans: Mapped[List["Bans"]] = relationship("Bans", back_populates="guild",
	                                          cascade="save-update, merge, delete, delete-orphan")

	def __int__(self) :
		return self.id


class Appeals(Base) :
	__tablename__ = "appeals"
	id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
	ban_id: Mapped[int] = mapped_column(ForeignKey("bans.ban_id"))
	message: Mapped[str] = mapped_column(String(2000, collation='utf8mb4_unicode_ci'))
	status: Mapped[str] = mapped_column(Enum('approved', 'pending', 'denied', name='status_enum'), nullable=False,
	                                    default='pending')
	ban: Mapped["Bans"] = relationship("Bans", back_populates="appeals", )

	def __int__(self) :
		return self.id


class Config(Base) :
	# Reminder to self you can add multiple keys in this database
	__tablename__ = "config"
	id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
	guild: Mapped[int] = mapped_column(BigInteger, ForeignKey("servers.id", ondelete="CASCADE"))
	key: Mapped[str] = mapped_column(String(512), primary_key=True)
	value: Mapped[str] = mapped_column(String(1980))

class FlaggedTerms(Base):
	__tablename__ = "flagged_terms"
	id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
	term: Mapped[str] = mapped_column(String(512, collation='utf8mb4_unicode_ci'), unique=True)
	action: Mapped[str] = mapped_column(String(128, collation='utf8mb4_unicode_ci'))
	regex: Mapped[bool] = mapped_column(Boolean, default=False)
	active: Mapped[bool] = mapped_column(Boolean, default=True)

def create_bot_database() :
	Base.metadata.create_all(engine)


def drop_bot_database() :
	if os.getenv('DISCORD_TOKEN') is not None :
		raise Exception("You cannot drop the database while the bot is in production")
	Session = sessionmaker(bind=engine)
	session = Session()
	session.close_all()
	Base.metadata.drop_all(engine)
