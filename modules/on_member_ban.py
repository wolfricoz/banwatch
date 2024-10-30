import logging

import discord
from discord.ext import commands

from classes.bans import Bans
from classes.configer import Configer
from view.buttons.baninform import BanInform
from view.buttons.banoptionbuttons import BanOptionButtons


class BanEvents(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(BanOptionButtons())
        self.bot.add_view(BanInform(Bans()))

    # Overhaul due to letting server owners choose
    # TODO: update the announcement system, make it work with the db mayhaps?
    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        """informs other servers an user is banned and updates banlist"""
        print('ban event')

        bot = self.bot
        if user == bot.user:
            logging.warning(f"I was banned in {guild.name}")
            return
        ban = await guild.fetch_ban(user)
        if ban.reason is None or ban.reason in ["", "none", "Account has no avatar.", "No reason given."] or str(ban.reason).lower().startswith('[silent]') or str(ban.reason).lower().startswith('[hidden]'):
            print("silent or hidden ban/no reason, not prompting")
            await Bans().add_ban(user.id, guild.id, "Hidden Ban", "Unknown")
            return
        logging.info("starting to update banlist and informing other servers")
        view = BanOptionButtons()
        modchannel = await Configer.get(guild.id, "modchannel")
        if modchannel is None:
            await guild.owner.send("No moderation channel set, please setup your moderation channel using the /config commands.")
        modchannel = bot.get_channel(int(modchannel))
        embed = discord.Embed(title=f"Do you want to share {user}'s ({user.id}) ban with other servers?",
                              description=f"{ban.reason}")
        embed.set_footer(text=f"{guild.id}-{user.id}")
        await modchannel.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(BanEvents(bot))
