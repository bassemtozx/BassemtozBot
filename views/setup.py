import discord
from discord import ui

from modals import CaseSubmitModal


class OpenCaseButton(ui.Button):
    def __init__(self, submit_callback):
        super().__init__(style=discord.ButtonStyle.primary, label="رفع محضر", custom_id="cases:open_case")
        self._submit_callback = submit_callback

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("هذا الأمر يعمل داخل السيرفر فقط.", ephemeral=True)
            return
        modal = CaseSubmitModal(self._submit_callback)
        await interaction.response.send_modal(modal)


class SetupCasesView(ui.View):
    def __init__(self, submit_callback, timeout=None):
        super().__init__(timeout=timeout)
        self.add_item(OpenCaseButton(submit_callback))
