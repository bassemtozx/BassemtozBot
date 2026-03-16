import discord
from discord import ui


class CaseSubmitModal(ui.Modal, title="رفع محضر جديد"):
    defendant = ui.TextInput(
        label="اسم أو منشن المشتكى عليه",
        placeholder="اسم أو @المستخدم",
        max_length=256,
        required=True,
    )
    case_type = ui.TextInput(
        label="نوع القضية",
        placeholder="مثال: إساءة، غش، تحرش",
        max_length=256,
        required=True,
    )
    description = ui.TextInput(
        label="وصف القضية",
        placeholder="اشرح تفاصيل القضية",
        style=discord.TextStyle.paragraph,
        max_length=2000,
        required=True,
    )
    evidence = ui.TextInput(
        label="الأدلة",
        placeholder="روابط أو وصف الأدلة",
        style=discord.TextStyle.paragraph,
        max_length=2000,
        required=True,
    )
    witnesses = ui.TextInput(
        label="الشهود (اختياري)",
        placeholder="أسماء أو منشن الشهود",
        max_length=500,
        required=False,
    )

    def __init__(self, callback):
        super().__init__()
        self._callback = callback

    async def on_submit(self, interaction: discord.Interaction):
        await self._callback(
            interaction,
            self.defendant.value.strip(),
            self.case_type.value.strip(),
            self.description.value.strip(),
            self.evidence.value.strip(),
            (self.witnesses.value or "").strip(),
        )
