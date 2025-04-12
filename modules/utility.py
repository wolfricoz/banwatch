import discord
from discord import app_commands
from discord.ext import commands
from discord_py_utilities.messages import send_response


class Utility(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot


    @app_commands.command()
    async def support(self, interaction: discord.Interaction):
        await interaction.response.send_message(
                "If you are in need of support, please read our documentation at https://wolfricoz.github.io/banwatch/ ! You can find our discord link in the documentation. If you still need help, please join our discord server and ask in the support channel.", ephemeral=True)

    @app_commands.command(name="donate", description="If you like banwatch, consider donating!")
    async def donate(self, interaction: discord.Interaction):
        await send_response(interaction, f"If you like the service banwatch provides and would like to financially support banwatch, you can do so here: https://donate.stripe.com/dR6eV63rQfr5g2kcMM")




async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))
