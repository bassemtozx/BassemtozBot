import discord
from discord import ui


class EvidenceModal(ui.Modal, title="إضافة دليل"):
    evidence = ui.TextInput(
        label="الدليل / الوصف",
        placeholder="رابط أو وصف الدليل الجديد",
        style=discord.TextStyle.paragraph,
        max_length=2000,
        required=True,
    )

    def __init__(self, case_id: str, callback):
        super().__init__(title=f"إضافة دليل — {case_id}")
        self._case_id = case_id
        self._callback = callback

    async def on_submit(self, interaction: discord.Interaction):
        await self._callback(interaction, self._case_id, self.evidence.value.strip())
