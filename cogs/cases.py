# cogs/cases.py — نظام إدارة المحاضر
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime

from config import (
    STAFF_ROLE_ID,
    JUDGE_ROLE_ID,
    ADMIN_ROLE_ID,
    OPEN_CASES_CATEGORY_ID,
    CLOSED_CASES_CATEGORY_ID,
    VERDICTS_CHANNEL_ID,
    CASE_STATUSES,
)
from database import queries as q
from modals import CaseSubmitModal, VerdictModal, AppealModal, NoteModal, EvidenceModal
from views import SetupCasesView, CaseActionsView
from utils.perms import is_staff, is_judge, is_admin, can_manage_case, can_issue_verdict, can_override_verdict
from utils.embeds import build_case_embed, build_verdict_announce_embed, build_list_embed
from utils.log_channel import send_log_embed
from utils.transcript import export_transcript
from utils.punishment import parse_punishment_duration


def _now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


class CasesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(SetupCasesView(self._submit_callback))

    async def _case_channel_overwrites(self, guild: discord.Guild, creator_id: int) -> dict:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        creator = guild.get_member(creator_id)
        if creator:
            overwrites[creator] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        if STAFF_ROLE_ID:
            r = guild.get_role(STAFF_ROLE_ID)
            if r:
                overwrites[r] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        if JUDGE_ROLE_ID:
            r = guild.get_role(JUDGE_ROLE_ID)
            if r:
                overwrites[r] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        if ADMIN_ROLE_ID:
            r = guild.get_role(ADMIN_ROLE_ID)
            if r:
                overwrites[r] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        return overwrites

    async def _submit_callback(
        self,
        interaction: discord.Interaction,
        defendant_text: str,
        case_type: str,
        description: str,
        evidence: str,
        witnesses: str,
    ):
        if not interaction.guild:
            await interaction.response.send_message("هذا الأمر يعمل داخل السيرفر فقط.", ephemeral=True)
            return
        try:
            await interaction.response.defer(ephemeral=True)
        except Exception:
            try:
                await interaction.response.send_message("حدث خطأ عند الاستجابة. جرّب مرة أخرى.", ephemeral=True)
            except Exception:
                pass
            return
        try:
            guild = interaction.guild
            creator_id = interaction.user.id
            defendant_user_id = None
            for mention in getattr(interaction, "resolved", {}).values() or []:
                if hasattr(mention, "id"):
                    defendant_user_id = mention.id
                    break
            try:
                case_id = q.next_case_id(guild.id)
            except Exception as e:
                await interaction.followup.send(f"خطأ في إنشاء رقم القضية: {e}", ephemeral=True)
                return
            category = guild.get_channel(OPEN_CASES_CATEGORY_ID) if OPEN_CASES_CATEGORY_ID else None
            if not category or not isinstance(category, discord.CategoryChannel):
                await interaction.followup.send(
                    "لم يتم ضبط فئة قنوات القضايا المفتوحة (OPEN_CASES_CATEGORY_ID). راجع الإعدادات.",
                    ephemeral=True,
                )
                return
            overwrites = await self._case_channel_overwrites(guild, creator_id)
            channel_name = case_id.lower().replace("-", "")
            try:
                ch = await guild.create_text_channel(
                    name=channel_name,
                    category=category,
                    overwrites=overwrites,
                    topic=f"القضية {case_id} — مقدم الشكوى: {interaction.user.display_name}",
                )
            except discord.Forbidden:
                await interaction.followup.send("البوت لا يملك صلاحية إنشاء قنوات.", ephemeral=True)
                return
            except Exception as e:
                await interaction.followup.send(f"فشل إنشاء القناة: {e}", ephemeral=True)
                return
            try:
                q.create_case(
                    case_id,
                    guild.id,
                    ch.id,
                    creator_id,
                    defendant_text,
                    defendant_user_id,
                    case_type,
                    description,
                    evidence,
                    witnesses or "",
                )
            except Exception as e:
                await ch.delete(reason="Rollback after DB error")
                await interaction.followup.send(f"خطأ في حفظ القضية: {e}", ephemeral=True)
                return
            q.log_action(case_id, creator_id, "إنشاء القضية", None)
            try:
                case = q.get_case_by_id(case_id)
                emb = build_case_embed(case, guild)
                view = CaseActionsView(case_id, self)
                await ch.send(embed=emb, view=view)
                await interaction.followup.send(
                    f"تم إنشاء القضية **{case_id}** وقناتها: {ch.mention}",
                    ephemeral=True,
                )
            except Exception as e:
                await interaction.followup.send(
                    f"تم إنشاء القضية **{case_id}** وقناتها: {ch.mention}. (تحذير: فشل إرسال تفاصيل داخل القناة: {e})",
                    ephemeral=True,
                )
            try:
                await send_log_embed(self.bot, case_id, "قضية جديدة", interaction.user, case_id)
            except Exception:
                pass
        except Exception as e:
            try:
                await interaction.followup.send(f"حدث خطأ: {str(e)[:300]}", ephemeral=True)
            except Exception:
                pass

    def _get_guild(self, interaction: discord.Interaction) -> discord.Guild | None:
        return interaction.guild

    async def on_claim(self, interaction: discord.Interaction, case_id: str):
        case = q.get_case_by_id(case_id)
        if not case:
            await interaction.response.send_message("القضية غير موجودة.", ephemeral=True)
            return
        q.assign_staff(case_id, interaction.user.id)
        q.update_case_status(case_id, "قيد المراجعة")
        q.log_action(case_id, interaction.user.id, "استلام القضية", str(interaction.user.id))
        case = q.get_case_by_id(case_id)
        emb = build_case_embed(case, interaction.guild)
        view = CaseActionsView(case_id, self)
        try:
            await interaction.response.send_message("تم استلام القضية.", ephemeral=True)
            if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
                await interaction.channel.send(embed=emb, view=view)
        except discord.NotFound:
            if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
                await interaction.channel.send(embed=emb, view=view)

    async def on_add_evidence_modal(self, interaction: discord.Interaction, case_id: str):
        modal = EvidenceModal(case_id, self._evidence_callback)
        await interaction.response.send_modal(modal)

    async def _evidence_callback(self, interaction: discord.Interaction, case_id: str, evidence: str):
        case = q.get_case_by_id(case_id)
        if not case:
            await interaction.response.send_message("القضية غير موجودة.", ephemeral=True)
            return
        q.append_evidence(case_id, evidence)
        q.log_action(case_id, interaction.user.id, "إضافة دليل", evidence[:200])
        await interaction.response.send_message("تمت إضافة الدليل.", ephemeral=True)
        case = q.get_case_by_id(case_id)
        emb = build_case_embed(case, interaction.guild)
        view = CaseActionsView(case_id, self)
        if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
            await interaction.channel.send(embed=emb, view=view)

    async def on_request_evidence(self, interaction: discord.Interaction, case_id: str):
        q.update_case_status(case_id, "بانتظار أدلة إضافية")
        q.log_action(case_id, interaction.user.id, "طلب أدلة إضافية", None)
        await interaction.response.send_message("تم تحديث الحالة إلى: بانتظار أدلة إضافية", ephemeral=True)

    async def on_change_status(self, interaction: discord.Interaction, case_id: str):
        options = [discord.SelectOption(label=s, value=s) for s in CASE_STATUSES]
        select = ui.Select(placeholder="اختر الحالة", options=options, custom_id=f"status_select:{case_id}")

        async def sel_cb(inter: discord.Interaction):
            if not can_manage_case(inter.user):
                await inter.response.send_message("ليس لديك صلاحية.", ephemeral=True)
                return
            val = inter.data["values"][0]
            q.update_case_status(case_id, val)
            q.log_action(case_id, inter.user.id, "تغيير الحالة", val)
            await inter.response.send_message(f"تم تغيير الحالة إلى: {val}", ephemeral=True)

        select.callback = sel_cb
        view = ui.View(timeout=60)
        view.add_item(select)
        await interaction.response.send_message("اختر الحالة الجديدة:", view=view, ephemeral=True)

    async def on_note_modal(self, interaction: discord.Interaction, case_id: str):
        modal = NoteModal(case_id, self._note_callback)
        await interaction.response.send_modal(modal)

    async def _note_callback(self, interaction: discord.Interaction, case_id: str, note: str):
        q.add_note(case_id, interaction.user.id, note)
        q.log_action(case_id, interaction.user.id, "ملاحظة إدارية", note[:200])
        await interaction.response.send_message("تم حفظ الملاحظة.", ephemeral=True)

    async def on_verdict_modal(self, interaction: discord.Interaction, case_id: str):
        modal = VerdictModal(case_id, self._verdict_callback)
        await interaction.response.send_modal(modal)

    async def _verdict_callback(
        self,
        interaction: discord.Interaction,
        case_id: str,
        verdict_type: str,
        reason: str,
        punishment_duration: str,
        appeal_ok: bool,
        extra_notes: str,
    ):
        if not can_issue_verdict(interaction.user):
            await interaction.response.send_message("صلاحية إصدار الحكم للقضاة والإدمن فقط.", ephemeral=True)
            return
        case = q.get_case_by_id(case_id)
        if not case or case.get("verdict_locked"):
            await interaction.response.send_message("القضية غير موجودة أو الحكم مقفل.", ephemeral=True)
            return
        q.set_verdict(case_id, verdict_type, reason, punishment_duration or None, appeal_ok)
        q.lock_verdict(case_id)
        q.log_action(case_id, interaction.user.id, "إصدار الحكم", verdict_type)
        case = q.get_case_by_id(case_id)
        timeout_applied = False
        if case.get("defendant_user_id") and punishment_duration:
            duration_delta = parse_punishment_duration(punishment_duration)
            if duration_delta and interaction.guild:
                member = interaction.guild.get_member(case["defendant_user_id"])
                if member:
                    try:
                        await member.timeout(
                            duration_delta,
                            reason=f"حكم قضية {case_id}: {verdict_type} — {reason[:400]}",
                        )
                        timeout_applied = True
                        q.log_action(case_id, interaction.user.id, "تنفيذ Timeout على المتهم", str(duration_delta))
                    except discord.Forbidden:
                        q.log_action(case_id, interaction.user.id, "فشل Timeout (صلاحيات)", str(case["defendant_user_id"]))
                    except Exception as e:
                        q.log_action(case_id, interaction.user.id, "فشل Timeout", str(e))
        msg = "تم تسجيل الحكم وقفله."
        if timeout_applied:
            msg += " تم تنفيذ العقوبة (Timeout) على المتهم."
        elif case.get("defendant_user_id") and punishment_duration:
            msg += " (لم يتم تطبيق Timeout — تأكد من إضافة المتهم عبر /add وصلاحيات البوت)"
        await interaction.response.send_message(msg, ephemeral=True)
        emb = build_case_embed(case, interaction.guild)
        view = CaseActionsView(case_id, self)
        if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
            await interaction.channel.send(embed=emb, view=view)
        if VERDICTS_CHANNEL_ID:
            ch = self.bot.get_channel(VERDICTS_CHANNEL_ID)
            if ch and isinstance(ch, discord.TextChannel):
                ann = build_verdict_announce_embed(case, ch.guild)
                await ch.send(embed=ann)
        await send_log_embed(self.bot, case_id, "صدر الحكم", interaction.user, verdict_type)

    async def _move_channel_to_closed(
        self, channel_id: int, guild: discord.Guild, channel_obj: discord.TextChannel | None = None
    ) -> tuple[bool, str]:
        if not CLOSED_CASES_CATEGORY_ID:
            return False, "CLOSED_CASES_CATEGORY_ID غير مضبوط في Variables"
        category = guild.get_channel(CLOSED_CASES_CATEGORY_ID)
        if not category or not isinstance(category, discord.CategoryChannel):
            return False, "فئة القضايا المغلقة غير موجودة أو الرقم غلط"
        ch = channel_obj or guild.get_channel(channel_id)
        if not ch and channel_id:
            try:
                ch = await self.bot.fetch_channel(channel_id)
            except Exception as e:
                return False, str(e)
        if not ch or not isinstance(ch, discord.TextChannel):
            return False, "القناة غير موجودة"
        try:
            await ch.edit(category=category)
            return True, ""
        except discord.Forbidden:
            return False, "البوت محتاج صلاحية Manage Channels"
        except Exception as e:
            return False, str(e)

    async def on_close(self, interaction: discord.Interaction, case_id: str):
        case = q.get_case_by_id(case_id)
        if not case:
            await interaction.response.send_message("القضية غير موجودة.", ephemeral=True)
            return
        q.update_case_status(case_id, "مغلقة", _now())
        q.log_action(case_id, interaction.user.id, "إغلاق القضية", None)
        ch_obj = None
        if interaction.channel and interaction.channel.id == case.get("channel_id"):
            ch_obj = interaction.channel
        moved, err = await self._move_channel_to_closed(
            case.get("channel_id") or 0, interaction.guild, ch_obj
        ) if interaction.guild else (False, "لا يوجد سيرفر")
        msg = "تم إغلاق القضية."
        if not moved:
            msg += f" (نقل القناة فشل: {err[:200]})"
        await interaction.response.send_message(msg, ephemeral=True)

    async def on_archive(self, interaction: discord.Interaction, case_id: str):
        case = q.get_case_by_id(case_id)
        if not case:
            await interaction.response.send_message("القضية غير موجودة.", ephemeral=True)
            return
        ch = None
        if interaction.guild and case.get("channel_id"):
            ch = interaction.guild.get_channel(case["channel_id"])
            if not ch:
                try:
                    ch = await self.bot.fetch_channel(case["channel_id"])
                except Exception:
                    pass
        if ch and isinstance(ch, discord.TextChannel):
            try:
                path = await export_transcript(ch, case_id)
                if path:
                    await ch.send(f"تم تصدير النقل إلى: `{path}`")
            except Exception:
                pass
        q.update_case_status(case_id, "مؤرشفة", _now())
        q.log_action(case_id, interaction.user.id, "أرشفة القضية", None)
        if interaction.guild and case.get("channel_id"):
            ch_obj = interaction.channel if (interaction.channel and interaction.channel.id == case.get("channel_id")) else None
            await self._move_channel_to_closed(case["channel_id"], interaction.guild, ch_obj)
        await interaction.response.send_message("تم أرشفة القضية.", ephemeral=True)

    async def on_reopen(self, interaction: discord.Interaction, case_id: str):
        q.update_case_status(case_id, "مفتوحة")
        q.log_action(case_id, interaction.user.id, "إعادة فتح القضية", None)
        case = q.get_case_by_id(case_id)
        ch = self.bot.get_channel(case["channel_id"]) if case else None
        if ch and isinstance(ch, discord.TextChannel) and OPEN_CASES_CATEGORY_ID:
            try:
                await ch.edit(category_id=OPEN_CASES_CATEGORY_ID)
            except Exception:
                pass
        await interaction.response.send_message("تم إعادة فتح القضية.", ephemeral=True)

    async def on_appeal_modal(self, interaction: discord.Interaction, case_id: str):
        modal = AppealModal(case_id, self._appeal_callback)
        await interaction.response.send_modal(modal)

    async def _appeal_callback(
        self,
        interaction: discord.Interaction,
        case_id: str,
        reason: str,
        new_evidence: str,
        details: str,
    ):
        case = q.get_case_by_id(case_id)
        if not case or case["creator_id"] != interaction.user.id:
            await interaction.response.send_message("غير مصرح.", ephemeral=True)
            return
        pend = q.get_pending_appeal(case_id)
        if pend:
            await interaction.response.send_message("يوجد استئناف معلق مسبقاً.", ephemeral=True)
            return
        q.submit_appeal(case_id, interaction.user.id, reason, new_evidence, details)
        q.log_action(case_id, interaction.user.id, "تقديم استئناف", reason[:200])
        await interaction.response.send_message("تم تقديم الاستئناف. بانتظار المراجعة.", ephemeral=True)
        case = q.get_case_by_id(case_id)
        emb = build_case_embed(case, interaction.guild)
        view = CaseActionsView(case_id, self)
        if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
            await interaction.channel.send(embed=emb, view=view)

    @app_commands.command(name="setup_cases", description="إعداد قناة رفع المحاضر")
    @app_commands.describe(channel="القناة التي سيُرسل فيها زر رفع المحضر")
    async def setup_cases(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not is_staff(interaction.user):
            await interaction.response.send_message("ليس لديك صلاحية الإعداد.", ephemeral=True)
            return
        emb = discord.Embed(
            title="رفع محضر / شكوى رسمية",
            description="اضغط الزر أدناه لفتح نموذج رفع محضر جديد.",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow(),
        )
        emb.set_footer(text="نظام إدارة المحاضر")
        view = SetupCasesView(self._submit_callback)
        await channel.send(embed=emb, view=view)
        await interaction.response.send_message(f"تم إرسال الزر في {channel.mention}", ephemeral=True)

    @app_commands.command(name="case_open_manual", description="فتح قضية يدوياً (للمشرفين)")
    @app_commands.describe(
        defendant="المشتكى عليه",
        case_type="نوع القضية",
        description="وصف القضية",
        evidence="الأدلة",
        witnesses="الشهود (اختياري)",
    )
    async def case_open_manual(
        self,
        interaction: discord.Interaction,
        defendant: str,
        case_type: str,
        description: str,
        evidence: str,
        witnesses: str = "",
    ):
        if not can_manage_case(interaction.user):
            await interaction.response.send_message("صلاحية المشرفين فقط.", ephemeral=True)
            return
        await self._submit_callback(
            interaction, defendant, case_type, description, evidence, witnesses
        )

    @app_commands.command(name="case_view", description="عرض تفاصيل قضية")
    @app_commands.describe(case_id="رقم القضية مثل CASE-1001")
    async def case_view(self, interaction: discord.Interaction, case_id: str):
        case = q.get_case_by_id(case_id.strip())
        if not case:
            await interaction.response.send_message("القضية غير موجودة.", ephemeral=True)
            return
        if not interaction.guild:
            await interaction.response.send_message("هذا الأمر يعمل داخل السيرفر فقط.", ephemeral=True)
            return
        if case["creator_id"] != interaction.user.id and not is_staff(interaction.user):
            await interaction.response.send_message("لا يمكنك عرض هذه القضية.", ephemeral=True)
            return
        emb = build_case_embed(case, interaction.guild)
        await interaction.response.send_message(embed=emb, ephemeral=True)

    @app_commands.command(name="case_list", description="قائمة القضايا")
    @app_commands.describe(status="تصفية حسب الحالة (اختياري)", my_cases="عرض قضاياي فقط")
    @app_commands.choices(status=[app_commands.Choice(name=s, value=s) for s in CASE_STATUSES])
    async def case_list(
        self,
        interaction: discord.Interaction,
        my_cases: bool = False,
        status: str | None = None,
    ):
        if not interaction.guild:
            await interaction.response.send_message("هذا الأمر يعمل داخل السيرفر فقط.", ephemeral=True)
            return
        creator = interaction.user.id if my_cases else None
        cases = q.list_cases(interaction.guild.id, creator_id=creator, status=status)
        if my_cases and status:
            cases = [c for c in cases if c["status"] == status]
        title = "قائمة القضايا" + (" (قضاياي)" if my_cases else "") + (f" — {status}" if status else "")
        emb = build_list_embed(cases, title)
        await interaction.response.send_message(embed=emb, ephemeral=True)

    @app_commands.command(name="case_assign", description="تعيين مشرف للقضية")
    @app_commands.describe(case_id="رقم القضية", staff_member="المشرف")
    async def case_assign(
        self,
        interaction: discord.Interaction,
        case_id: str,
        staff_member: discord.Member,
    ):
        if not can_manage_case(interaction.user):
            await interaction.response.send_message("صلاحية المشرفين فقط.", ephemeral=True)
            return
        case = q.get_case_by_id(case_id.strip())
        if not case:
            await interaction.response.send_message("القضية غير موجودة.", ephemeral=True)
            return
        q.assign_staff(case_id.strip(), staff_member.id)
        q.log_action(case_id.strip(), interaction.user.id, "تعيين مشرف", str(staff_member.id))
        await interaction.response.send_message(f"تم تعيين {staff_member.mention} كمشرف على القضية.", ephemeral=True)

    @app_commands.command(name="case_assign_judge", description="تعيين قاضٍ للقضية")
    @app_commands.describe(case_id="رقم القضية", judge_member="القاضي")
    async def case_assign_judge(
        self,
        interaction: discord.Interaction,
        case_id: str,
        judge_member: discord.Member,
    ):
        if not can_manage_case(interaction.user):
            await interaction.response.send_message("صلاحية المشرفين فقط.", ephemeral=True)
            return
        case = q.get_case_by_id(case_id.strip())
        if not case:
            await interaction.response.send_message("القضية غير موجودة.", ephemeral=True)
            return
        q.assign_judge(case_id.strip(), judge_member.id)
        q.log_action(case_id.strip(), interaction.user.id, "تعيين قاضٍ", str(judge_member.id))
        await interaction.response.send_message(f"تم تعيين {judge_member.mention} قاضياً للقضية.", ephemeral=True)

    @app_commands.command(name="add", description="إضافة المتهم (عضو) للقضية")
    @app_commands.describe(case_id="رقم القضية", member="العضو")
    async def case_add_defendant(
        self,
        interaction: discord.Interaction,
        case_id: str,
        member: discord.Member,
    ):
        if not can_manage_case(interaction.user):
            await interaction.response.send_message("صلاحية المشرفين فقط.", ephemeral=True)
            return
        case = q.get_case_by_id(case_id.strip())
        if not case:
            await interaction.response.send_message("القضية غير موجودة.", ephemeral=True)
            return
        ch = self.bot.get_channel(case["channel_id"]) if case.get("channel_id") else None
        if ch and isinstance(ch, discord.TextChannel):
            await ch.set_permissions(member, read_messages=True, send_messages=True)
        q.set_defendant_user(case_id.strip(), member.id)
        q.log_action(case_id.strip(), interaction.user.id, "إضافة المتهم", str(member.id))
        await interaction.response.send_message(f"تم إضافة {member.mention} للقضية ومنحه الوصول للقناة.", ephemeral=True)

    @app_commands.command(name="case_status", description="تغيير حالة القضية")
    @app_commands.describe(case_id="رقم القضية", status="الحالة الجديدة")
    @app_commands.choices(status=[app_commands.Choice(name=s, value=s) for s in CASE_STATUSES])
    async def case_status(
        self,
        interaction: discord.Interaction,
        case_id: str,
        status: str,
    ):
        if not can_manage_case(interaction.user):
            await interaction.response.send_message("صلاحية المشرفين فقط.", ephemeral=True)
            return
        case = q.get_case_by_id(case_id.strip())
        if not case:
            await interaction.response.send_message("القضية غير موجودة.", ephemeral=True)
            return
        q.update_case_status(case_id.strip(), status)
        q.log_action(case_id.strip(), interaction.user.id, "تغيير الحالة", status)
        await interaction.response.send_message(f"تم تحديث الحالة إلى: {status}", ephemeral=True)

    @app_commands.command(name="case_note", description="إضافة ملاحظة إدارية")
    @app_commands.describe(case_id="رقم القضية", note="الملاحظة")
    async def case_note(self, interaction: discord.Interaction, case_id: str, note: str):
        if not can_manage_case(interaction.user):
            await interaction.response.send_message("صلاحية المشرفين فقط.", ephemeral=True)
            return
        case = q.get_case_by_id(case_id.strip())
        if not case:
            await interaction.response.send_message("القضية غير موجودة.", ephemeral=True)
            return
        q.add_note(case_id.strip(), interaction.user.id, note)
        q.log_action(case_id.strip(), interaction.user.id, "ملاحظة إدارية", note[:200])
        await interaction.response.send_message("تم حفظ الملاحظة.", ephemeral=True)

    @app_commands.command(name="case_verdict", description="فتح نموذج إصدار الحكم (قاضي/أدمن)")
    @app_commands.describe(case_id="رقم القضية")
    async def case_verdict(self, interaction: discord.Interaction, case_id: str):
        if not can_issue_verdict(interaction.user):
            await interaction.response.send_message("صلاحية القضاة والإدمن فقط.", ephemeral=True)
            return
        case = q.get_case_by_id(case_id.strip())
        if not case:
            await interaction.response.send_message("القضية غير موجودة.", ephemeral=True)
            return
        if case.get("verdict_locked"):
            await interaction.response.send_message(
                "الحكم مقفل. استخدم case_override_unlock_verdict إذا كنت أدمن.",
                ephemeral=True,
            )
            return
        modal = VerdictModal(case_id.strip(), self._verdict_callback)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="case_close", description="إغلاق القضية")
    @app_commands.describe(case_id="رقم القضية")
    async def case_close(self, interaction: discord.Interaction, case_id: str):
        if not can_manage_case(interaction.user):
            await interaction.response.send_message("صلاحية المشرفين فقط.", ephemeral=True)
            return
        case = q.get_case_by_id(case_id.strip())
        if not case:
            await interaction.response.send_message("القضية غير موجودة.", ephemeral=True)
            return
        q.update_case_status(case_id.strip(), "مغلقة", _now())
        q.log_action(case_id.strip(), interaction.user.id, "إغلاق القضية", None)
        moved, err = False, ""
        if interaction.guild and case.get("channel_id"):
            ch_obj = interaction.channel if (interaction.channel and interaction.channel.id == case.get("channel_id")) else None
            moved, err = await self._move_channel_to_closed(case["channel_id"], interaction.guild, ch_obj)
        msg = "تم إغلاق القضية."
        if not moved and case.get("channel_id"):
            msg += f" (نقل القناة فشل: {err[:200]})"
        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(name="case_archive", description="أرشفة القضية")
    @app_commands.describe(case_id="رقم القضية")
    async def case_archive(self, interaction: discord.Interaction, case_id: str):
        if not can_manage_case(interaction.user):
            await interaction.response.send_message("صلاحية المشرفين فقط.", ephemeral=True)
            return
        case = q.get_case_by_id(case_id.strip())
        if not case:
            await interaction.response.send_message("القضية غير موجودة.", ephemeral=True)
            return
        ch = None
        if interaction.guild and case.get("channel_id"):
            ch = interaction.guild.get_channel(case["channel_id"])
            if not ch:
                try:
                    ch = await self.bot.fetch_channel(case["channel_id"])
                except Exception:
                    pass
        if ch and isinstance(ch, discord.TextChannel):
            try:
                path = await export_transcript(ch, case_id.strip())
                if path:
                    await ch.send(f"تم تصدير النقل: `{path}`")
            except Exception:
                pass
        q.update_case_status(case_id.strip(), "مؤرشفة", _now())
        q.log_action(case_id.strip(), interaction.user.id, "أرشفة القضية", None)
        if interaction.guild and case.get("channel_id"):
            ch_obj = interaction.channel if (interaction.channel and interaction.channel.id == case.get("channel_id")) else None
            await self._move_channel_to_closed(case["channel_id"], interaction.guild, ch_obj)
        await interaction.response.send_message("تم أرشفة القضية.", ephemeral=True)

    @app_commands.command(name="case_reopen", description="إعادة فتح القضية")
    @app_commands.describe(case_id="رقم القضية")
    async def case_reopen(self, interaction: discord.Interaction, case_id: str):
        if not can_manage_case(interaction.user):
            await interaction.response.send_message("صلاحية المشرفين فقط.", ephemeral=True)
            return
        case = q.get_case_by_id(case_id.strip())
        if not case:
            await interaction.response.send_message("القضية غير موجودة.", ephemeral=True)
            return
        q.update_case_status(case_id.strip(), "مفتوحة")
        q.log_action(case_id.strip(), interaction.user.id, "إعادة فتح القضية", None)
        ch = self.bot.get_channel(case["channel_id"]) if case.get("channel_id") else None
        if ch and isinstance(ch, discord.TextChannel) and OPEN_CASES_CATEGORY_ID:
            try:
                await ch.edit(category_id=OPEN_CASES_CATEGORY_ID)
            except Exception:
                pass
        await interaction.response.send_message("تم إعادة فتح القضية.", ephemeral=True)

    @app_commands.command(name="case_logs", description="عرض سجل القضية")
    @app_commands.describe(case_id="رقم القضية")
    async def case_logs(self, interaction: discord.Interaction, case_id: str):
        case = q.get_case_by_id(case_id.strip())
        if not case:
            await interaction.response.send_message("القضية غير موجودة.", ephemeral=True)
            return
        if case["creator_id"] != interaction.user.id and not is_staff(interaction.user):
            await interaction.response.send_message("لا يمكنك عرض السجل.", ephemeral=True)
            return
        from utils.embeds import build_log_embed
        logs = q.get_logs(case_id.strip())
        emb = build_log_embed(logs, case_id.strip(), interaction.guild)
        await interaction.response.send_message(embed=emb, ephemeral=True)

    @app_commands.command(name="case_appeal_review", description="قبول أو رفض الاستئناف")
    @app_commands.describe(case_id="رقم القضية", action="قبول أو رفض")
    @app_commands.choices(action=[
        app_commands.Choice(name="قبول", value="مقبول"),
        app_commands.Choice(name="رفض", value="مرفوض"),
    ])
    async def case_appeal_review(
        self,
        interaction: discord.Interaction,
        case_id: str,
        action: str,
    ):
        if not is_judge(interaction.user):
            await interaction.response.send_message("صلاحية القضاة والإدمن فقط.", ephemeral=True)
            return
        appeal = q.get_pending_appeal(case_id.strip())
        if not appeal:
            await interaction.response.send_message("لا يوجد استئناف معلق لهذه القضية.", ephemeral=True)
            return
        q.set_appeal_status(appeal["id"], action)
        q.log_action(case_id.strip(), interaction.user.id, f"استئناف {action}", str(appeal["id"]))
        if action == "مقبول":
            q.update_case_status(case_id.strip(), "قيد المراجعة")
        await interaction.response.send_message(f"تم {action} الاستئناف.", ephemeral=True)

    @app_commands.command(name="case_override_unlock_verdict", description="فتح قفل الحكم (أدمن فقط)")
    @app_commands.describe(case_id="رقم القضية")
    async def case_override_unlock_verdict(self, interaction: discord.Interaction, case_id: str):
        if not can_override_verdict(interaction.user):
            await interaction.response.send_message("صلاحية الأدمن فقط.", ephemeral=True)
            return
        case = q.get_case_by_id(case_id.strip())
        if not case:
            await interaction.response.send_message("القضية غير موجودة.", ephemeral=True)
            return
        q.unlock_verdict(case_id.strip())
        q.log_action(case_id.strip(), interaction.user.id, "فتح قفل الحكم (أدمن)", None)
        await interaction.response.send_message("تم فتح قفل الحكم. يمكنك الآن تعديله عبر case_verdict.", ephemeral=True)


