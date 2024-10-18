import discord
from discord.ui import View, button

from classes.support.discord_tools import send_response
from database.current import Proof
from database.databaseController import ProofDbTransactions


class Pagination(View):
    pages = 0
    current_page = 0
    data: list[Proof] = []
    interaction = None

    def __init__(self, data: list):
        super().__init__(timeout=None)
        self.data = data
        self.pages = len(data)

    async def send_view(self):
        if self.pages <= 0:
            return await send_response(self.interaction, f"This user does not have any evidence")
        embed = await self.create_embed()
        self.update_buttons()
        await self.interaction.response.send_message(embed=embed, view=self)

    async def create_embed(self) -> discord.Embed:
        data: Proof = self.data[self.current_page]
        embed = discord.Embed(title=f"Evidence for ban entry: {data.ban_id}",
                              description=f"{data.proof}")
        for attachment in data.get_attachments():
            embed.add_field(name="", value=attachment)
        return embed

    async def delete_item(self, interaction):
        self.data.pop(self.current_page)
        self.pages = len(self.data)
        if self.pages == 0:
            await interaction.message.edit(content="No evidence remaining", embed=None, view=None)
            return
        self.update_buttons()
        await self.load_page(self.current_page - 1)

    async def load_page(self, page_number: int):
        if page_number + 1 > self.pages:
            page_number = 0
        self.current_page = page_number
        embed = await self.create_embed()
        self.update_buttons()
        await self.interaction.message.edit(embed=embed, view=self)

    @button(label="Previous", custom_id="Previous", style=discord.ButtonStyle.success)
    async def previous(self, interaction: discord.Interaction, button: button):
        await interaction.response.defer()
        self.interaction = interaction
        await self.load_page(self.current_page - 1)

    @button(label="Delete", custom_id="Delete", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete(self, interaction: discord.Interaction, button: button):
        await interaction.response.defer()

        if interaction.guild.id != self.data[self.current_page].ban.gid:
            await interaction.followup.send("Evidence may only be removed by the original server or banwatch staff.", ephemeral=True)
            return

        result = ProofDbTransactions().delete(self.data[self.current_page].id)
        if not result:
            await interaction.followup.send("Failed to delete", ephemeral=True)
            return
        await interaction.followup.send(f"Deleted entry successfully", ephemeral=True)
        await self.delete_item(interaction)
        pass

    @button(label="Next", custom_id="Next", style=discord.ButtonStyle.success)
    async def next(self, interaction: discord.Interaction, button: button):
        await interaction.response.defer()
        self.interaction = interaction
        await self.load_page(self.current_page + 1)

    def update_buttons(self):
        if self.current_page == 0:
            self.previous.disabled = True
            self.previous.style = discord.ButtonStyle.gray
            print(self.previous.disabled)
        else:
            self.previous.disabled = False
            self.previous.style = discord.ButtonStyle.success

        if self.current_page == self.pages - 1:
            self.next.disabled = True
            self.next.style = discord.ButtonStyle.gray
        else:
            self.next.disabled = False
            self.next.style = discord.ButtonStyle.primary
