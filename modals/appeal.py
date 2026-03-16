import discord
from discord import ui


class AppealModal(ui.Modal, title="تقديم استئناف"):
    reason = ui.TextInput(
        label="سبب الاستئناف",
        placeholder="لماذا تطلب إعادة النظر؟",
        style=discord.TextStyle.paragraph,
        max_length=1500,
        required=True,
    )
    new_evidence = ui.TextInput(
        label="هل توجد أدلة جديدة؟",
        placeholder="نعم/لا مع التفاصيل",
        max_length=500,
        required=False,
    )
    details = ui.TextInput(
        label="التفاصيل",
        placeholder="أي معلومات إضافية",
        style=discord.TextStyle.paragraph,
        max_length=2000,
        required=False,
    )

    def __init__(self, case_id: str, callback):
        super().__init__(title=f"استئناف — {case_id}")
        self._case_id = case_id
        self._callback = callback

    async def on_submit(self, interaction: discord.Interaction):
        await self._callback(
            interaction,
            self._case_id,
            self.reason.value.strip(),
            (self.new_evidence.value or "").strip(),
            (self.details.value or "").strip(),
        )
