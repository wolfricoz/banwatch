import os
from datetime import datetime
from typing import List

import pymysql
from dotenv import load_dotenv
from sqlalchemy import create_engine, DateTime, ForeignKey, String, BigInteger, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.sql import func
from sqlalchemy_utils import database_exists, create_database

pymysql.install_as_MySQLdb()
load_dotenv('main.env')
DB = os.getenv('DB')

engine = create_engine(f"{DB}?charset=utf8mb4", poolclass=NullPool, echo=False, )
if not database_exists(engine.url):
    create_database(engine.url)

conn = engine.connect()


class Base(DeclarativeBase):
    pass


class Bans(Base):
    __tablename__ = "bans"
    ban_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    uid: Mapped[int] = mapped_column(BigInteger)
    gid: Mapped[int] = mapped_column(BigInteger, ForeignKey("servers.id"))
    reason: Mapped[str] = mapped_column(String(4096, collation='utf8mb4_unicode_ci'), default="")
    approved: Mapped[bool] = mapped_column(Boolean, default=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    staff: Mapped[str] = mapped_column(String(1024, collation='utf8mb4_unicode_ci'))
    proof: Mapped["Proof"] = relationship("Proof", cascade="save-update, merge, delete, delete-orphan", back_populates="ban")
    guild: Mapped["Servers"] = relationship("Servers", back_populates="bans")


class Proof(Base):
    __tablename__ = "proof"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ban_id: Mapped[int] = mapped_column(ForeignKey("bans.ban_id"))
    proof: Mapped[str] = mapped_column(String(4096, collation='utf8mb4_unicode_ci'))
    attachments: Mapped[str] = mapped_column(String(10000, collation='utf8mb4_unicode_ci'))
    ban: Mapped["Bans"] = relationship("Bans", back_populates="proof")


class Servers(Base):
    __tablename__ = "servers"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    owner: Mapped[str] = mapped_column(String(1024, collation='utf8mb4_unicode_ci'))
    member_count: Mapped[int] = mapped_column(BigInteger)
    invite: Mapped[str] = mapped_column(String(256, collation='utf8mb4_unicode_ci'), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=None, nullable=True)
    bans: Mapped[List["Bans"]] = relationship("Bans", back_populates="guild", cascade="save-update, merge, delete, delete-orphan")


def create_bot_database():
    Base.metadata.create_all(engine)


def drop_bot_database():
    if os.getenv('DISCORD_TOKEN') is not None:
        raise Exception("You cannot drop the database while the bot is in production")
    sessionmaker(engine).close_all()
    Base.metadata.drop_all(engine)
