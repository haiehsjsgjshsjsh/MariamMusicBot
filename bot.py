import os
import json
import random
import re
import asyncio
from pathlib import Path

from pyrogram import Client, filters, idle
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatPermissions,
    ChatPrivileges,
)

from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, GroupCallConfig


# =========================================================
# START TEST
# =========================================================

print("========== BOT FILE STARTED ==========")


# =========================================================
# ENV
# =========================================================

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
SESSION_STRING = os.environ["SESSION_STRING"]

PHOTO_PATH = "IMG_20260922_130735_050.jpg"


# =========================================================
# CLIENTS
# =========================================================

bot = Client(
    "MariamMusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

assistant = Client(
    "MariamMusicAssistant",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
)

calls = None


# =========================================================
# DATA
# =========================================================

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

CUSTOM_FILE = DATA_DIR / "custom_replies.json"
SETTINGS_FILE = DATA_DIR / "group_settings.json"
WARNINGS_FILE = DATA_DIR / "warnings.json"


def load_json(path, default):
    try:
        if not path.exists():
            path.write_text(
                json.dumps(
                    default,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            return default

        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except Exception:
        return default


def save_json(path, data):
    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


custom_replies = load_json(
    CUSTOM_FILE,
    {},
)

group_settings = load_json(
    SETTINGS_FILE,
    {},
)

warnings_data = load_json(
    WARNINGS_FILE,
    {},
)


# =========================================================
# MUSIC DATA
# =========================================================

queues = {}
current_song = {}
waiting_for_song = set()


# =========================================================
# GAME DATA
# =========================================================

games = {}


# =========================================================
# BAD WORDS
# =========================================================

BAD_WORDS = [
    "كلمة_ممنوعة_1",
    "كلمة_ممنوعة_2",
]


# =========================================================
# COMMANDS
# =========================================================

HELP_TEXT = """
🎀 **مريومه الدلوعه**

🎵 **الميوزك**
• تشغيل
• تشغيل اسم الأغنية
• تخطي
• وقف
• إيقاف
• القائمة

🎮 **الألعاب**
• العاب
• اكتب اسم أي لعبة من القائمة

👑 **الإدارة**
• تفعيل البوت
• تعطيل البوت
• رتبتي
• المالك
• المشرفين
• ترقية
• تنزيل
• طرد
• حظر
• فك حظر
• كتم
• فك كتم

⚠️ **التحذيرات**
• تحذير
• تحذيرات
• مسح تحذيرات

📌 **التثبيت**
• تثبيت
• إلغاء تثبيت

🔒 **الحماية**
• قفل الروابط
• فتح الروابط
• قفل الصور
• فتح الصور
• قفل الفيديو
• فتح الفيديو
• قفل الملصقات
• فتح الملصقات
• قفل الصوت
• فتح الصوت
• قفل السب
• فتح السب

💬 **الردود**
• اضف رد الكلمة = الرد
• مسح رد الكلمة

🎮 اكتب `العاب` لرؤية كل الألعاب.
"""


# =========================================================
# 120+ GAMES
# =========================================================

GAME_NAMES = [
    "إكس أو",
    "حجر ورق مقص",
    "تخمين الرقم",
    "تخمين الحرف",
    "صح أو خطأ",
    "أسئلة عامة",
    "رياضيات سريعة",
    "أكمل الكلمة",
    "خمن الحيوان",
    "خمن الدولة",
    "خمن العاصمة",
    "خمن اللاعب",
    "خمن الفيلم",
    "خمن المسلسل",
    "خمن الأغنية",
    "خمن الشخصية",
    "خمن السيارة",
    "خمن الماركة",
    "خمن العلم",
    "خمن الطعام",
    "خمن الفاكهة",
    "خمن الخضار",
    "خمن اللون",
    "خمن المهنة",
    "خمن الرياضة",
    "خمن النادي",
    "خمن المنتخب",
    "خمن المدينة",
    "خمن القارة",
    "خمن الكوكب",
    "خمن الحيوان من الوصف",
    "خمن الشيء",
    "خمن الكلمة",
    "السرعة",
    "أسرع إجابة",
    "أسرع رقم",
    "أسرع حرف",
    "أسرع لون",
    "أسرع كلمة",
    "ذاكرة",
    "اختبار الذاكرة",
    "ترتيب الأرقام",
    "ترتيب الحروف",
    "عد تنازلي",
    "عد تصاعدي",
    "حساب سريع",
    "جمع سريع",
    "طرح سريع",
    "ضرب سريع",
    "قسمة سريعة",
    "نعم أو لا",
    "مين أنا",
    "من الأكثر",
    "اختار واحد",
    "اختيار عشوائي",
    "الحظ",
    "صندوق الحظ",
    "عجلة الحظ",
    "رقم الحظ",
    "تحدي اليوم",
    "تحدي السرعة",
    "تحدي الذكاء",
    "تحدي الذاكرة",
    "تحدي الحساب",
    "تحدي الكلمات",
    "تحدي الحروف",
    "تحدي الدول",
    "تحدي العواصم",
    "تحدي الحيوانات",
    "تحدي السيارات",
    "تحدي الأفلام",
    "تحدي الأغاني",
    "تحدي الرياضة",
    "مسابقة عامة",
    "مسابقة رياضيات",
    "مسابقة حيوانات",
    "مسابقة دول",
    "مسابقة عواصم",
    "مسابقة سيارات",
    "مسابقة أفلام",
    "مسابقة أغاني",
    "مسابقة كرة قدم",
    "مسابقة معلومات",
    "لغز اليوم",
    "لغز سريع",
    "لغز صعب",
    "لغز سهل",
    "لغز رياضي",
    "لغز كلمات",
    "لغز من أنا",
    "كلمة السر",
    "البحث عن الكلمة",
    "الكلمة المفقودة",
    "الحرف المفقود",
    "المختلف",
    "اعثر على المختلف",
    "صحح الجملة",
    "أكمل الجملة",
    "أكمل المثل",
    "أكمل الأغنية",
    "تحدي الأمثال",
    "تحدي الثقافة",
    "تحدي التاريخ",
    "تحدي الجغرافيا",
    "تحدي العلوم",
    "تحدي التكنولوجيا",
    "تحدي السيارات 2",
    "تحدي كرة القدم 2",
    "تحدي الذكاء 2",
    "تحدي الحظ 2",
    "تحدي الأصدقاء",
    "تحدي شخصين",
    "تحدي ضد البوت",
    "من يفوز",
    "المواجهة",
    "المباراة",
    "النهائي",
    "البطل",
    "ملك الأسئلة",
    "ملك السرعة",
    "ملك الحساب",
    "ملك الحروف",
    "ملك المعلومات",
]


TWO_PLAYER_GAMES = {
    "إكس أو",
    "حجر ورق مقص",
    "تخمين الرقم",
    "تخمين الحرف",
    "تحدي شخصين",
    "تحدي الأصدقاء",
    "تحدي ضد البوت",
    "من يفوز",
    "المواجهة",
    "المباراة",
    "النهائي",
    "ملك السرعة",
    "ملك الحساب",
    "ملك الحروف",
}


def normalize(text):
    if not text:
        return ""

    text = text.strip().lower()

    text = text.replace("أ", "ا")
    text = text.replace("إ", "ا")
    text = text.replace("آ", "ا")
    text = text.replace("ى", "ي")

    return text


GAME_LOOKUP = {
    normalize(x): x
    for x in GAME_NAMES
}


# =========================================================
# SETTINGS
# =========================================================

def get_settings(chat_id):
    key = str(chat_id)

    if key not in group_settings:
        group_settings[key] = {
            "enabled": True,
            "links": False,
            "photos": False,
            "videos": False,
            "stickers": False,
            "audio": False,
            "bad_words": False,
        }

        save_json(
            SETTINGS_FILE,
            group_settings,
        )

    return group_settings[key]


# =========================================================
# ADMIN
# =========================================================

async def is_admin(chat_id, user_id):
    try:
        member = await bot.get_chat_member(
            chat_id,
            user_id,
        )

        status = str(
            member.status
        ).lower()

        return (
            "administrator" in status
            or "owner" in status
            or "creator" in status
        )

    except Exception:
        return False


async def get_rank(chat_id, user_id):
    try:
        member = await bot.get_chat_member(
            chat_id,
            user_id,
        )

        status = str(
            member.status
        ).lower()

        if (
            "owner" in status
            or "creator" in status
        ):
            return "المالك 👑"

        if (
            "administrator" in status
            or "admin" in status
        ):
            return "مشرف 🛡️"

        if "member" in status:
            return "عضو 👤"

        return "غير معروف"

    except Exception:
        return "غير معروف"


async def require_admin(message):
    if not await is_admin(
        message.chat.id,
        message.from_user.id,
    ):
        await message.reply_text(
            "❌ الأمر ده للمشرفين فقط."
        )
        return False

    return True


# =========================================================
# START
# =========================================================

@bot.on_message(
    filters.command(
        "start",
        prefixes="/",
    )
)
async def start_handler(client, message):
    await message.reply_text(
        "🎀 أهلاً بيك في مريومه الدلوعه!\n\n"
        "اكتب `الأوامر` لمعرفة كل الأوامر."
    )


# =========================================================
# HELP
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(
        r"^(الأوامر|الاوامر|مساعدة|مساعده)$"
    )
)
async def help_handler(client, message):
    await message.reply_text(
        HELP_TEXT
    )


# =========================================================
# ENABLE / DISABLE
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(
        r"^(تفعيل البوت|تعطيل البوت)$"
    )
)
async def enable_handler(client, message):

    if not await require_admin(message):
        return

    settings = get_settings(
        message.chat.id
    )

    if message.text.strip() == "تفعيل البوت":

        settings["enabled"] = True

        save_json(
            SETTINGS_FILE,
            group_settings,
        )

        await message.reply_text(
            "✅ تم تفعيل البوت."
        )

    else:

        settings["enabled"] = False

        save_json(
            SETTINGS_FILE,
            group_settings,
        )

        await message.reply_text(
            "⛔ تم تعطيل البوت."
        )


# =========================================================
# RANK
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^رتبتي$")
)
async def rank_handler(client, message):

    rank = await get_rank(
        message.chat.id,
        message.from_user.id,
    )

    await message.reply_text(
        f"📌 رتبتك: {rank}"
    )


# =========================================================
# OWNER
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^المالك$")
)
async def owner_handler(client, message):

    try:

        text = "👑 **مالك المجموعة:**\n\n"

        found = False

        async for member in bot.get_chat_members(
            message.chat.id,
            filter="administrators",
        ):

            status = str(
                member.status
            ).lower()

            if (
                "owner" in status
                or "creator" in status
            ):

                found = True

                user = member.user

                text += (
                    f"• {user.first_name}"
                )

                if user.username:
                    text += (
                        f" @{user.username}"
                    )

                text += "\n"

        if not found:
            text = (
                "❌ مش قادر أحدد المالك."
            )

        await message.reply_text(
            text
        )

    except Exception as e:
        await message.reply_text(
            f"❌ حصل خطأ:\n{e}"
        )


# =========================================================
# ADMINS
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^المشرفين$")
)
async def admins_handler(client, message):

    try:

        text = "🛡️ **مشرفين المجموعة:**\n\n"

        async for member in bot.get_chat_members(
            message.chat.id,
            filter="administrators",
        ):

            status = str(
                member.status
            ).lower()

            if (
                "administrator" in status
                or "owner" in status
                or "creator" in status
            ):

                user = member.user

                text += (
                    f"• {user.first_name}"
                )

                if user.username:
                    text += (
                        f" @{user.username}"
                    )

                if (
                    "owner" in status
                    or "creator" in status
                ):
                    text += " 👑"
                else:
                    text += " 🛡️"

                text += "\n"

        await message.reply_text(
            text
        )

    except Exception as e:
        await message.reply_text(
            f"❌ حصل خطأ:\n{e}"
        )


# =========================================================
# PROMOTE
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^ترقية$")
)
async def promote_handler(client, message):

    if not await require_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "↩️ اعمل رد على الشخص واكتب: ترقية"
        )
        return

    user_id = (
        message.reply_to_message
        .from_user
        .id
    )

    try:

        privileges = ChatPrivileges(
            can_manage_chat=True,
            can_delete_messages=True,
            can_manage_video_chats=True,
            can_restrict_members=True,
            can_promote_members=False,
            can_change_info=True,
            can_invite_users=True,
            can_pin_messages=True,
        )

        await bot.promote_chat_member(
            message.chat.id,
            user_id,
            privileges=privileges,
        )

        await message.reply_text(
            "✅ تمت ترقية العضو."
        )

    except Exception as e:

        await message.reply_text(
            f"❌ فشلت الترقية:\n{e}"
        )


# =========================================================
# DEMOTE
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^تنزيل$")
)
async def demote_handler(client, message):

    if not await require_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "↩️ اعمل رد على المشرف واكتب: تنزيل"
        )
        return

    user_id = (
        message.reply_to_message
        .from_user
        .id
    )

    try:

        privileges = ChatPrivileges(
            can_manage_chat=False,
            can_delete_messages=False,
            can_manage_video_chats=False,
            can_restrict_members=False,
            can_promote_members=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False,
        )

        await bot.promote_chat_member(
            message.chat.id,
            user_id,
            privileges=privileges,
        )

        await message.reply_text(
            "✅ تم تنزيل الرتبة."
        )

    except Exception as e:

        await message.reply_text(
            f"❌ حصل خطأ:\n{e}"
        )


# =========================================================
# KICK
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^طرد$")
)
async def kick_handler(client, message):

    if not await require_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "↩️ اعمل رد على العضو واكتب: طرد"
        )
        return

    user_id = (
        message.reply_to_message
        .from_user
        .id
    )

    try:

        await bot.ban_chat_member(
            message.chat.id,
            user_id,
        )

        await bot.unban_chat_member(
            message.chat.id,
            user_id,
        )

        await message.reply_text(
            "🚪 تم طرد العضو."
        )

    except Exception as e:

        await message.reply_text(
            f"❌ حصل خطأ:\n{e}"
        )


# =========================================================
# BAN
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^حظر$")
)
async def ban_handler(client, message):

    if not await require_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "↩️ اعمل رد على العضو واكتب: حظر"
        )
        return

    user_id = (
        message.reply_to_message
        .from_user
        .id
    )

    try:

        await bot.ban_chat_member(
            message.chat.id,
            user_id,
        )

        await message.reply_text(
            "🚫 تم حظر العضو."
        )

    except Exception as e:

        await message.reply_text(
            f"❌ حصل خطأ:\n{e}"
        )


# =========================================================
# UNBAN
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^فك حظر$")
)
async def unban_handler(client, message):

    if not await require_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "↩️ اعمل رد على العضو واكتب: فك حظر"
        )
        return

    user_id = (
        message.reply_to_message
        .from_user
        .id
    )

    try:

        await bot.unban_chat_member(
            message.chat.id,
            user_id,
        )

        await message.reply_text(
            "✅ تم فك الحظر."
        )

    except Exception as e:

        await message.reply_text(
            f"❌ حصل خطأ:\n{e}"
        )


# =========================================================
# MUTE
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^كتم$")
)
async def mute_handler(client, message):

    if not await require_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "↩️ اعمل رد على العضو واكتب: كتم"
        )
        return

    user_id = (
        message.reply_to_message
        .from_user
        .id
    )

    try:

        await bot.restrict_chat_member(
            message.chat.id,
            user_id,
            permissions=ChatPermissions(
                can_send_messages=False
            ),
        )

        await message.reply_text(
            "🔇 تم كتم العضو."
        )

    except Exception as e:

        await message.reply_text(
            f"❌ حصل خطأ:\n{e}"
        )


# =========================================================
# UNMUTE
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^فك كتم$")
)
async def unmute_handler(client, message):

    if not await require_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "↩️ اعمل رد على العضو واكتب: فك كتم"
        )
        return

    user_id = (
        message.reply_to_message
        .from_user
        .id
    )

    try:

        await bot.restrict_chat_member(
            message.chat.id,
            user_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_send_polls=True,
                can_add_web_page_previews=True,
                can_invite_users=True,
            ),
        )

        await message.reply_text(
            "🔊 تم فك الكتم."
        )

    except Exception as e:

        await message.reply_text(
            f"❌ حصل خطأ:\n{e}"
        )


# =========================================================
# WARN
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^تحذير$")
)
async def warn_handler(client, message):

    if not await require_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "↩️ اعمل رد على العضو واكتب: تحذير"
        )
        return

    user = (
        message.reply_to_message
        .from_user
    )

    chat_id = str(
        message.chat.id
    )

    user_id = str(
        user.id
    )

    warnings_data.setdefault(
        chat_id,
        {},
    )

    warnings_data[chat_id][user_id] = (
        warnings_data[chat_id].get(
            user_id,
            0,
        ) + 1
    )

    save_json(
        WARNINGS_FILE,
        warnings_data,
    )

    count = warnings_data[
        chat_id
    ][user_id]

    await message.reply_text(
        f"⚠️ تم تحذير {user.first_name}\n"
        f"عدد التحذيرات: {count}"
    )


# =========================================================
# WARNINGS
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^تحذيرات$")
)
async def warnings_handler(client, message):

    if not message.reply_to_message:
        await message.reply_text(
            "↩️ اعمل رد على العضو واكتب: تحذيرات"
        )
        return

    user = (
        message.reply_to_message
        .from_user
    )

    count = warnings_data.get(
        str(message.chat.id),
        {},
    ).get(
        str(user.id),
        0,
    )

    await message.reply_text(
        f"⚠️ تحذيرات {user.first_name}: {count}"
    )


# =========================================================
# CLEAR WARNINGS
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(
        r"^مسح تحذيرات$"
    )
)
async def clear_warnings_handler(
    client,
    message,
):

    if not await require_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "↩️ اعمل رد على العضو واكتب: مسح تحذيرات"
        )
        return

    user_id = str(
        message.reply_to_message
        .from_user
        .id
    )

    chat_id = str(
        message.chat.id
    )

    warnings_data.setdefault(
        chat_id,
        {},
    )

    warnings_data[chat_id][user_id] = 0

    save_json(
        WARNINGS_FILE,
        warnings_data,
    )

    await message.reply_text(
        "✅ تم مسح التحذيرات."
    )


# =========================================================
# PIN
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^تثبيت$")
)
async def pin_handler(client, message):

    if not await require_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "↩️ اعمل رد على الرسالة واكتب: تثبيت"
        )
        return

    try:

        await bot.pin_chat_message(
            message.chat.id,
            message.reply_to_message.id,
        )

        await message.reply_text(
            "📌 تم تثبيت الرسالة."
        )

    except Exception as e:
        await message.reply_text(
            f"❌ {e}"
        )


# =========================================================
# UNPIN
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(
        r"^إلغاء تثبيت$"
    )
)
async def unpin_handler(client, message):

    if not await require_admin(message):
        return

    try:

        await bot.unpin_chat_message(
            message.chat.id
        )

        await message.reply_text(
            "📌 تم إلغاء التثبيت."
        )

    except Exception as e:
        await message.reply_text(
            f"❌ {e}"
        )


# =========================================================
# PROTECTION
# =========================================================

PROTECTION = {
    "قفل الروابط": "links",
    "فتح الروابط": "links",
    "قفل الصور": "photos",
    "فتح الصور": "photos",
    "قفل الفيديو": "videos",
    "فتح الفيديو": "videos",
    "قفل الملصقات": "stickers",
    "فتح الملصقات": "stickers",
    "قفل الصوت": "audio",
    "فتح الصوت": "audio",
    "قفل السب": "bad_words",
    "فتح السب": "bad_words",
}


@bot.on_message(
    filters.group
    & filters.text
)
async def protection_settings_handler(
    client,
    message,
):

    command = message.text.strip()

    if command not in PROTECTION:
        return

    if not await require_admin(message):
        return

    setting = PROTECTION[command]

    settings = get_settings(
        message.chat.id
    )

    if command.startswith("قفل"):
        settings[setting] = True
        result = "🔒 تم القفل."

    else:
        settings[setting] = False
        result = "🔓 تم الفتح."

    save_json(
        SETTINGS_FILE,
        group_settings,
    )

    await message.reply_text(
        result
    )


# =========================================================
# CUSTOM REPLIES
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
)
async def custom_reply_commands(
    client,
    message,
):

    text = message.text.strip()

    # ADD
    if text.startswith("اضف رد "):

        if not await require_admin(message):
            return

        raw = text[7:].strip()

        if "=" not in raw:
            await message.reply_text(
                "❌ استخدم:\n"
                "اضف رد الكلمة = الرد"
            )
            return

        trigger, reply = raw.split(
            "=",
            1,
        )

        trigger = trigger.strip()
        reply = reply.strip()

        if not trigger or not reply:
            await message.reply_text(
                "❌ اكتب الكلمة والرد."
            )
            return

        chat_id = str(
            message.chat.id
        )

        custom_replies.setdefault(
            chat_id,
            {},
        )

        if (
            trigger
            not in custom_replies[chat_id]
            and len(
                custom_replies[chat_id]
            ) >= 500
        ):
            await message.reply_text(
                "❌ الحد الأقصى 500 رد."
            )
            return

        custom_replies[
            chat_id
        ][trigger] = reply

        save_json(
            CUSTOM_FILE,
            custom_replies,
        )

        await message.reply_text(
            f"✅ تم إضافة الرد.\n\n"
            f"الكلمة: {trigger}\n"
            f"الرد: {reply}"
        )

        return

    # DELETE
    if text.startswith("مسح رد "):

        if not await require_admin(message):
            return

        trigger = text[7:].strip()

        chat_id = str(
            message.chat.id
        )

        if trigger in custom_replies.get(
            chat_id,
            {},
        ):

            del custom_replies[
                chat_id
            ][trigger]

            save_json(
                CUSTOM_FILE,
                custom_replies,
            )

            await message.reply_text(
                "✅ تم مسح الرد."
            )

        else:

            await message.reply_text(
                "❌ الرد مش موجود."
            )


# =========================================================
# CUSTOM REPLY RESPONSE
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
)
async def custom_reply_response(
    client,
    message,
):

    text = message.text.strip()

    if (
        text.startswith("اضف رد ")
        or text.startswith("مسح رد ")
    ):
        return

    chat_id = str(
        message.chat.id
    )

    reply = custom_replies.get(
        chat_id,
        {},
    ).get(text)

    if reply:
        await message.reply_text(
            reply
        )


# =========================================================
# GAMES LIST
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(
        r"^(العاب|ألعاب)$"
    )
)
async def games_list_handler(
    client,
    message,
):

    lines = [
        "🎮 **ألعاب مريومه الدلوعه**",
        "",
        "🤖 = ضد البوت",
        "👥 = لاعبين",
        "",
    ]

    for number, game_name in enumerate(
        GAME_NAMES,
        1,
    ):

        icon = (
            "👥"
            if game_name in TWO_PLAYER_GAMES
            else "🤖"
        )

        lines.append(
            f"{number}. {icon} {game_name}"
        )

    text = "\n".join(lines)

    chunks = []

    while len(text) > 3900:

        position = text.rfind(
            "\n",
            0,
            3900,
        )

        if position == -1:
            position = 3900

        chunks.append(
            text[:position]
        )

        text = text[
            position + 1:
        ]

    if text:
        chunks.append(text)

    for chunk in chunks:
        await message.reply_text(
            chunk
        )


# =========================================================
# GAME START
# =========================================================

async def start_game(
    message,
    game_name,
):

    chat_id = message.chat.id

    # RPS
    if game_name == "حجر ورق مقص":

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🪨 حجر",
                        callback_data=(
                            f"rps:{chat_id}:حجر"
                        ),
                    ),
                    InlineKeyboardButton(
                        "📄 ورق",
                        callback_data=(
                            f"rps:{chat_id}:ورق"
                        ),
                    ),
                    InlineKeyboardButton(
                        "✂️ مقص",
                        callback_data=(
                            f"rps:{chat_id}:مقص"
                        ),
                    ),
                ]
            ]
        )

        await message.reply_text(
            "🎮 حجر ورق مقص\n\n"
            "اختار:",
            reply_markup=keyboard,
        )

        return

    # NUMBER
    if game_name in {
        "تخمين الرقم",
        "خمن الرقم",
        "رقم الحظ",
    }:

        number = random.randint(
            1,
            20,
        )

        games[chat_id] = {
            "type": "number",
            "answer": number,
        }

        await message.reply_text(
            "🎯 خمن رقم من 1 إلى 20."
        )

        return

    # MATH
    if game_name in {
        "رياضيات سريعة",
        "حساب سريع",
        "جمع سريع",
        "طرح سريع",
        "ضرب سريع",
        "قسمة سريعة",
    }:

        a = random.randint(
            1,
            30,
        )

        b = random.randint(
            1,
            20,
        )

        if game_name == "طرح سريع":

            answer = a - b
            question = f"{a} - {b}"

        elif game_name == "ضرب سريع":

            answer = a * b
            question = f"{a} × {b}"

        elif game_name == "قسمة سريعة":

            b = random.randint(
                1,
                10,
            )

            answer = random.randint(
                1,
                10,
            )

            a = b * answer

            question = f"{a} ÷ {b}"

        else:

            answer = a + b
            question = f"{a} + {b}"

        games[chat_id] = {
            "type": "math",
            "answer": answer,
        }

        await message.reply_text(
            f"🧠 أسرع واحد يجاوب:\n\n"
            f"❓ {question} = ؟"
        )

        return

    # TRUE / FALSE
    if game_name in {
        "صح أو خطأ",
        "نعم أو لا",
        "أسئلة عامة",
    }:

        questions = [
            (
                "القاهرة عاصمة مصر؟",
                "صح",
            ),
            (
                "الشمس نجم؟",
                "صح",
            ),
            (
                "الأرض مسطحة؟",
                "خطأ",
            ),
            (
                "الماء يتجمد عند 0 درجة؟",
                "صح",
            ),
            (
                "أفريقيا دولة؟",
                "خطأ",
            ),
        ]

        question, answer = random.choice(
            questions
        )

        games[chat_id] = {
            "type": "question",
            "answer": answer,
        }

        await message.reply_text(
            f"❓ {question}\n\n"
            "اكتب صح أو خطأ."
        )

        return

    # GENERIC
    challenges = [
        "اكتب اسم حيوان بسرعة.",
        "اكتب اسم دولة.",
        "اكتب اسم لاعب كرة قدم.",
        "اكتب اسم سيارة.",
        "اكتب اسم فيلم.",
        "اكتب اسم لون.",
        "اكتب اسم فاكهة.",
        "اكتب اسم مدينة.",
        "اكتب اسم نادي.",
        "اكتب اسم لاعب.",
    ]

    challenge = random.choice(
        challenges
    )

    games[chat_id] = {
        "type": "generic",
    }

    await message.reply_text(
        f"🎮 **{game_name}**\n\n"
        f"🔥 التحدي:\n{challenge}\n\n"
        "أسرع إجابة تكسب!"
    )


# =========================================================
# TWO PLAYER LOBBY
# =========================================================

async def create_lobby(
    message,
    game_name,
):

    game_id = (
        f"{message.chat.id}:"
        f"{message.id}"
    )

    games[game_id] = {
        "type": "lobby",
        "chat_id": message.chat.id,
        "game": game_name,
        "player1": message.from_user.id,
        "player1_name": (
            message.from_user.first_name
        ),
        "player2": None,
        "player2_name": None,
    }

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🎮 انضم للعبة",
                    callback_data=(
                        f"join:{game_id}"
                    ),
                )
            ]
        ]
    )

    await message.reply_text(
        f"🎮 **{game_name}**\n\n"
        f"👤 اللاعب الأول: "
        f"{message.from_user.first_name}\n\n"
        "👥 اللاعب الثاني يضغط الزر "
        "عشان ينضم.",
        reply_markup=keyboard,
    )


# =========================================================
# GAME NAME HANDLER
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
)
async def game_name_handler(
    client,
    message,
):

    text = message.text.strip()

    ignored = {
        "العاب",
        "ألعاب",
        "الأوامر",
        "الاوامر",
        "مساعدة",
        "مساعده",
        "تشغيل",
        "تخطي",
        "وقف",
        "إيقاف",
        "تفعيل البوت",
        "تعطيل البوت",
        "رتبتي",
        "المالك",
        "المشرفين",
        "ترقية",
        "تنزيل",
        "طرد",
        "حظر",
        "فك حظر",
        "كتم",
        "فك كتم",
        "تحذير",
        "تحذيرات",
        "مسح تحذيرات",
        "تثبيت",
        "إلغاء تثبيت",
    }

    if text in ignored:
        return

    game_name = GAME_LOOKUP.get(
        normalize(text)
    )

    if not game_name:
        return

    if game_name in TWO_PLAYER_GAMES:

        await create_lobby(
            message,
            game_name,
        )

    else:

        await start_game(
            message,
            game_name,
        )


# =========================================================
# JOIN BUTTON
# =========================================================

@bot.on_callback_query(
    filters.regex(r"^join:")
)
async def join_game_callback(
    client,
    query,
):

    game_id = query.data[
        5:
    ]

    game = games.get(
        game_id
    )

    if not game:

        await query.answer(
            "❌ اللعبة انتهت.",
            show_alert=True,
        )

        return

    if (
        query.from_user.id
        == game["player1"]
    ):

        await query.answer(
            "❌ أنت اللاعب الأول.",
            show_alert=True,
        )

        return

    if game["player2"]:

        await query.answer(
            "❌ اللعبة اكتملت.",
            show_alert=True,
        )

        return

    game["player2"] = (
        query.from_user.id
    )

    game["player2_name"] = (
        query.from_user.first_name
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "▶️ ابدأ اللعب",
                    callback_data=(
                        f"startgame:{game_id}"
                    ),
                )
            ]
        ]
    )

    await query.message.edit_text(
        f"🎮 **{game['game']}**\n\n"
        f"👤 {game['player1_name']}\n"
        f"👤 {game['player2_name']}\n\n"
        "✅ اللاعبان انضموا.\n"
        "اضغطوا زر ابدأ اللعب.",
        reply_markup=keyboard,
    )

    await query.answer(
        "✅ انضممت للعبة."
    )


# =========================================================
# START GAME BUTTON
# =========================================================

@bot.on_callback_query(
    filters.regex(r"^startgame:")
)
async def start_game_callback(
    client,
    query,
):

    game_id = query.data[
        10:
    ]

    game = games.get(
        game_id
    )

    if not game:

        await query.answer(
            "❌ اللعبة انتهت.",
            show_alert=True,
        )

        return

    user_id = query.from_user.id

    if user_id not in {
        game["player1"],
        game["player2"],
    }:

        await query.answer(
            "❌ أنت مش من اللاعبين.",
            show_alert=True,
        )

        return

    if not game["player2"]:

        await query.answer(
            "❌ لسه محتاج لاعب ثاني.",
            show_alert=True,
        )

        return

    # XO
    if game["game"] == "إكس أو":

        game["type"] = "xo"
        game["board"] = [
            "⬜",
            "⬜",
            "⬜",
            "⬜",
            "⬜",
            "⬜",
            "⬜",
            "⬜",
            "⬜",
        ]

        game["turn"] = game["player1"]

        await show_xo(
            query.message,
            game_id,
        )

    # RPS
    elif game["game"] == "حجر ورق مقص":

        game["type"] = "rps"
        game["choices"] = {}

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🪨 حجر",
                        callback_data=(
                            f"rps2:{game_id}:حجر"
                        ),
                    ),
                    InlineKeyboardButton(
                        "📄 ورق",
                        callback_data=(
                            f"rps2:{game_id}:ورق"
                        ),
                    ),
                    InlineKeyboardButton(
                        "✂️ مقص",
                        callback_data=(
                            f"rps2:{game_id}:مقص"
                        ),
                    ),
                ]
            ]
        )

        await query.message.edit_text(
            "🎮 **حجر ورق مقص**\n\n"
            "كل لاعب يختار مرة واحدة.",
            reply_markup=keyboard,
        )

    else:

        game["type"] = "two_generic"

        await query.message.edit_text(
            f"🎮 **{game['game']}**\n\n"
            f"👤 {game['player1_name']}\n"
            f"👤 {game['player2_name']}\n\n"
            "🔥 بدأت اللعبة!\n"
            "أول لاعب يجاوب يفوز."
        )

    await query.answer()


# =========================================================
# XO
# =========================================================

def xo_keyboard(game_id, board):

    rows = []

    for row in range(3):

        buttons = []

        for col in range(3):

            index = row * 3 + col

            buttons.append(
                InlineKeyboardButton(
                    board[index],
                    callback_data=(
                        f"xo:{game_id}:{index}"
                    ),
                )
            )

        rows.append(buttons)

    return InlineKeyboardMarkup(
        rows
    )


def check_xo(board):

    wins = [
        (0, 1, 2),
        (3, 4, 5),
        (6, 7, 8),
        (0, 3, 6),
        (1, 4, 7),
        (2, 5, 8),
        (0, 4, 8),
        (2, 4, 6),
    ]

    for a, b, c in wins:

        if (
            board[a] != "⬜"
            and board[a]
            == board[b]
            == board[c]
        ):
            return board[a]

    if "⬜" not in board:
        return "draw"

    return None


async def show_xo(
    message,
    game_id,
):

    game = games.get(
        game_id
    )

    if not game:
        return

    if (
        game["turn"]
        == game["player1"]
    ):

        turn_name = (
            game["player1_name"]
        )

    else:

        turn_name = (
            game["player2_name"]
        )

    await message.edit_text(
        "❌⭕ **إكس أو**\n\n"
        f"🎯 الدور على: {turn_name}",
        reply_markup=xo_keyboard(
            game_id,
            game["board"],
        ),
    )


@bot.on_callback_query(
    filters.regex(r"^xo:")
)
async def xo_callback(
    client,
    query,
):

    parts = query.data.split(":")

    game_id = parts[1]
    index = int(parts[2])

    game = games.get(
        game_id
    )

    if not game:

        await query.answer(
            "❌ اللعبة انتهت.",
            show_alert=True,
        )

        return

    if (
        query.from_user.id
        != game["turn"]
    ):

        await query.answer(
            "❌ مش دورك.",
            show_alert=True,
        )

        return

    if game["board"][index] != "⬜":

        await query.answer(
            "❌ المكان مستخدم.",
            show_alert=True,
        )

        return

    if (
        query.from_user.id
        == game["player1"]
    ):

        symbol = "❌"
        next_player = game["player2"]

    else:

        symbol = "⭕"
        next_player = game["player1"]

    game["board"][index] = symbol

    result = check_xo(
        game["board"]
    )

    if result:

        if result == "draw":

            result_text = "🤝 تعادل!"

        elif result == "❌":

            result_text = (
                f"🏆 الفائز: "
                f"{game['player1_name']}"
            )

        else:

            result_text = (
                f"🏆 الفائز: "
                f"{game['player2_name']}"
            )

        await query.message.edit_text(
            "❌⭕ **انتهت إكس أو**\n\n"
            f"{result_text}"
        )

        games.pop(
            game_id,
            None,
        )

    else:

        game["turn"] = next_player

        await show_xo(
            query.message,
            game_id,
        )

    await query.answer()


# =========================================================
# RPS TWO PLAYERS
# =========================================================

@bot.on_callback_query(
    filters.regex(r"^rps2:")
)
async def rps_two_callback(
    client,
    query,
):

    parts = query.data.split(":")

    game_id = parts[1]
    choice = parts[2]

    game = games.get(
        game_id
    )

    if not game:

        await query.answer(
            "❌ اللعبة انتهت.",
            show_alert=True,
        )

        return

    user_id = query.from_user.id

    if user_id not in {
        game["player1"],
        game["player2"],
    }:

        await query.answer(
            "❌ أنت مش لاعب.",
            show_alert=True,
        )

        return

    if user_id in game["choices"]:

        await query.answer(
            "❌ اخترت بالفعل.",
            show_alert=True,
        )

        return

    game["choices"][user_id] = choice

    await query.answer(
        "✅ تم تسجيل اختيارك."
    )

    if len(
        game["choices"]
    ) < 2:

        await query.message.edit_text(
            "🎮 حجر ورق مقص\n\n"
            "✅ لاعب اختار.\n"
            "⏳ في انتظار اللاعب الثاني..."
        )

        return

    p1 = game["choices"][
        game["player1"]
    ]

    p2 = game["choices"][
        game["player2"]
    ]

    if p1 == p2:

        result = "🤝 تعادل!"

    elif (
        (
            p1 == "حجر"
            and p2 == "مقص"
        )
        or (
            p1 == "ورق"
            and p2 == "حجر"
        )
        or (
            p1 == "مقص"
            and p2 == "ورق"
        )
    ):

        result = (
            f"🏆 الفائز: "
            f"{game['player1_name']}"
        )

    else:

        result = (
            f"🏆 الفائز: "
            f"{game['player2_name']}"
        )

    await query.message.edit_text(
        f"🎮 **حجر ورق مقص**\n\n"
        f"👤 {game['player1_name']}: {p1}\n"
        f"👤 {game['player2_name']}: {p2}\n\n"
        f"{result}"
    )

    games.pop(
        game_id,
        None,
    )


# =========================================================
# SINGLE GAME ANSWERS
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
)
async def game_answer_handler(
    client,
    message,
):

    chat_id = message.chat.id

    game = games.get(
        chat_id
    )

    if not game:
        return

    # Ignore commands
    if message.text in {
        "العاب",
        "ألعاب",
        "الأوامر",
        "الاوامر",
    }:
        return

    game_type = game.get(
        "type"
    )

    if game_type == "number":

        try:
            value = int(
                message.text.strip()
            )
        except Exception:
            return

        answer = game["answer"]

        if value == answer:

            await message.reply_text(
                f"🏆 صح!\n"
                f"الرقم كان: {answer}\n"
                f"الفائز: "
                f"{message.from_user.first_name}"
            )

            games.pop(
                chat_id,
                None,
            )

        elif value < answer:

            await message.reply_text(
                "⬆️ أعلى!"
            )

        else:

            await message.reply_text(
                "⬇️ أقل!"
            )

    elif game_type == "math":

        try:
            value = int(
                message.text.strip()
            )
        except Exception:
            return

        if value == game["answer"]:

            await message.reply_text(
                "🏆 إجابة صحيحة!\n"
                f"الفائز: "
                f"{message.from_user.first_name}"
            )

            games.pop(
                chat_id,
                None,
            )

    elif game_type == "question":

        answer = normalize(
            message.text
        )

        if answer == normalize(
            game["answer"]
        ):

            await message.reply_text(
                "🏆 إجابة صحيحة!\n"
                f"الفائز: "
                f"{message.from_user.first_name}"
            )

            games.pop(
                chat_id,
                None,
            )

    elif game_type == "generic":

        await message.reply_text(
            f"🏆 أول إجابة!\n"
            f"الفائز: "
            f"{message.from_user.first_name}"
        )

        games.pop(
            chat_id,
            None,
        )


# =========================================================
# MUSIC SEARCH
# =========================================================

async def search_song(name):

    import yt_dlp

    music_dir = Path("music")
    music_dir.mkdir(
        exist_ok=True
    )

    output = str(
        music_dir
        / "%(id)s.%(ext)s"
    )

    options = {
        "format": "bestaudio/best",
        "outtmpl": output,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    sources = [
        f"scsearch1:{name}",
        f"ytsearch1:{name}",
    ]

    for source in sources:

        try:

            with yt_dlp.YoutubeDL(
                options
            ) as ydl:

                info = ydl.extract_info(
                    source,
                    download=True,
                )

                if "entries" in info:

                    entries = info.get(
                        "entries"
                    )

                    if not entries:
                        continue

                    info = entries[0]

                path = ydl.prepare_filename(
                    info
                )

                path = str(
                    Path(path).with_suffix(
                        ".mp3"
                    )
                )

                if Path(path).exists():

                    return {
                        "path": path,
                        "title": info.get(
                            "title",
                            name,
                        ),
                        "duration": info.get(
                            "duration",
                            0,
                        ),
                    }

        except Exception as e:

            print(
                "Music source error:",
                e,
            )

            continue

    return None


# =====
