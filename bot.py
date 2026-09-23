import os
import json
import random
import asyncio
import re
from pathlib import Path

import static_ffmpeg
static_ffmpeg.add_paths()

import pyrogram
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
                json.dumps(default, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return default

        return json.loads(path.read_text(encoding="utf-8"))

    except Exception:
        return default


def save_json(path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


custom_replies = load_json(CUSTOM_FILE, {})
group_settings = load_json(SETTINGS_FILE, {})
warnings_data = load_json(WARNINGS_FILE, {})


# =========================================================
# MUSIC
# =========================================================

queues = {}
current_song = {}
waiting_for_song = set()


# =========================================================
# GAMES
# =========================================================

active_games = {}


# =========================================================
# BAD WORDS
# =========================================================

BAD_WORDS = [
    "كلمة_ممنوعة_1",
    "كلمة_ممنوعة_2",
]


# =========================================================
# HELP
# =========================================================

HELP_TEXT = """
🎀 **أوامر مريومه الدلوعه**

🎵 **الميوزك**

• `تشغيل`
• `تشغيل اسم الأغنية`
• `تخطي`
• `وقف`
• `إيقاف`
• `القائمة`

🎮 **الألعاب**

• `العاب`
• `الأوامر`
• قول اسم أي لعبة من القائمة

👑 **الإدارة**

• `تفعيل البوت`
• `تعطيل البوت`
• `رتبتي`
• `المالك`
• `المشرفين`
• `ترقية`
• `تنزيل`
• `طرد`
• `حظر`
• `فك حظر`
• `كتم`
• `فك كتم`

⚠️ **التحذيرات**

• `تحذير`
• `تحذيرات`
• `مسح تحذيرات`

📌 **التثبيت**

• `تثبيت`
• `إلغاء تثبيت`

🔒 **الحماية**

• `قفل الروابط`
• `فتح الروابط`
• `قفل الصور`
• `فتح الصور`
• `قفل الفيديو`
• `فتح الفيديو`
• `قفل الملصقات`
• `فتح الملصقات`
• `قفل الصوت`
• `فتح الصوت`
• `قفل السب`
• `فتح السب`

💬 **الردود**

• `اضف رد الكلمة = الرد`
• `مسح رد الكلمة`

ℹ️ اكتب `العاب` لرؤية قائمة الألعاب.
"""


# =========================================================
# GAME CATALOG
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
    "خمن الرقم",
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


# =========================================================
# TWO PLAYER GAMES
# =========================================================

TWO_PLAYER_GAMES = {
    "إكس أو",
    "حجر ورق مقص",
    "تخمين الرقم",
    "تخمين الحرف",
    "المواجهة",
    "المباراة",
    "النهائي",
    "من يفوز",
    "تحدي شخصين",
    "تحدي الأصدقاء",
    "تحدي ضد البوت",
    "ملك السرعة",
    "ملك الحساب",
    "ملك الحروف",
}


# =========================================================
# NORMALIZE
# =========================================================

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
    normalize(name): name
    for name in GAME_NAMES
}


# =========================================================
# GROUP SETTINGS
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
        save_json(SETTINGS_FILE, group_settings)

    return group_settings[key]


# =========================================================
# ADMIN
# =========================================================

async def is_admin(client, chat_id, user_id):
    try:
        member = await client.get_chat_member(chat_id, user_id)

        status = str(member.status).lower()

        return (
            "administrator" in status
            or "owner" in status
            or "creator" in status
        )

    except Exception:
        return False


async def get_rank(client, chat_id, user_id):
    try:
        member = await client.get_chat_member(chat_id, user_id)

        status = str(member.status).lower()

        if "owner" in status or "creator" in status:
            return "المالك 👑"

        if "administrator" in status or "admin" in status:
            return "مشرف 🛡️"

        if "member" in status:
            return "عضو 👤"

        return "غير معروف"

    except Exception:
        return "غير معروف"


async def require_admin(message):
    if not await is_admin(
        bot,
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

@bot.on_message(filters.command("start", prefixes="/"))
async def start_command(client, message):
    await message.reply_text(
        "🎀 أهلاً بيك في مريومه الدلوعه\n\n"
        "اكتب `الأوامر` لمعرفة كل الأوامر.\n"
        "اكتب `العاب` لرؤية الألعاب."
    )


# =========================================================
# HELP
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^(الأوامر|الاوامر|مساعدة|مساعده)$")
)
async def commands_handler(client, message):
    await message.reply_text(HELP_TEXT)


# =========================================================
# ENABLE / DISABLE
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^(تفعيل البوت|تعطيل البوت)$")
)
async def enable_disable(client, message):

    if not await require_admin(message):
        return

    settings = get_settings(message.chat.id)

    if message.text.strip() == "تفعيل البوت":
        settings["enabled"] = True
        save_json(SETTINGS_FILE, group_settings)

        await message.reply_text(
            "✅ تم تفعيل البوت في المجموعة."
        )

    else:
        settings["enabled"] = False
        save_json(SETTINGS_FILE, group_settings)

        await message.reply_text(
            "⛔ تم تعطيل البوت في المجموعة."
        )


# =========================================================
# RANK
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^رتبتي$")
)
async def my_rank(client, message):

    rank = await get_rank(
        bot,
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
    filters.group &
    filters.text &
    filters.regex(r"^المالك$")
)
async def owner_command(client, message):

    try:
        admins = []

        async for member in bot.get_chat_members(
            message.chat.id,
            filter=pyrogram.enums.ChatMembersFilter.ADMINISTRATORS,
        ):
            status = str(member.status).lower()

            if "owner" in status or "creator" in status:
                admins.append(member)

        if not admins:
            await message.reply_text(
                "❌ لم أستطع معرفة المالك."
            )
            return

        text = "👑 مالك المجموعة:\n\n"

        for member in admins:
            user = member.user

            text += f"• {user.first_name}"

            if user.username:
                text += f" @{user.username}"

            text += "\n"

        await message.reply_text(text)

    except Exception as e:
        await message.reply_text(
            f"❌ حصل خطأ: {e}"
        )


# =========================================================
# ADMINS
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^المشرفين$")
)
async def admins_command(client, message):

    try:
        text = "🛡️ مشرفين المجموعة:\n\n"

        async for member in bot.get_chat_members(
            message.chat.id,
            filter=pyrogram.enums.ChatMembersFilter.ADMINISTRATORS,
        ):
            status = str(member.status).lower()

            if "administrator" in status or "owner" in status:
                user = member.user

                text += f"• {user.first_name}"

                if user.username:
                    text += f" @{user.username}"

                if "owner" in status:
                    text += " 👑"

                else:
                    text += " 🛡️"

                text += "\n"

        await message.reply_text(text)

    except Exception as e:
        await message.reply_text(
            f"❌ حصل خطأ: {e}"
        )


# =========================================================
# PROMOTE
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^ترقية$")
)
async def promote_command(client, message):

    if not await require_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "↩️ اعمل رد على الشخص واكتب: ترقية"
        )
        return

    user_id = message.reply_to_message.from_user.id

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
            "✅ تمت ترقية العضو لمشرف."
        )

    except Exception as e:
        await message.reply_text(
            f"❌ فشلت الترقية:\n{e}"
        )


# =========================================================
# DEMOTE
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^تنزيل$")
)
async def demote_command(client, message):

    if not await require_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "↩️ اعمل رد على المشرف واكتب: تنزيل"
        )
        return

    user_id = message.reply_to_message.from_user.id

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
            "✅ تم تنزيل رتبة المشرف."
        )

    except Exception as e:
        await message.reply_text(
            f"❌ حصل خطأ:\n{e}"
        )


# =========================================================
# KICK
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^طرد$")
)
async def kick_command(client, message):

    if not await require_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "↩️ اعمل رد على العضو واكتب: طرد"
        )
        return

    user_id = message.reply_to_message.from_user.id

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
    filters.group &
    filters.text &
    filters.regex(r"^حظر$")
)
async def ban_command(client, message):

    if not await require_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "↩️ اعمل رد على العضو واكتب: حظر"
        )
        return

    user_id = message.reply_to_message.from_user.id

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
    filters.group &
    filters.text &
    filters.regex(r"^فك حظر$")
)
async def unban_command(client, message):

    if not await require_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "↩️ اعمل رد على العضو واكتب: فك حظر"
        )
        return

    user_id = message.reply_to_message.from_user.id

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
    filters.group &
    filters.text &
    filters.regex(r"^كتم$")
)
async def mute_command(client, message):

    if not await require_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "↩️ اعمل رد على العضو واكتب: كتم"
        )
        return

    user_id = message.reply_to_message.from_user.id

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
    filters.group &
    filters.text &
    filters.regex(r"^فك كتم$")
)
async def unmute_command(client, message):

    if not await require_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "↩️ اعمل رد على العضو واكتب: فك كتم"
        )
        return

    user_id = message.reply_to_message.from_user.id

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
    filters.group &
    filters.text &
    filters.regex(r"^تحذير$")
)
async def warn_command(client, message):

    if not await require_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "↩️ اعمل رد على العضو واكتب: تحذير"
        )
        return

    user = message.reply_to_message.from_user
    chat_id = str(message.chat.id)
    user_id = str(user.id)

    if chat_id not in warnings_data:
        warnings_data[chat_id] = {}

    warnings_data[chat_id][user_id] = (
        warnings_data[chat_id].get(user_id, 0) + 1
    )

    save_json(WARNINGS_FILE, warnings_data)

    count = warnings_data[chat_id][user_id]

    await message.reply_text(
        f"⚠️ تم تحذير {user.first_name}\n"
        f"عدد التحذيرات: {count}"
    )


# =========================================================
# WARNINGS
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^تحذيرات$")
)
async def warnings_command(client, message):

    if not message.reply_to_message:
        await message.reply_text(
            "↩️ اعمل رد على العضو واكتب: تحذيرات"
        )
        return

    user = message.reply_to_message.from_user

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
    filters.group &
    filters.text &
    filters.regex(r"^مسح تحذيرات$")
)
async def clear_warnings(client, message):

    if not await require_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "↩️ اعمل رد على العضو واكتب: مسح تحذيرات"
        )
        return

    user = message.reply_to_message.from_user

    chat_id = str(message.chat.id)
    user_id = str(user.id)

    warnings_data.setdefault(chat_id, {})
    warnings_data[chat_id][user_id] = 0

    save_json(WARNINGS_FILE, warnings_data)

    await message.reply_text(
        "✅ تم مسح التحذيرات."
    )


# =========================================================
# PIN
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^تثبيت$")
)
async def pin_command(client, message):

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
    filters.group &
    filters.text &
    filters.regex(r"^إلغاء تثبيت$")
)
async def unpin_command(client, message):

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
# PROTECTION SETTINGS
# =========================================================

PROTECTION_COMMANDS = {
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


@bot.on_message(filters.group & filters.text)
async def protection_settings(client, message):

    command = message.text.strip()

    if command not in PROTECTION_COMMANDS:
        return

    if not await is_admin(
        bot,
        message.chat.id,
        message.from_user.id,
    ):
        await message.reply_text(
            "❌ الأمر ده للمشرفين فقط."
        )
        return

    setting = PROTECTION_COMMANDS[command]
    settings = get_settings(message.chat.id)

    if command.startswith("قفل"):
        settings[setting] = True
        result = "🔒 تم القفل."

    else:
        settings[setting] = False
        result = "🔓 تم الفتح."

    save_json(SETTINGS_FILE, group_settings)

    await message.reply_text(result)


# =========================================================
# CUSTOM REPLIES
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^اضف رد ")
)
async def add_reply(client, message):

    if not await require_admin(message):
        return

    raw = message.text[7:].strip()

    if "=" not in raw:
        await message.reply_text(
            "❌ استخدم:\n"
            "اضف رد الكلمة = الرد"
        )
        return

    trigger, reply = raw.split("=", 1)

    trigger = trigger.strip()
    reply = reply.strip()

    if not trigger or not reply:
        await message.reply_text(
            "❌ اكتب الكلمة والرد."
        )
        return

    chat_id = str(message.chat.id)

    custom_replies.setdefault(chat_id, {})

    if (
        trigger not in custom_replies[chat_id]
        and len(custom_replies[chat_id]) >= 500
    ):
        await message.reply_text(
            "❌ وصلت المجموعة للحد الأقصى: 500 رد."
        )
        return

    custom_replies[chat_id][trigger] = reply

    save_json(CUSTOM_FILE, custom_replies)

    await message.reply_text(
        f"✅ تم إضافة الرد.\n\n"
        f"الكلمة: {trigger}\n"
        f"الرد: {reply}"
    )


# =========================================================
# DELETE CUSTOM REPLY
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^مسح رد ")
)
async def delete_reply(client, message):

    if not await require_admin(message):
        return

    trigger = message.text[7:].strip()
    chat_id = str(message.chat.id)

    if trigger in custom_replies.get(chat_id, {}):
        del custom_replies[chat_id][trigger]
        save_json(CUSTOM_FILE, custom_replies)

        await message.reply_text(
            "✅ تم مسح الرد."
        )

    else:
        await message.reply_text(
            "❌ الرد مش موجود."
        )


# =========================================================
# CUSTOM REPLY EXECUTION
# =========================================================

@bot.on_message(
    filters.group &
    filters.text
)
async def custom_reply_handler(client, message):

    text = message.text.strip()
    chat_id = str(message.chat.id)

    reply = custom_replies.get(
        chat_id,
        {},
    ).get(text)

    if reply:
        await message.reply_text(reply)


# =========================================================
# GAMES LIST
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^(العاب|ألعاب)$")
)
async def games_list(client, message):

    lines = [
        "🎮 **قائمة الألعاب**",
        "",
        "اكتب اسم أي لعبة عشان تبدأ.",
        "",
    ]

    for i, game in enumerate(GAME_NAMES, 1):
        mode = "👥" if game in TWO_PLAYER_GAMES else "🤖"
        lines.append(
            f"{i}. {mode} {game}"
        )

    text = "\n".join(lines)

    # Telegram message limit protection
    if len(text) <= 4000:
        await message.reply_text(text)
        return

    chunks = []

    current = ""

    for line in lines:
        if len(current) + len(line) + 1 > 3800:
            chunks.append(current)
            current = ""

        current += line + "\n"

    if current:
        chunks.append(current)

    for chunk in chunks:
        await message.reply_text(chunk)


# =========================================================
# GAME START
# =========================================================

async def start_single_game(message, game_name):

    chat_id = message.chat.id

    if game_name == "حجر ورق مقص":
        options = ["🪨 حجر", "📄 ورق", "✂️ مقص"]

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🪨 حجر",
                    callback_data=f"rps:{chat_id}:حجر",
                ),
                InlineKeyboardButton(
                    "📄 ورق",
                    callback_data=f"rps:{chat_id}:ورق",
                ),
                InlineKeyboardButton(
                    "✂️ مقص",
                    callback_data=f"rps:{chat_id}:مقص",
                ),
            ]
        ])

        await message.reply_text(
            "🎮 حجر ورق مقص\n\nاختار:",
            reply_markup=keyboard,
        )
        return

    if game_name in {
        "تخمين الرقم",
        "خمن الرقم",
        "رقم الحظ",
    }:
        number = random.randint(1, 20)

        active_games[chat_id] = {
            "type": "guess_number",
            "number": number,
            "game": game_name,
        }

        await message.reply_text(
            "🎯 خمن رقم من 1 إلى 20\n"
            "اكتب الرقم في الشات."
        )
        return

    if game_name in {
        "رياضيات سريعة",
        "حساب سريع",
        "جمع سريع",
        "طرح سريع",
        "ضرب سريع",
        "قسمة سريعة",
    }:
        a = random.randint(1, 30)
        b = random.randint(1, 20)

        if game_name == "طرح سريع":
            answer = a - b
            question = f"{a} - {b}"

        elif game_name == "ضرب سريع":
            answer = a * b
            question = f"{a} × {b}"

        elif game_name == "قسمة سريعة":
            b = random.randint(1, 10)
            answer = random.randint(1, 10)
            a = b * answer
            question = f"{a} ÷ {b}"

        else:
            answer = a + b
            question = f"{a} + {b}"

        active_games[chat_id] = {
            "type": "math",
            "answer": answer,
            "game": game_name,
        }

        await message.reply_text(
            f"🧠 أسرع واحد يجاوب:\n\n"
            f"❓ {question} = ؟"
        )
        return

    if game_name in {
        "صح أو خطأ",
        "نعم أو لا",
        "أسئلة عامة",
    }:
        questions = [
            ("القاهرة عاصمة مصر؟", "صح"),
            ("الشمس نجم؟", "صح"),
            ("الأرض مسطحة؟", "خطأ"),
            ("الماء يتجمد عند 0 درجة مئوية؟", "صح"),
            ("أفريقيا دولة؟", "خطأ"),
        ]

        question, answer = random.choice(questions)

        active_games[chat_id] = {
            "type": "question",
            "answer": answer,
            "game": game_name,
        }

        await message.reply_text(
            f"❓ {question}\n\n"
            "اكتب: صح أو خطأ"
        )
        return

    # Generic game
    challenges = [
        "اكتب رقم من 1 إلى 10.",
        "اكتب أول حرف من اسمك.",
        "اكتب اسم حيوان بسرعة.",
        "اكتب اسم دولة.",
        "اكتب اسم لاعب كرة قدم.",
        "اكتب اسم سيارة.",
        "اكتب اسم فيلم.",
        "اكتب اسم لون.",
        "اكتب اسم فاكهة.",
        "اكتب اسم مدينة.",
    ]

    challenge = random.choice(challenges)

    active_games[chat_id] = {
        "type": "generic",
        "game": game_name,
    }

    await message.reply_text(
        f"🎮 **{game_name}**\n\n"
        f"🔥 التحدي:\n{challenge}\n\n"
        "أسرع إجابة تكسب!"
    )


# =========================================================
# TWO PLAYER INVITE
# =========================================================

async def create_two_player_game(message, game_name):

    chat_id = message.chat.id
    user = message.from_user

    game_id = f"{chat_id}:{message.id}"

    active_games[game_id] = {
        "type": "two_player_lobby",
        "chat_id": chat_id,
        "game": game_name,
        "player1": user.id,
        "player1_name": user.first_name,
        "player2": None,
        "player2_name": None,
        "started": False,
    }

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🎮 انضم للعبة",
                callback_data=f"gamejoin:{game_id}",
            )
        ]
    ])

    await message.reply_text(
        f"🎮 **{game_name}**\n\n"
        f"👤 اللاعب الأول: {user.first_name}\n\n"
        "اضغط الزر عشان اللاعب الثاني ينضم.",
        reply_markup=keyboard,
    )


# =========================================================
# GAME NAME DETECTOR
# =========================================================

@bot.on_message(
    filters.group &
    filters.text
)
async def game_name_handler(client, message):

    text = message.text.strip()
    normalized = normalize(text)

    # Don't treat bot commands as games
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
    }

    if text in ignored:
        return

    game_name = GAME_LOOKUP.get(normalized)

    if not game_name:
        return

    if game_name in TWO_PLAYER_GAMES:
        await create_two_player_game(
            message,
            game_name,
        )

    else:
        await start_single_game(
            message,
            game_name,
        )


# =========================================================
# GAME JOIN
# =========================================================

@bot.on_callback_query(
    filters.regex(r"^gamejoin:")
)
async def game_join_callback(client, query):

    game_id = query.data.split(":", 1)[1]

    game = active_games.get(game_id)

    if not game:
        await query.answer(
            "❌ اللعبة انتهت.",
            show_alert=True,
        )
        return

    user = query.from_user

    if user.id == game["player1"]:
        await query.answer(
            "❌ أنت اللاعب الأول بالفعل.",
            show_alert=True,
        )
        return

    if game["player2"]:
        await query.answer(
            "❌ اللعبة اكتملت.",
            show_alert=True,
        )
        return

    game["player2"] = user.id
    game["player2_name"] = user.first_name

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "▶️ ابدأ اللعب",
                callback_data=f"gamestart:{game_id}",
            )
        ]
    ])

    await query.message.edit_text(
        f"🎮 **{game['game']}**\n\n"
        f"👤 اللاعب الأول: {game['player1_name']}\n"
        f"👤 اللاعب الثاني: {game['player2_name']}\n\n"
        "✅ اللاعبان انضموا.\n"
        "اضغطوا ابدأ اللعب.",
        reply_markup=keyboard,
    )

    await query.answer(
        "✅ انضممت للعبة!"
    )


# =========================================================
# GAME START BUTTON
# =========================================================

@bot.on_callback_query(
    filters.regex(r"^gamestart:")
)
async def game_start_callback(client, query):

    game_id = query.data.split(":", 1)[1]

    game = active_games.get(game_id)

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
            "❌ أنت مش من لاعبي اللعبة.",
            show_alert=True,
        )
        return

    if not game["player2"]:
        await query.answer(
            "❌ لسه محتاج لاعب ثاني.",
            show_alert=True,
        )
        return

    game["started"] = True

    if game["game"] == "حجر ورق مقص":

        game["choices"] = {}

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🪨 حجر",
                    callback_data=f"rps2:{game_id}:حجر",
                ),
                InlineKeyboardButton(
                    "📄 ورق",
                    callback_data=f"rps2:{game_id}:ورق",
                ),
                InlineKeyboardButton(
                    "✂️ مقص",
                    callback_data=f"rps2:{game_id}:مقص",
                ),
            ]
        ])

        await query.message.edit_text(
            f"🎮 **حجر ورق مقص**\n\n"
            f"👤 {game['player1_name']}\n"
            f"👤 {game['player2_name']}\n\n"
            "كل لاعب يختار.",
            reply_markup=keyboard,
        )

    elif game["game"] == "إكس أو":

        game["board"] = ["⬜"] * 9
        game["turn"] = game["player1"]

        await send_xo_board(
            query.message,
            game_id,
        )

    else:

        await query.message.edit_text(
            f"🎮 **{game['game']}**\n\n"
            f"👤 {game['player1_name']}\n"
            f"👤 {game['player2_name']}\n\n"
            "🔥 التحدي بدأ!\n"
            "أول لاعب يجاوب يفوز."
        )

    await query.answer()


# =========================================================
# XO BOARD
# =========================================================

def xo_keyboard(game_id, board):

    buttons = []

    for row in range(3):
        line = []

        for col in range(3):
            index = row * 3 + col

            line.append(
                InlineKeyboardButton(
                    board[index],
                    callback_data=f"xo:{game_id}:{index}",
                )
            )

        buttons.append(line)

    return InlineKeyboardMarkup(buttons)


async def send_xo_board(message, game_id):

    game = active_games.get(game_id)

    if not game:
        return

    turn_name = (
        game["player1_name"]
        if game["turn"] == game["player1"]
        else game["player2_name"]
    )

    await message.edit_text(
        "❌⭕ **إكس أو**\n\n"
        f"🎯 الدور على: {turn_name}",
        reply_markup=xo_keyboard(
            game_id,
            game["board"],
        ),
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
            and board[a] == board[b] == board[c]
        ):
            return board[a]

    if "⬜" not in board:
        return "draw"

    return None


# =========================================================
# XO CALLBACK
# =========================================================

@bot.on_callback_query(
    filters.regex(r"^xo:")
)
async def xo_callback(client, query):

    _, game_id, index = query.data.split(":")

    game = active_games.get(game_id)

    if not game:
        await query.answer(
            "❌ اللعبة انتهت.",
            show_alert=True,
        )
        return

    user_id = query.from_user.id

    if user_id != game["turn"]:
        await query.answer(
            "❌ مش دورك.",
            show_alert=True,
        )
        return

    index = int(index)

    if game["board"][index] != "⬜":
        await query.answer(
            "❌ المكان مستخدم.",
            show_alert=True,
        )
        return

    if user_id == game["player1"]:
        symbol = "❌"
        next_player = game["player2"]
    else:
        symbol = "⭕"
        next_player = game["player1"]

    game["board"][index] = symbol

    result = check_xo(game["board"])

    if result:

        if result == "draw":
            result_text = "🤝 تعادل!"

        elif result == "❌":
            result_text = (
                f"🏆 الفائز: {game['player1_name']}"
            )

        else:
            result_text = (
                f"🏆 الفائز: {game['player2_name']}"
            )

        await query.message.edit_text(
            f"❌⭕ **إكس أو انتهت**\n\n"
            f"{result_text}"
        )

        active_games.pop(game_id, None)

    else:

        game["turn"] = next_player

        await send_xo_board(
            query.message,
            game_id,
        )

    await query.answer()


# =========================================================
# RPS 2 PLAYERS
# =========================================================

@bot.on_callback_query(
    filters.regex(r"^rps2:")
)
async def rps_two_callback(client, query):

    _, game_id, choice = query.data.split(":")

    game = active_games.get(game_id)

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

    if "choices" not in game:
        game["choices"] = {}

    if user_id in game["choices"]:
        await query.answer(
            "❌ أنت اخترت بالفعل.",
            show_alert=True,
        )
        return

    game["choices"][user_id] = choice

    await query.answer(
        "✅ تم تسجيل اختيارك."
    )

    if len(game["choices"]) < 2:
        await query.message.edit_text(
            "🎮 حجر ورق مقص\n\n"
            "✅ لاعب اختار.\n"
            "⏳ في انتظار اللاعب الثاني..."
        )
        return

    p1 = game["choices"][game["player1"]]
    p2 = game["choices"][game["player2"]]

    winner = None

    if p1 == p2:
        result = "🤝 تعادل!"

    elif (
        (p1 == "حجر" and p2 == "مقص")
        or
        (p1 == "ورق" and p2 == "حجر")
        or
        (p1 == "مقص" and p2 == "ورق")
    ):
        winner = game["player1"]
        result = f"🏆 الفائز: {game['player1_name']}"

    else:
        winner = game["player2"]
        result = f"🏆 الفائز: {game['player2_name']}"

    await query.message.edit_text(
        f"🎮 **حجر ورق مقص**\n\n"
        f"👤 {game['player1_name']}: {p1}\n"
        f"👤 {game['player2_name']}: {p2}\n\n"
        f"{result}"
    )

    active_games.pop(game_id, None)


# =========================================================
# SINGLE GAME ANSWERS
# =========================================================

@bot.on_message(
    filters.group &
    filters.text
)
async def game_answer_handler(client, message):

    chat_id = message.chat.id

    game = active_games.get(chat_id)

    if not game:
        return

    text = message.text.strip()

    if game["type"] == "guess_number":

        try:
            guess = int(text)
        except Exception:
            return

        number = game["number"]

        if guess == number:

            await message.reply_text(
                f"🏆 صح!\n"
                f"الرقم كان: {number}"
            )

            active_games.pop(chat_id, None)

        elif guess < number:

            await message.reply_text(
                "⬆️ أعلى!"
            )

        else:

            await message.reply_text(
                "⬇️ أقل!"
            )

    elif game["type"] == "math":

        try:
            answer = int(text)
        except Exception:
            return

        if answer == game["answer"]:

            await message.reply_text(
                f"🏆 إجابة صحيحة!\n"
                f"الفائز: {message.from_user.first_name}"
            )

            active_games.pop(chat_id, None)

    elif game["type"] == "question":

        answer = normalize(text)

        correct = normalize(game["answer"])

        if answer == correct:

            await message.reply_text(
                f"🏆 إجابة صحيحة!\n"
                f"الفائز: {message.from_user.first_name}"
            )

            active_games.pop(chat_id, None)


# =========================================================
# MUSIC SEARCH
# =========================================================

async def search_and_download(name):

    import yt_dlp

    output_dir = Path("music")
    output_dir.mkdir(exist_ok=True)

    output = str(
        output_dir / "%(id)s.%(ext)s"
    )

    # SoundCloud first
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

            with yt_dlp.YoutubeDL(options) as ydl:

                info = ydl.extract_info(
                    source,
                    download=True,
                )

                if "entries" in info:
                    entries = info.get("entries")

                    if not entries:
                        continue

                    info = entries[0]

                path = ydl.prepare_filename(info)

                path = str(
                    Path(path).with_suffix(".mp3")
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
                        "requester": name,
                    }

        except Exception:
            continue

    return None


# =========================================================
# PLAY SONG
# =========================================================

async def play_song(chat_id, song):

    global calls

    stream = MediaStream(
        song["path"],
        video_flags=MediaStream.Flags.IGNORE,
    )

    await calls.play(
        chat_id,
        stream,
        GroupCallConfig(
            auto_start=True
        ),
    )

    current_song[chat_id] = song

    minutes = int(song["duration"] // 60)
    seconds = int(song["duration"] % 60)

    duration = f"{minutes}:{seconds:02d}"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "⏭️ تخطي",
                callback_data=f"music_skip:{chat_id}",
            ),
            InlineKeyboardButton(
                "⏹️ إيقاف",
                callback_data=f"music_stop:{chat_id}",
            ),
        ]
    ])

    caption = (
        "🎶 **مريومه الدلوعه**\n\n"
        f"🎵 الأغنية: {song['title']}\n"
        f"⏱ المدة: {duration}\n"
        f"👤 الطلب: {song['requester']}\n\n"
        "▶️ يتم التشغيل الآن..."
    )

    try:

        if Path(PHOTO_PATH).exists():

            await bot.send_photo(
                chat_id,
                PHOTO_PATH,
                caption=caption,
                reply_markup=keyboard,
            )

        else:

            await bot.send_message(
                chat_id,
                caption,
                reply_markup=keyboard,
            )

    except Exception:
        await bot.send_message(
            chat_id,
            caption,
            reply_markup=keyboard,
        )


# =========================================================
# PLAY NEXT
# =========================================================

async def play_next(chat_id):

    queue = queues.get(chat_id, [])

    if not queue:
        current_song.pop(chat_id, None)
        return

    song = queue.pop(0)

    await play_song(
        chat_id,
        song,
    )


# =========================================================
# MUSIC COMMANDS
# =========================================================

@bot.on_message(
    filters.group &
    filters.text
)
async def music_commands(client, message):

    global calls

    text = message.text.strip()

    if text.startswith("تشغيل "):

        if not get_settings(
            message.chat.id
        )["enabled"]:
            return

        name = text[7:].strip()

        if not name:
            await message.reply_text(
                "🎵 اكتب اسم الأغنية."
            )
            return

        await message.reply_text(
            f"🔎 بدور على: {name}"
        )

        song = await search_and_download(
            name
        )

        if not song:
            await message.reply_text(
                "❌ مش لاقي الأغنية."
            )
            return

        chat_id = message.chat.id

        song["requester"] = (
            message.from_user.first_name
        )

        if chat_id in current_song:

            queues.setdefault(
                chat_id,
                [],
            ).append(song)

            await message.reply_text(
                f"✅ اتضافت للقائمة:\n"
                f"🎵 {song['title']}"
            )

        else:

            try:
                await play_song(
                    chat_id,
                    song,
                )

            except Exception as e:

                await message.reply_text(
                    f"❌ حصل خطأ في تشغيل الأغنية:\n{e}"
                )

        return

    if text == "تشغيل":

        if not get_settings(
            message.chat.id
        )["enabled"]:
            return

        waiting_for_song.add(
            message.chat.id
        )

        await message.reply_text(
            "🎵 قول اسم الأغنية."
        )

        return

    if text == "القائمة":

        queue = queues.get(
            message.chat.id,
            [],
        )

        if not queue:

            await message.reply_text(
                "📭 القائمة فاضية."
            )

            return

        text_out = "🎵 **قائمة التشغيل:**\n\n"

        for i, song in enumerate(queue, 1):

            text_out += (
                f"{i}. {song['title']}\n"
            )

        await message.reply_text(
            text_out
        )


# =========================================================
# WA
