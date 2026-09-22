import os
import re
import json
import asyncio
from pathlib import Path
from collections import defaultdict, deque

import static_ffmpeg
static_ffmpeg.add_paths()

from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from pyrogram.enums import ChatMemberStatus

from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, GroupCallConfig

import yt_dlp


# =========================================================
# إعدادات البوت
# =========================================================

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
SESSION_STRING = os.environ["SESSION_STRING"]

PHOTO_PATH = "IMG_20260922_130735_050.jpg"

CUSTOM_REPLIES_FILE = "custom_replies.json"
WARNINGS_FILE = "warnings.json"
SETTINGS_FILE = "group_settings.json"

# لو عايز اشتراك إجباري:
# في Railway أضف:
# REQUIRED_CHAT=@اسم_القناة
#
# لو مش عايز اشتراك إجباري اتركه فاضي.
REQUIRED_CHAT = os.getenv("REQUIRED_CHAT", "").strip()


# =========================================================
# تشغيل البوت
# =========================================================

bot = Client(
    "MariamMusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

assistant = Client(
    "MariamAssistant",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
)

calls = PyTgCalls(assistant)


# =========================================================
# بيانات مؤقتة
# =========================================================

queues = defaultdict(deque)
current_tracks = {}
pending_songs = {}


# =========================================================
# ملفات البيانات
# =========================================================

def load_json(filename, default):
    path = Path(filename)

    if not path.exists():
        return default

    try:
        return json.loads(
            path.read_text(encoding="utf-8")
        )
    except Exception:
        return default


def save_json(filename, data):
    Path(filename).write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


custom_replies = load_json(
    CUSTOM_REPLIES_FILE,
    {}
)

warnings_data = load_json(
    WARNINGS_FILE,
    {}
)

settings_data = load_json(
    SETTINGS_FILE,
    {}
)


# =========================================================
# إعدادات الجروبات
# =========================================================

DEFAULT_SETTINGS = {
    "links": False,
    "bad_words": True,
    "spam": True,
    "photos": False,
    "videos": False,
    "stickers": False,
    "voice": False,
}


def get_settings(chat_id):

    key = str(chat_id)

    if key not in settings_data:
        settings_data[key] = DEFAULT_SETTINGS.copy()
        save_json(
            SETTINGS_FILE,
            settings_data
        )

    return settings_data[key]


# =========================================================
# كلمات ممنوعة
# =========================================================

BAD_WORDS = {
    "كلمة_ممنوعة",
    "كلمة_ممنوعة2",
    "كلمة_ممنوعة3",
}


# =========================================================
# رسائل الترحيب
# =========================================================

WELCOME_MESSAGES = [
    "👋 أهلاً وسهلاً {name} ❤️ نورت الجروب!",
    "🌷 يا مرحباً بـ {name} ❤️",
    "🎉 نورتنا يا {name}!",
    "💕 أهلاً يا {name}، نورت المكان!",
]


# =========================================================
# أدوات مساعدة
# =========================================================

def normalize(text):

    return " ".join(
        (text or "").strip().lower().split()
    )


def mention_user(user):

    if not user:
        return "المستخدم"

    return user.mention


async def is_admin(message, user_id=None):

    if message.chat.type == "private":
        return True

    if user_id is None:

        if not message.from_user:
            return False

        user_id = message.from_user.id

    try:

        member = await bot.get_chat_member(
            message.chat.id,
            user_id
        )

        return member.status in (
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        )

    except Exception:

        return False


async def is_owner(message, user_id=None):

    if user_id is None:

        if not message.from_user:
            return False

        user_id = message.from_user.id

    try:

        member = await bot.get_chat_member(
            message.chat.id,
            user_id
        )

        return member.status == ChatMemberStatus.OWNER

    except Exception:

        return False


async def bot_is_admin(message):

    try:

        member = await bot.get_chat_member(
            message.chat.id,
            "me"
        )

        return member.status in (
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        )

    except Exception:

        return False


async def target_user(message):

    if message.reply_to_message:

        return message.reply_to_message.from_user

    return None


# =========================================================
# التحقق
# =========================================================

async def is_user_joined(user_id):

    if not REQUIRED_CHAT:
        return True

    try:

        member = await bot.get_chat_member(
            REQUIRED_CHAT,
            user_id
        )

        return member.status not in (
            ChatMemberStatus.LEFT,
            ChatMemberStatus.BANNED,
        )

    except Exception:

        return False


def verification_keyboard():

    buttons = []

    if REQUIRED_CHAT:

        username = REQUIRED_CHAT.replace(
            "@",
            ""
        )

        buttons.append([
            InlineKeyboardButton(
                "📢 انضم للمجموعة",
                url=f"https://t.me/{username}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "✅ تحقق",
            callback_data="verify"
        )
    ])

    return InlineKeyboardMarkup(buttons)


async def send_verification(message):

    await message.reply_text(
        "🔐 **لاستخدام البوت لازم تعمل تحقق أولاً.**\n\n"
        "اضغط على زر الانضمام ثم اضغط «✅ تحقق».",
        reply_markup=verification_keyboard()
    )


@bot.on_callback_query(
    filters.regex("^verify$")
)
async def verify_callback(client, query):

    if await is_user_joined(
        query.from_user.id
    ):

        await query.answer(
            "✅ تم التحقق!",
            show_alert=True
        )

        try:

            await query.message.edit_text(
                "✅ تم التحقق بنجاح.\n\n"
                "تقدر الآن استخدام البوت."
            )

        except Exception:
            pass

    else:

        await query.answer(
            "❌ لم تنضم بعد.",
            show_alert=True
        )


# =========================================================
# /start
# =========================================================

@bot.on_message(
    filters.private & filters.command("start")
)
async def start_handler(client, message):

    if not await is_user_joined(
        message.from_user.id
    ):

        return await send_verification(
            message
        )

    await message.reply_text(
        "🎵 **مريومه الدلوعه** ❤️\n\n"
        "أهلاً بيك!\n\n"
        "🎶 `تشغيل`\n"
        "🎶 `تشغيل اسم الأغنية`\n"
        "⏭ `تخطي`\n"
        "⏹ `وقف`\n"
        "📜 `القائمة`"
    )


# =========================================================
# ترحيب الأعضاء
# =========================================================

@bot.on_message(
    filters.group & filters.new_chat_members
)
async def welcome_handler(client, message):

    for member in message.new_chat_members:

        if member.is_bot:
            continue

        name = member.first_name or "يا جميل"

        text = WELCOME_MESSAGES[
            hash(str(member.id)) %
            len(WELCOME_MESSAGES)
        ]

        text = text.replace(
            "{name}",
            name
        )

        await message.reply_text(
            text
        )


# =========================================================
# الردود الجاهزة
# =========================================================

BUILTIN_REPLIES = {

    "السلام عليكم":
        "وعليكم السلام ورحمة الله وبركاته ❤️",

    "سلام عليكم":
        "وعليكم السلام يا جميل ❤️",

    "صباح الخير":
        "صباح النور ☀️❤️",

    "مساء الخير":
        "مساء النور 🌙❤️",

    "ازيك":
        "الحمد لله تمام ❤️ وإنت؟",

    "إزيك":
        "الحمد لله تمام ❤️ وإنت؟",

    "اخبارك":
        "تمام الحمد لله ❤️",

    "أخبارك":
        "تمام يا جميل ❤️",

    "شكرا":
        "العفو ❤️",

    "شكراً":
        "العفو يا جميل ❤️",

    "ميرسي":
        "العفو ❤️",

    "بحبك":
        "وأنا بحب الروح الحلوة دي 😂❤️",

    "هههه":
        "😂😂",

    "ههههه":
        "😂😂😂",

    "منور":
        "ده نورك ❤️",

    "منورة":
        "ده نورك يا قمر ❤️",

    "نورت":
        "ده نورك ❤️",

    "نورتي":
        "ده نورك يا قمر ❤️",

    "عاش":
        "عاش يا نجم 🔥",

    "برافو":
        "برافو عليك 👏❤️",

    "كفو":
        "كفو يا بطل ❤️",

    "أحسنت":
        "تسلم ❤️",

    "شاطر":
        "تسلم يا بطل 😎",

    "شطورة":
        "تسلمي يا قمر ❤️",

    "يا معلم":
        "أؤمر يا معلم 😎",

    "يا ملك":
        "تحت أمرك يا ملك 👑",

    "يا ملكة":
        "تحت أمرك يا ملكة 👑",
}


# =========================================================
# إضافة رد
# =========================================================

async def add_reply(message):

    if not await is_admin(message):
        return await message.reply_text(
            "❌ الأمر ده للأدمن فقط."
        )

    text = message.text.strip()

    raw = text[len("أضف رد "):].strip()

    if "=" not in raw:

        return await message.reply_text(
            "❌ الاستخدام الصحيح:\n\n"
            "`أضف رد الكلمة = الرد`"
        )

    trigger, reply = raw.split(
        "=",
        1
    )

    trigger = normalize(trigger)
    reply = reply.strip()

    if not trigger or not reply:

        return await message.reply_text(
            "❌ اكتب الكلمة والرد."
        )

    key = str(message.chat.id)

    custom_replies.setdefault(
        key,
        {}
    )

    if (
        trigger not in custom_replies[key]
        and len(custom_replies[key]) >= 500
    ):

        return await message.reply_text(
            "❌ وصلت للحد الأقصى وهو 500 رد."
        )

    custom_replies[key][trigger] = reply

    save_json(
        CUSTOM_REPLIES_FILE,
        custom_replies
    )

    await message.reply_text(
        "✅ تم إضافة الرد بنجاح."
    )


# =========================================================
# الرتب
# =========================================================

@bot.on_message(
    filters.group & filters.command(
        ["ترقية", "تنزيل", "رتبتي", "المشرفين"],
        prefixes=""
    )
)
async def ranks_handler(client, message):

    command = normalize(
        message.text
    )

    # -----------------------------
    # رتبتي
    # -----------------------------

    if command == "رتبتي":

        member = await bot.get_chat_member(
            message.chat.id,
            message.from_user.id
        )

        if member.status == ChatMemberStatus.OWNER:

            rank = "👑 مالك الجروب"

        elif member.status == ChatMemberStatus.ADMINISTRATOR:

            rank = "🛡️ مشرف"

        else:

            rank = "👤 عضو"

        return await message.reply_text(
            f"رتبتك: **{rank}**"
        )

    # -----------------------------
    # المشرفين
    # -----------------------------

    if command == "المشرفين":

        admins = []

        async for member in bot.get_chat_members(
            message.chat.id,
            filter="administrators"
        ):

            if member.user:

                admins.append(
                    f"• {member.user.mention}"
                )

        if not admins:

            return await message.reply_text(
                "❌ لم أجد مشرفين."
            )

        return await message.reply_text(
            "👑 **مشرفين الجروب:**\n\n"
            + "\n".join(admins)
        )

    # -----------------------------
    # ترقية
    # -----------------------------

    if command.startswith("ترقية"):

        if not await is_owner(message):

            return await message.reply_text(
                "❌ الترقية للمالك فقط."
            )

        target = await target_user(
            message
        )

        if not target:

            return await message.reply_text(
                "❌ اعمل Reply على الشخص واكتب `ترقية`."
            )

        try:

            await bot.promote_chat_member(
                message.chat.id,
                target.id,
                can_manage_chat=True,
                can_delete_messages=True,
                can_manage_video_chats=True,
                can_restrict_members=True,
                can_promote_members=False,
                can_change_info=False,
                can_invite_users=True,
                can_pin_messages=True,
            )

            return await message.reply_text(
                f"👑 تم ترقية {target.mention} إلى مشرف."
            )

        except Exception as e:

            return await message.reply_text(
                "❌ فشلت الترقية.\n"
                "تأكد أن البوت مشرف وعنده صلاحية إضافة مشرفين."
            )

    # -----------------------------
    # تنزيل
    # -----------------------------

    if command.startswith("تنزيل"):

        if not await is_owner(message):

            return await message.reply_text(
                "❌ التنزيل للمالك فقط."
            )

        target = await target_user(
            message
        )

        if not target:

            return await message.reply_text(
                "❌ اعمل Reply على الشخص واكتب `تنزيل`."
            )

        try:

            await bot.promote_chat_member(
                message.chat.id,
                target.id,
                is_anonymous=False,
                can_manage_chat=False,
                can_delete_messages=False,
                can_manage_video_chats=False,
                can_restrict_members=False,
                can_promote_members=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False,
            )

            return await message.reply_text(
                f"⬇️ تم تنزيل {target.mention}."
            )

        except Exception:

            return await message.reply_text(
                "❌ فشل تنزيل المشرف."
            )


# =========================================================
# الإدارة: طرد / حظر / فك حظر / كتم
# =========================================================

@bot.on_message(
    filters.group & filters.text
)
async def moderation_commands(client, message):

    text = normalize(
        message.text
    )

    # ---------------------------------
    # طرد
    # ---------------------------------

    if text == "طرد":

        if not await is_admin(message):

            return await message.reply_text(
                "❌ للأدمن فقط."
            )

        target = await target_user(
            message
        )

        if not target:

            return await message.reply_text(
                "❌ اعمل Reply على الشخص."
            )

        if target.id == message.from_user.id:

            return

        try:

            await bot.ban_chat_member(
                message.chat.id,
                target.id
            )

            await bot.unban_chat_member(
                message.chat.id,
                target.id
            )

            return await message.reply_text(
                f"🚪 تم طرد {target.mention}."
            )

        except Exception:

            return await message.reply_text(
                "❌ فشل الطرد."
            )

    # ---------------------------------
    # حظر
    # ---------------------------------

    if text == "حظر":

        if not await is_admin(message):

            return await message.reply_text(
                "❌ للأدمن فقط."
            )

        target = await target_user(
            message
        )

        if not target:

            return await message.reply_text(
                "❌ اعمل Reply على الشخص."
            )

        try:

            await bot.ban_chat_member(
                message.chat.id,
                target.id
            )

            return await message.reply_text(
                f"🔨 تم حظر {target.mention}."
            )

        except Exception:

            return await message.reply_text(
                "❌ فشل الحظر."
            )

    # ---------------------------------
    # فك حظر
    # ---------------------------------

    if text == "فك حظر":

        if not await is_admin(message):

            return await message.reply_text(
                "❌ للأدمن فقط."
            )

        target = await target_user(
            message
        )

        if not target:

            return await message.reply_text(
                "❌ اعمل Reply على الشخص."
            )

        try:

            await bot.unban_chat_member(
                message.chat.id,
                target.id
            )

            return await message.reply_text(
                f"✅ تم فك حظر {target.mention}."
            )

        except Exception:

            return await message.reply_text(
                "❌ فشل فك الحظر."
            )

    # ---------------------------------
    # كتم
    # ---------------------------------

    if text == "كتم":

        if not await is_admin(message):

            return await message.reply_text(
                "❌ للأدمن فقط."
            )

        target = await target_user(
            message
        )

        if not target:

            return await message.reply_text(
                "❌ اعمل Reply على الشخص."
            )

        try:

            await bot.restrict_chat_member(
                message.chat.id,
                target.id,
                permissions={
                    "can_send_messages": False
                }
            )

            return await message.reply_text(
                f"🔇 تم كتم {target.mention}."
            )

        except Exception:

            return await message.reply_text(
                "❌ فشل الكتم."
            )

    # ---------------------------------
    # فك كتم
    # ---------------------------------

    if text == "فك كتم":

        if not await is_admin(message):

            return await message.reply_text(
                "❌ للأدمن فقط."
            )

        target = await target_user(
            message
        )

        if not target:

            return await message.reply_text(
                "❌ اعمل Reply على الشخص."
            )

        try:

            await bot.restrict_chat_member(
                message.chat.id,
                target.id,
                permissions={
                    "can_send_messages": True
                }
            )

            return await message.reply_text(
                f"🔊 تم فك كتم {target.mention}."
            )

        except Exception:

            return await message.reply_text(
                "❌ فشل فك الكتم."
            )


# =========================================================
# التحذيرات
# =========================================================

@bot.on_message(
    filters.group & filters.text
)
async def warning_commands(client, message):

    text = normalize(
        message.text
    )

    # -----------------------------
    # تحذير
    # -----------------------------

    if text == "تحذير":

        if not await is_admin(message):

            return await message.reply_text(
                "❌ للأدمن فقط."
            )

        target = await target_user(
            message
        )

        if not target:

            return await message.reply_text(
                "❌ اعمل Reply على الشخص."
            )

        chat = str(message.chat.id)
        user = str(target.id)

        warnings_data.setdefault(
            chat,
            {}
        )

        warnings_data[chat][user] = (
            warnings_data[chat].get(user, 0) + 1
        )

        count = warnings_data[chat][user]

        save_json(
            WARNINGS_FILE,
            warnings_data
        )

        if count >= 3:

            try:

                await bot.restrict_chat_member(
                    message.chat.id,
                    target.id,
                    permissions={
                        "can_send_messages": False
                    }
                )

                return await message.reply_text(
                    f"🔇 {target.mention} وصل إلى 3 تحذيرات وتم كتمه."
                )

            except Exception:
                pass

        return await message.reply_text(
            f"⚠️ تحذير لـ {target.mention}\n"
            f"عدد التحذيرات: {count}/3"
        )

    # -----------------------------
    # تحذيرات
    # -----------------------------

    if text == "تحذيرات":

        target = await target_user(
            message
        )

        if not target:

            target = message.from_user

        chat = str(message.chat.id)
        user = str(target.id)

        count = warnings_data.get(
            chat,
            {}
        ).get(
            user,
            0
        )

        return await message.reply_text(
            f"⚠️ تحذيرات {target.mention}: "
            f"**{count}/3**"
        )

    # -----------------------------
    # مسح تحذيرات
    # -----------------------------

    if text == "مسح تحذيرات":

        if not await is_admin(message):

            return await message.reply_text(
                "❌ للأدمن فقط."
            )

        target = await target_user(
            message
        )

        if not target:

            return await message.reply_text(
                "❌ اعمل Reply على الشخص."
            )

        chat = str(message.chat.id)
        user = str(target.id)

        if chat in warnings_data:

            warnings_data[chat].pop(
                user,
                None
            )

        save_json(
            WARNINGS_FILE,
            warnings_data
        )

        return await message.reply_text(
            f"✅ تم مسح تحذيرات {target.mention}."
        )


# =========================================================
# تثبيت / إلغاء تثبيت
# =========================================================

@bot.on_message(
    filters.group & filters.text
)
async def pin_commands(client, message):

    text = normalize(
        message.text
    )

    if text == "تثبيت":

        if not await is_admin(message):

            return await message.reply_text(
                "❌ للأدمن فقط."
            )

        if not message.reply_to_message:

            return await message.reply_text(
                "❌ اعمل Reply على الرسالة."
            )

        try:

            await message.reply_to_message.pin(
                disable_notification=False
            )

            return await message.reply_text(
                "📌 تم تثبيت الرسالة."
            )

        except Exception:

            return await message.reply_text(
                "❌ فشل التثبيت."
            )

    if text == "الغاء تثبيت" or text == "إلغاء تثبيت":

        if not await is_admin(message):

            return await message.reply_text(
                "❌ للأدمن فقط."
            )

        try:

            await message.reply_to_message.unpin()

            return await message.reply_text(
                "📌 تم إلغاء التثبيت."
            )

        except Exception:

            return await message.reply_text(
                "❌ فشل إلغاء التثبيت."
            )


# =========================================================
# أوامر الحماية
# =========================================================

@bot.on_message(
    filters.group & filters.text
)
async def protection_settings(client, message):

    text = normalize(
        message.text
    )

    if text not in (
        "قفل الروابط",
        "فتح الروابط",
        "قفل الصور",
        "فتح الصور",
        "قفل الفيديو",
        "فتح الفيديو",
        "قفل الملصقات",
        "فتح الملصقات",
        "قفل الصوت",
        "فتح الصوت",
        "قفل السب",
        "فتح السب",
    ):
        return

    if not await is_admin(message):

        return await message.reply_text(
            "❌ للأدمن فقط."
        )

    settings = get_settings(
        message.chat.id
    )

    if text == "قفل الروابط":
        settings["links"] = True

    elif text == "فتح الروابط":
        settings["links"] = False

    elif text == "قفل الصور":
        settings["photos"] = True

    elif text == "فتح الصور":
        settings["photos"] = False

    elif text == "قفل الفيديو":
        settings["videos"] = True

    elif text == "فتح الفيديو":
        settings["videos"] = False

    elif text == "قفل الملصقات":
        settings["stickers"] = True

    elif text == "فتح الملصقات":
        settings["stickers"] = False

    elif text == "قفل الصوت":
        settings["voice"] = True

    elif text == "فتح الصوت":
        settings["voice"] = False

    elif text == "قفل السب":
        settings["bad_words"] = True

    elif text == "فتح السب":
        settings["bad_words"] = False

    save_json(
        SETTINGS_FILE,
        settings_data
    )

    await message.reply_text(
        "✅ تم تغيير إعداد الحماية."
    )


# =========================================================
# حماية الرسائل
# =========================================================

URL_PATTERN = re.compile(
    r"(https?://|www\.|t\.me/|telegram\.me/)",
    re.IGNORECASE
)


@bot.on_message(
    filters.group
)
async def protection_handler(client, message):

    if not message.from_user:
        return

    if await is_admin(message):
        return

    settings = get_settings(
        message.chat.id
    )

    # -----------------------------
    # الروابط
    # -----------------------------

    if settings["links"]:

        text = message.text or message.caption or ""

        if URL_PATTERN.search(text):

            try:
                await message.delete()
            except Exception:
                pass

            return

    # -----------------------------
    # السب
    # -----------------------------

    if settings["bad_words"]:

        text = normalize(
            message.text or message.caption or ""
        )

        for bad in BAD_WORDS:

            if bad and bad in text:

                try:
                    await message.delete()
                except Exception:
                    pass

                return

    # -----------------------------
    # الصور
    # -----------------------------

    if settings["photos"] and message.photo:

        try:
            await message.delete()
        except Exception:
            pass

        return

    # -----------------------------
    # الفيديو
    # -----------------------------

    if settings["videos"] and (
        message.video or
        message.animation
    ):

        try:
            await message.delete()
        except Exception:
            pass

        return

    # -----------------------------
    # الملصقات
    # -----------------------------

    if settings["stickers"] and message.sticker:

        try:
            await message.delete()
        except Exception:
            pass

        return

    # -----------------------------
    # الصوت
    # -----------------------------

    if settings["voice"] and (
        message.voice or
        message.audio
    ):

        try:
            await message.delete()
        except Exception:
            pass

        return


# =========================================================
# البحث عن الأغاني
# =========================================================

async def search_song(query):

    options = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "default_search": "scsearch1",
    }

    def search():

        with yt_dlp.YoutubeDL(
            options
        ) as ydl:

            data = ydl.extract_info(
                f"scsearch1:{query}",
                download=False
            )

            entries = data.get(
                "entries"
            ) or []

            if entries:
                return entries[0]

            return None

    return await asyncio.to_thread(
        search
    )


async def get_audio_url(info):

    url = (
        info.get("webpage_url")
        or info.get("original_url")
        or info.get("url")
    )

    if not url:
        return None

    options = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "noplaylist": True,
    }

    def extract():

        with yt_dlp.YoutubeDL(
            options
        ) as ydl:

            data = ydl.extract_info(
                url,
                download=False
            )

            return data.get("url")

    return await asyncio.to_thread(
        extract
    )


def duration_text(seconds):

    try:

        seconds = int(
            seconds or 0
        )

    except Exception:

        return "غير معروف"

    minutes = seconds // 60
    seconds = seconds % 60

    return f"{minutes}:{seconds:02d}"


# =========================================================
# أزرار الموسيقى
# =========================================================

def music_keyboard():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "⏭ تخطي",
                callback_data="music_skip"
            ),
            InlineKeyboardButton(
                "⏹ وقف",
                callback_data="music_stop"
            )
        ],
        [
            InlineKeyboardButton(
                "📜 القائمة",
                callback_data="music_queue"
            )
        ]
    ])


# =========================================================
# تشغيل الأغنية
# =========================================================

async def start_track(
    chat_id,
    track,
    message
):

    audio_url = await get_audio_url(
        track
    )

    if not audio_url:

        raise RuntimeError(
            "لم أستطع الحصول على رابط الصوت."
        )

    stream = MediaStream(
        audio_url,
        video_flags=MediaStream.Flags.IGNORE
    )

    await calls.play(
        chat_id,
        stream,
        GroupCallConfig(
            auto_start=True
        )
    )

    current_tracks[chat_id] = track

    title = (
        track.get("title")
        or "أغنية"
    )

    duration = duration_text(
        track.get("duration")
    )

    requester = (
        message.from_user.mention
        if message.from_user
        else "غير معروف"
    )

    caption = (
        "🎵 **مريومه الدلوعه**\n\n"
        f"🎶 **الأغنية:** {title}\n"
        f"⏱ **المدة:** {duration}\n"
        f"👤 **الطلب:** {requester}"
    )

    try:

        await message.reply_photo(
            PHOTO_PATH,
            caption=caption,
            reply_markup=music_keyboard()
        )

    except Exception:

        await message.reply_text(
            caption,
            reply_markup=music_keyboard()
        )


async def play_next(
    chat_id,
    message
):

    if not queues[chat_id]:

        current_tracks.pop(
            chat_id,
            None
        )

        return

    track = queues[
        chat_id
    ].popleft()

    try:

        await start_track(
            chat_id,
            track,
            message
        )

    except Exception as error:

        await message.reply_text(
            "❌ حصل خطأ أثناء تشغيل الأغنية:\n"
            f"`{error}`"
        )

        if queues[chat_id]:

            await play_next(
                chat_id,
                message
            )


async def stop_music(chat_id):

    try:

        await calls.leave_call(
            chat_id
        )

    except Exception:
        pass

    queues[chat_id].clear()

    current_tracks.pop(
        chat_id,
        None
    )


# =========================================================
# أوامر الموسيقى
# =========================================================

@bot.on_message(
    filters.group & filters.text
)
async def music_commands(client, message):

    text = message.text.strip()
    low = normalize(text)

    # ----------------------------------
    # تشغيل
    # ----------------------------------

    if low == "تشغيل":

        pending_songs[
            message.chat.id
        ] = message.from_user.id

        return await message.reply_text(
            "🎵 قول اسم الأغنية."
        )

    # ----------------------------------
    # تشغيل اسم الأغنية
    # ----------------------------------

    if low.startswith("تشغيل "):

        query = text[
            len("تشغيل "):
        ].strip()

        if not query:

            return await message.reply_text(
                "🎵 قول اسم الأغنية."
            )

        await message.reply_text(
            "🔎 جاري البحث..."
        )

        try:

            result = await search_song(
                query
            )

        except Exception as error:

            return await message.reply_text(
                "❌ حصل خطأ في البحث:\n"
                f"`{error}`"
            )

        if not result:

            return await message.reply_text(
                "❌ ملقتش الأغنية."
            )

        queues[
            message.chat.id
        ].append(result)

        if message.chat.id in current_tracks:

            return await message.reply_text(
                "✅ اتضافت الأغنية للقائمة."
            )

        return await play_next(
            message.chat.id,
            message
        )

    # ----------------------------------
    # تخطي
    # ----------------------------------

    if low == "تخطي":

        if not await is_admin(message):

            return await message.reply_text(
                "❌ التخطي للأدمن فقط."
            )

        try:

            await calls.leave_call(
                message.chat.id
            )

        except Exception:
            pass

        return await play_next(
            message.chat.id,
            message
        )

    # ----------------------------------
    # وقف
    # ----------------------------------

    if low in (
        "وقف",
        "إيقاف"
    ):

        if not await is_admin(message):

            return await message.reply_text(
                "❌ الأمر ده للأدمن فقط."
            )

        await stop_music(
            message.chat.id
        )

        return await message.reply_text(
            "⏹ تم إيقاف الأغاني."
        )

    # ----------------------------------
    # القائمة
    # ----------------------------------

    if low == "القائمة":

        items = list(
            queues[
                message.chat.id
            ]
        )

        if not items:

            return await message.reply_text(
                "📭 قائمة التشغيل فاضية."
            )

        lines = [
            "📜 **قائمة التشغيل:**\n"
        ]

        for number, item in enumerate(
            items,
            1
        ):

            lines.append(
                f"{number}. "
                f"{item.get('title', 'بدون اسم')}"
            )

        return await message.reply_text(
            "\n".join(lines)
        )


# =========================================================
# متابعة اسم الأغنية بعد "تشغيل"
# =========================================================

@bot.on_message(
    filters.group & filters.text
)
async def pending_song_handler(
    client,
    message
):

    chat_id = message.chat.id

    if chat_id not in pending_songs:
        return

    if message.from_user.id != pending_songs[chat_id]:
        return

    text = message.text.strip()

    if normalize(text) in (
        "تشغيل",
        "تخطي",
        "وقف",
        "إيقاف",
        "القائمة"
    ):
        return

    del pending_songs[chat_id]

    await message.reply_text(
        "🔎 جاري البحث عن الأغنية..."
    )

    try:

        result = await search_song(
            text
        )

    except Exception as error:

        return await message.reply_text(
            "❌ حصل خطأ:\n"
            f"`{error}`"
        )

    if not result:

        return await message.reply_text(
            "❌ ملقتش الأغنية."
        )

    queues[chat_id].append(
        result
    )

    if chat_id in current_tracks:

        return await message.reply_text(
            "✅ الأغنية اتضافت للقائمة."
        )

    await play_next(
        chat_id,
        message
    )


# =========================================================
# أزرار الموسيقى
# =========================================================

@bot.on_callback_query(
    filters.regex("^music_skip$")
)
async def music_skip_callback(
    client,
    query
):

    if not await is_admin(
        query.message
    ):

        return await query.answer(
            "❌ للأدمن فقط.",
            show_alert=True
        )

    await query.answer(
        "⏭ تخطي"
    )

    chat_id = query.message.chat.id

    try:

        await calls.leave_call(
            chat_id
        )

    except Exception:
        pass

    await play_next(
        chat_id,
        query.message
    )


@bot.on_callback_query(
    filters.regex("^music_stop$")
)
async def music_stop_callback(
    client,
    query
):

    if not await is_admin(
        query.message
    ):

        return await query.answer(
            "❌ للأدمن فقط.",
            show_alert=True
        )

    await query.answer(
        "⏹ تم الإيقاف"
    )

    await stop_music(
        query.message.chat.id
    )

    await query.message.reply_text(
        "⏹ تم إيقاف التشغيل."
    )


@bot.on_callback_query(
    filters.regex("^music_queue$")
)
async def music_queue_callback(
    client,
    query
):

    items = list(
        queues[
            query.message.chat.id
        ]
    )

    if not items:

        return await query.answer(
            "📭 القائمة فاضية.",
            show_alert=True
        )

    lines = [
        "📜 **قائمة التشغيل:**"
    ]

    for number, item in enumerate(
        items,
        1
    ):

        lines.append(
            f"{number}. "
            f"{item.get('title', 'بدون اسم')}"
        )

    await query.message.reply_text(
        "\n".join(lines)
    )

    await query.answer()


# =========================================================
# أوامر الردود المخصصة
# =========================================================

@bot.on_message(
    filters.group & filters.text
)
async def custom_reply_commands(
    client,
    message
):

    text = message.text.strip()
    low = normalize(text)

    # إضافة رد
    if low.startswith("أضف رد "):

        return await add_reply(
            message
        )

    # حذف رد
    if low.startswith("حذف رد "):

        if not await is_admin(message):

            return await message.reply_text(
                "❌ للأدمن فقط."
            )

        trigger = normalize(
            text[len("حذف رد "):]
        )

        key = str(
            message.chat.id
        )

        if trigger not in custom_replies.get(
            key,
            {}
        ):

            return await message.reply_text(
                "❌ الرد مش موجود."
            )

        del custom_replies[key][trigger]

        save_json(
            CUSTOM_REPLIES_FILE,
            custom_replies
        )

        return await message.reply_text(
            "✅ تم حذف الرد."
        )

    # عرض الردود
    if low == "الردود":

        key = str(
            message.chat.id
        )

        data = custom_replies.get(
            key,
            {}
        )

        if not data:

            return await message.reply_text(
                "📭 مفيش ردود."
            )

        lines = [
            "📜 **الردود:**"
        ]

        for number, trigger in enumerate(
            data,
            1
        ):

            lines.append(
                f"{number}. `{trigger}`"
            )

        return await message.reply_text(
            "\n".join(lines)
        )

    # عدد الردود
    if low == "عدد الردود":

        key = str(
            message.chat.id
        )

        count = len(
            custom_replies.get(
                key,
                {}
            )
        )

        return await message.reply_text(
            f"📊 عدد الردود: **{count}/500**"
        )

    # مسح الردود
    if low == "مسح الردود":

        if not await is_admin(message):

            return await message.reply_text(
                "❌ للأدمن فقط."
            )

        key = str(
            message.chat.id
        )

        custom_replies[key] = {}

        save_json(
            CUSTOM_REPLIES_FILE,
            custom_replies
        )

        return await message.reply_text(
            "🗑 تم مسح الردود."
        )


# =========================================================
# تشغيل الردود
# =========================================================

@bot.on_message(
    filters.group & filters.text
)
async def replies_handler(
    client,
    message
):

    low = normalize(
        message.text
    )

    key = str(
        message.chat.id
    )

    data = custom_replies.get(
        key,
        {}
    )

    if low in data:

        await message.reply_text(
            data[low]
        )

        return

    if low in BUILTIN_REPLIES:

        await message.reply_text(
            BUILTIN_REPLIES[low]
        )


# =========================================================
# مساعدة
# =========================================================

@bot.on_message(
    filters.group & filters.text
)
async def help_handler(
    client,
    message
):

    if normalize(
        message.text
    ) != "مساعدة":
        return

    text = """
🎵 **أوامر الموسيقى**

`تشغيل`
`تشغيل اسم الأغنية`
`تخطي`
`وقف`
`القائمة`

👑 **أوامر الرتب**

`ترقية` — بالرد على العضو
`تنزيل` — بالرد على المشرف
`رتبتي`
`المشرفين`

🛡️ **الإدارة**

`طرد`
`حظر`
`فك حظر`
`كتم`
`فك كتم`

⚠️ **التحذيرات**

`تحذير`
`تحذيرات`
`مسح تحذيرات`

📌 **التثبيت**

`تثبيت`
`إلغاء تثبيت`

🔒 **الحماية**

`قفل الروابط`
`فتح الروابط`
`قفل الصور`
`فتح الصور`
`قفل الفيديو`
`فتح الفيديو`
`قفل الملصقات`
`فتح الملصقات`
`قفل الصوت`
`فتح الصوت`
`قفل السب`
`فتح السب`

💬 **الردود**

`أضف رد الكلمة = الرد`
`حذف رد الكلمة`
`الردود`
`عدد الردود`
`مسح الردود`
"""

    await message.reply_text(
        text
    )


# =========================================================
# تشغيل البرنامج
# =========================================================

async def main():

    print(
        "Starting assistant..."
    )

    await assistant.start()

    print(
        "Starting voice calls..."
    )

    calls.start()

    print(
        "Starting bot..."
    )

    await bot.start()

    print(
        "MariamMusicBot is running."
    )

    await asyncio.Event().wait()


if __name__ == "__main__":

    asyncio.run(
        main()
    )
