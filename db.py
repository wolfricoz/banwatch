import os

import pymysql
from dotenv import load_dotenv
from sqlalchemy import Column, String, Boolean, BIGINT, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import QueuePool

pymysql.install_as_MySQLdb()
load_dotenv('main.env')
DBTOKEN = os.getenv("DB")

# sqlalchemy
engine = create_engine(DBTOKEN, echo=False, echo_pool=True, pool_pre_ping=True, poolclass=QueuePool, max_overflow=20, pool_timeout=120, pool_recycle=120)  # connects to the database
base = declarative_base()
engine.echo = False


# class creates table
class user(base):
    __tablename__ = 'user'

    uid = Column(BIGINT, primary_key=True)
    dob = Column(String(10))

    def __init__(self, uid, dob):
        self.uid = uid
        self.dob = dob


class config(base):
    __tablename__ = 'config'

    guild = Column(BIGINT, primary_key=True)
    lobby = Column(BIGINT)
    agelog = Column(BIGINT)
    modlobby = Column(BIGINT)
    general = Column(BIGINT)

    def __init__(self, guild, lobby, agelog, modlobby, general):
        self.guild = guild
        self.lobby = lobby
        self.agelog = agelog
        self.modlobby = modlobby
        self.general = general


# commits it to the databse
class permissions(base):
    __tablename__ = 'permissions'

    guild = Column(BIGINT, primary_key=True)
    admin = Column(BIGINT)
    mod = Column(BIGINT)
    trial = Column(BIGINT)
    lobbystaff = Column(BIGINT, default=None)

    def __init__(self, guild, admin, mod, trial, lobbystaff):
        self.guild = guild
        self.admin = admin
        self.mod = mod
        self.trial = trial
        self.lobbystaff = lobbystaff


class warnings(base):
    __tablename__ = 'warnings'

    uid = Column(BIGINT, primary_key=True)
    swarnings = Column(BIGINT)

    def __init__(self, uid, swarnings):
        self.uid = uid
        self.swarnings = swarnings


class idcheck(base):
    __tablename__ = 'idcheck'

    uid = Column(BIGINT, primary_key=True)
    check = Column(Boolean, default=False)

    def __init__(self, uid, check):
        self.uid = uid
        self.check = check


base.metadata.create_all(engine)
