import discord
from discord import ui


class NoteModal(ui.Modal, title="ملاحظة إدارية"):
    note = ui.TextInput(
        label="الملاحظة",
        placeholder="اكتب الملاحظة الإدارية",
        style=discord.TextStyle.paragraph,
        max_length=1500,
        required=True,
    )

    def __init__(self, case_id: str, callback):
        super().__init__(title=f"ملاحظة — {case_id}")
        self._case_id = case_id
        self._callback = callback

    async def on_submit(self, interaction: discord.Interaction):
        await self._callback(interaction, self._case_id, self.note.value.strip())
