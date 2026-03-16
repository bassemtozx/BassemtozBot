import discord
from discord import ui


class VerdictModal(ui.Modal, title="إصدار الحكم النهائي"):
    verdict_type = ui.TextInput(
        label="نوع الحكم",
        placeholder="مثال: تحذير، إيقاف، حظر",
        max_length=256,
        required=True,
    )
    reason = ui.TextInput(
        label="سبب الحكم",
        placeholder="التفاصيل",
        style=discord.TextStyle.paragraph,
        max_length=2000,
        required=True,
    )
    punishment_duration = ui.TextInput(
        label="مدة العقوبة (اختياري)",
        placeholder="مثال: 3 أيام، أسبوع",
        max_length=256,
        required=False,
    )
    appeal_available = ui.TextInput(
        label="هل الاستئناف متاح؟",
        placeholder="نعم أو لا",
        max_length=10,
        required=True,
    )
    extra_notes = ui.TextInput(
        label="ملاحظات إضافية",
        placeholder="اختياري",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=False,
    )

    def __init__(self, case_id: str, callback):
        super().__init__(title=f"إصدار الحكم — {case_id}")
        self._case_id = case_id
        self._callback = callback

    async def on_submit(self, interaction: discord.Interaction):
        appeal_ok = self.appeal_available.value.strip().lower() in ("نعم", "yes", "y", "1")
        await self._callback(
            interaction,
            self._case_id,
            self.verdict_type.value.strip(),
            self.reason.value.strip(),
            (self.punishment_duration.value or "").strip(),
            appeal_ok,
            (self.extra_notes.value or "").strip(),
        )
