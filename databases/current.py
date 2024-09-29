import os
from datetime import datetime
from typing import List, Optional

import pymysql
from dotenv import load_dotenv
from sqlalchemy import create_engine, DateTime, ForeignKey, String, BigInteger, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.pool import NullPool
from sqlalchemy.sql import func
from sqlalchemy_utils import database_exists, create_database

pymysql.install_as_MySQLdb()
load_dotenv('.env')
DB = os.getenv('DB')

engine = create_engine(f"{DB}/rmrbotnew", poolclass=NullPool, echo=False)
if not database_exists(engine.url):
    create_database(engine.url)

conn = engine.connect()


class Base(DeclarativeBase):
    pass


class Bans(Base):
    __tablename__ = "bans"
    id: Mapped[int] = mapped_column(BigInteger ,primary_key=True)
    uid: Mapped[int] = mapped_column(BigInteger)
    gid: Mapped[int] = mapped_column(BigInteger)
    reason: Mapped[str] = mapped_column(String(4096))
    approved: Mapped[bool] = mapped_column(Boolean, default=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    staff: Mapped[str] = mapped_column(String(1024))


class Proof(Base):
    __tablename__ = "proof"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ban_id: Mapped[int] = mapped_column(ForeignKey("bans.id"))
    proof: Mapped[str] = mapped_column(String(4096))
    # Research lists in sqlalchemy
    attachments: Mapped[List[str]] = mapped_column(String(10000))


class Servers(Base):
    __tablename__ = "servers"
    guild: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)





class database:
    @staticmethod
    def create():
        Base.metadata.create_all(engine)
        print("Database built")
