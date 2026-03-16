import discord
from discord import ui

from config import CASE_STATUSES
from database.queries import get_case_by_id
from utils.perms import can_manage_case, can_issue_verdict, can_override_verdict


class CaseActionsView(ui.View):
    def __init__(self, case_id: str, action_handler, timeout=None):
        super().__init__(timeout=timeout)
        self._case_id = case_id
        self._handler = action_handler

    def _can_manage(self, user: discord.Member) -> bool:
        return user and user.guild and can_manage_case(user)

    def _can_verdict(self, user: discord.Member) -> bool:
        return user and user.guild and can_issue_verdict(user)

    def _can_override(self, user: discord.Member) -> bool:
        return user and user.guild and can_override_verdict(user)

    @ui.button(label="استلام القضية", style=discord.ButtonStyle.primary, custom_id="case:claim")
    async def claim(self, interaction: discord.Interaction, button: ui.Button):
        if not self._can_manage(interaction.user):
            await interaction.response.send_message("ليس لديك صلاحية إدارة القضايا.", ephemeral=True)
            return
        await self._handler.on_claim(interaction, self._case_id)

    @ui.button(label="تعيين قاضٍ", style=discord.ButtonStyle.secondary, custom_id="case:assign_judge")
    async def assign_judge(self, interaction: discord.Interaction, button: ui.Button):
        if not self._can_manage(interaction.user):
            await interaction.response.send_message("ليس لديك صلاحية.", ephemeral=True)
            return
        await interaction.response.send_message(
            "استخدم الأمر: `/case_assign_judge case_id:@القاضي`", ephemeral=True
        )

    @ui.button(label="إضافة دليل", style=discord.ButtonStyle.secondary, custom_id="case:add_evidence")
    async def add_evidence(self, interaction: discord.Interaction, button: ui.Button):
        if not self._can_manage(interaction.user):
            await interaction.response.send_message("ليس لديك صلاحية.", ephemeral=True)
            return
        await self._handler.on_add_evidence_modal(interaction, self._case_id)

    @ui.button(label="طلب أدلة إضافية", style=discord.ButtonStyle.secondary, custom_id="case:request_evidence")
    async def request_evidence(self, interaction: discord.Interaction, button: ui.Button):
        if not self._can_manage(interaction.user):
            await interaction.response.send_message("ليس لديك صلاحية.", ephemeral=True)
            return
        await self._handler.on_request_evidence(interaction, self._case_id)

    @ui.button(label="تغيير الحالة", style=discord.ButtonStyle.secondary, custom_id="case:change_status")
    async def change_status(self, interaction: discord.Interaction, button: ui.Button):
        if not self._can_manage(interaction.user):
            await interaction.response.send_message("ليس لديك صلاحية.", ephemeral=True)
            return
        await self._handler.on_change_status(interaction, self._case_id)

    @ui.button(label="كتابة ملاحظة", style=discord.ButtonStyle.secondary, custom_id="case:note")
    async def note(self, interaction: discord.Interaction, button: ui.Button):
        if not self._can_manage(interaction.user):
            await interaction.response.send_message("ليس لديك صلاحية.", ephemeral=True)
            return
        await self._handler.on_note_modal(interaction, self._case_id)

    @ui.button(label="إصدار حكم نهائي", style=discord.ButtonStyle.success, custom_id="case:verdict")
    async def verdict(self, interaction: discord.Interaction, button: ui.Button):
        if not self._can_verdict(interaction.user):
            await interaction.response.send_message("صلاحية إصدار الحكم للقضاة والإدمن فقط.", ephemeral=True)
            return
        case = get_case_by_id(self._case_id)
        if not case:
            await interaction.response.send_message("القضية غير موجودة.", ephemeral=True)
            return
        if case.get("verdict_locked"):
            await interaction.response.send_message(
                "الحكم مقفل. استخدم `/case_override_unlock_verdict` إذا كنت أدمن.", ephemeral=True
            )
            return
        await self._handler.on_verdict_modal(interaction, self._case_id)

    @ui.button(label="إغلاق القضية", style=discord.ButtonStyle.danger, custom_id="case:close")
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        if not self._can_manage(interaction.user):
            await interaction.response.send_message("ليس لديك صلاحية.", ephemeral=True)
            return
        await self._handler.on_close(interaction, self._case_id)

    @ui.button(label="أرشفة", style=discord.ButtonStyle.secondary, custom_id="case:archive")
    async def archive(self, interaction: discord.Interaction, button: ui.Button):
        if not self._can_manage(interaction.user):
            await interaction.response.send_message("ليس لديك صلاحية.", ephemeral=True)
            return
        await self._handler.on_archive(interaction, self._case_id)

    @ui.button(label="إعادة فتح", style=discord.ButtonStyle.secondary, custom_id="case:reopen")
    async def reopen(self, interaction: discord.Interaction, button: ui.Button):
        if not self._can_manage(interaction.user):
            await interaction.response.send_message("ليس لديك صلاحية.", ephemeral=True)
            return
        await self._handler.on_reopen(interaction, self._case_id)

    @ui.button(label="تقديم استئناف", style=discord.ButtonStyle.primary, custom_id="case:appeal")
    async def appeal(self, interaction: discord.Interaction, button: ui.Button):
        case = get_case_by_id(self._case_id)
        if not case:
            await interaction.response.send_message("القضية غير موجودة.", ephemeral=True)
            return
        if case["creator_id"] != interaction.user.id:
            await interaction.response.send_message("فقط مقدم الشكوى يمكنه تقديم استئناف.", ephemeral=True)
            return
        if not case.get("appeal_allowed"):
            await interaction.response.send_message("الاستئناف غير متاح لهذه القضية.", ephemeral=True)
            return
        if case["status"] != "صدر الحكم":
            await interaction.response.send_message("يمكن تقديم الاستئناف فقط بعد صدر الحكم.", ephemeral=True)
            return
        await self._handler.on_appeal_modal(interaction, self._case_id)


def build_status_select(case_id: str) -> ui.Select:
    options = [discord.SelectOption(label=s, value=s) for s in CASE_STATUSES]

    async def select_callback(interaction: discord.Interaction):
        from utils.perms import can_manage_case
        if not interaction.user or not can_manage_case(interaction.user):
            await interaction.response.send_message("ليس لديك صلاحية.", ephemeral=True)
            return
        from database.queries import update_case_status, log_action
        update_case_status(case_id, interaction.data["values"][0])
        log_action(case_id, interaction.user.id, "تغيير الحالة", interaction.data["values"][0])
        await interaction.response.send_message(f"تم تغيير الحالة إلى: {interaction.data['values'][0]}", ephemeral=True)

    select = ui.Select(placeholder="اختر الحالة", options=options, custom_id=f"case_status:{case_id}")
    select.callback = select_callback
    return select
