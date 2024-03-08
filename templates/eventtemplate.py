import logging

import discord
from discord.ext import commands
from abc import ABC, abstractmethod
import db
import adefs
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, column
from datetime import datetime, timedelta
import re
import typing

Session = sessionmaker(bind=db.engine)
session = Session()
class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        pass


async def setup(bot):
    await bot.add_cog(Events(bot))