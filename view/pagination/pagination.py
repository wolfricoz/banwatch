import discord
from discord.ui import View, button

from classes.support.discord_tools import await_message, send_response


class Pagination(View):
    pages = 0
    current_page = 0
    data = []
    interaction = None

    def __init__(self, data: list):
        super().__init__(timeout=None)
        self.data = data
        self.pages = len(data)

    async def send_view(self):
        if self.pages <= 0:
            return await send_response(self.interaction, f"This user does not have any evidence")
        await self.interaction.response.send_message(self.data[self.current_page], view=self)

    async def load_page(self, page_number: int):
        print(page_number)
        print(self.pages)
        if page_number + 1 > self.pages:
            page_number = 0
        await self.interaction.message.edit(content=self.data[page_number])
        self.current_page = page_number

    @button(label="Previous", custom_id="Previous", style=discord.ButtonStyle.success)
    async def previous(self, interaction: discord.Interaction, button: button):
        await interaction.response.defer()
        self.interaction = interaction
        await self.load_page(self.current_page - 1 )

    @button(label="Next", custom_id="Next", style=discord.ButtonStyle.success)
    async def next(self, interaction: discord.Interaction, button: button):
        await interaction.response.defer()
        self.interaction = interaction
        await self.load_page(self.current_page + 1)


