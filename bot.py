# ============================================================
# MariamMusicBot - bot.py
# ============================================================

import os
import re
import json
import asyncio
from pathlib import Path
from collections import defaultdict, deque

import static_ffmpeg
static_ffmpeg.add_paths()

import yt_dlp

from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatPermissions,
    ChatPrivileges,
)
from pyrogram.enums import ChatMembersFilter

from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, GroupCallConfig


# ============================================================
# ENV
# ============================================================

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
SESSION_STRING = os.environ["SESSION_STRING"]

# لو اسم الصورة عندك مختلف غير السطر ده فقط
PHOTO_PATH = "IMG_20260922_130735_050.jpg"

# قناة/مجموعة التحقق
REQUIRED_CHAT = os.getenv(
    "REQUIRED_CHAT",
    "@mariamqueennuriii"
).strip()


# ============================================================
# CLIENTS
# ============================================================

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

calls = PyTgCalls(assistant)

BOT_ME = None


# ============================================================
# FILES
# ============================================================

CUSTOM_REPLIES_FILE = Path("custom_replies.json")
WARNINGS_FILE = Path("warnings.json")
SETTINGS_FILE = Path("group_settings.json")


def load_json(path, default):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass

    return default


def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )
    except Exception as e:
        print(f"JSON SAVE ERROR: {e}")


custom_replies = load_json(CUSTOM_REPLIES_FILE, {})
warnings_data = load_json(WARNINGS_FILE, {})
settings_data = load_json(SETTINGS_FILE, {})


# ============================================================
# GROUP SETTINGS
# ============================================================

DEFAULT_SETTINGS = {
    "links": False,
    "bad_words": False,
    "spam": False,
    "photos": False,
    "videos": False,
    "stickers": False,
    "voice": False,
}


def get_settings(chat_id):
    key = str(chat_id)

    if key not in settings_data:
        settings_data[key] = DEFAULT_SETTINGS.copy()
        save_json(SETTINGS_FILE, settings_data)

    return settings_data[key]


# ============================================================
# WORDS
# ============================================================

# تقدر تزود الكلمات هنا
BAD_WORDS = {
    "كلمة سيئة",
    "شتيمة",
}


# ============================================================
# MUSIC
# ============================================================

music_queues = defaultdict(deque)
current_song = {}
pending_song = {}


# ============================================================
# HELPERS
# ============================================================

def normalize(text):
    if not text:
        return ""

    text = text.lower().strip()
    text = text.replace("أ", "ا")
    text = text.replace("إ", "ا")
    text = text.replace("آ", "ا")
    text = text.replace("ة", "ه")
    text = re.sub(r"\s+", " ", text)

    return text


async def is_admin(chat_id, user_id):
    try:
        member = await bot.get_chat_member(chat_id, user_id)

        status = str(member.status).lower()

        return (
            "administrator" in status
            or "owner" in status
        )

    except Exception:
        return False


async def is_owner(chat_id, user_id):
    try:
        member = await bot.get_chat_member(chat_id, user_id)

        status = str(member.status).lower()

        return "owner" in status

    except Exception:
        return False


async def bot_is_admin(chat_id):
    try:
        if BOT_ME is None:
            return False

        return await is_admin(chat_id, BOT_ME.id)

    except Exception:
        return False


async def get_target_user(message):
    if message.reply_to_message:
        if message.reply_to_message.from_user:
            return message.reply_to_message.from_user

    if message.entities:
        for entity in message.entities:
            if str(entity.type) == "MessageEntityType.MENTION":
                try:
                    username = message.text[
                        entity.offset:
                        entity.offset + entity.length
                    ]

                    username = username.replace("@", "")

                    return await bot.get_users(username)

                except Exception:
                    pass

    parts = message.text.split()

    if len(parts) >= 2:
        target = parts[1]

        if target.startswith("@"):
            try:
                return await bot.get_users(target)
            except Exception:
                pass

        if target.isdigit():
            try:
                return await bot.get_users(int(target))
            except Exception:
                pass

    return None


async def require_admin(message):
    if not message.from_user:
        return False

    if await is_admin(
        message.chat.id,
        message.from_user.id
    ):
        return True

    await message.reply_text(
        "❌ الأمر ده للمشرفين فقط."
    )

    return False


async def require_bot_admin(message):
    if await bot_is_admin(message.chat.id):
        return True

    await message.reply_text(
        "❌ لازم أكون مشرف في المجموعة علشان أنفذ الأمر."
    )

    return False


# ============================================================
# PRIVATE START / VERIFICATION
# ============================================================

@bot.on_message(filters.private & filters.command("start"))
async def start_private(_, message):

    me = await bot.get_me()

    add_url = (
        f"https://t.me/{me.username}"
        f"?startgroup=true"
    )

    buttons = [
        [
            InlineKeyboardButton(
                "➕ أضفني لمجموعتك",
                url=add_url
            )
        ]
    ]

    if REQUIRED_CHAT:
        buttons.append(
            [
                InlineKeyboardButton(
                    "📢 انضم للمجموعة",
                    url=f"https://t.me/{REQUIRED_CHAT.lstrip('@')}"
                )
            ]
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    "✅ تحقق",
                    callback_data="verify_join"
                )
            ]
        )

    await message.reply_text(
        "👋 أهلاً بيك في **مريومه الدلوعه** 🎶\n\n"
        "أنا بوت موسيقى وإدارة للمجموعات.\n\n"
        "➕ ضيفني لمجموعتك وابدأ التشغيل من هناك.",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@bot.on_callback_query(filters.regex("^verify_join$"))
async def verify_join(_, query):

    if not REQUIRED_CHAT:
        await query.answer(
            "التحقق غير مفعل.",
            show_alert=True
        )
        return

    try:
        member = await bot.get_chat_member(
            REQUIRED_CHAT,
            query.from_user.id
        )

        status = str(member.status).lower()

        if (
            "member" in status
            or "administrator" in status
            or "owner" in status
        ):
            await query.message.edit_text(
                "✅ تم التحقق بنجاح.\n\n"
                "تقدر دلوقتي تستخدم البوت في مجموعتك 🎵"
            )

            await query.answer(
                "تم التحقق ✅"
            )

        else:
            await query.answer(
                "❌ لازم تنضم الأول.",
                show_alert=True
            )

    except Exception:
        await query.answer(
            "❌ مش قادر أتحقق. تأكد إنك انضميت.",
            show_alert=True
        )


# ============================================================
# WELCOME
# ============================================================

WELCOME_MESSAGES = [
    "👋 أهلاً وسهلاً بيك {name} ❤️",
    "🌷 نورت المجموعة يا {name}",
    "✨ أهلاً بيك يا {name}، نورتنا.",
    "🎀 منور يا {name} ❤️",
    "💗 أهلاً وسهلاً يا {name}",
]


@bot.on_message(filters.group & filters.new_chat_members)
async def welcome_handler(_, message):

    for user in message.new_chat_members:

        if user.is_bot:
            continue

        text = WELCOME_MESSAGES[
            user.id % len(WELCOME_MESSAGES)
        ].format(
            name=user.mention
        )

        await message.reply_text(text)


# ============================================================
# BUILT-IN AUTO REPLIES
# ============================================================

BUILTIN_REPLIES = {
    "السلام عليكم": "وعليكم السلام ورحمة الله وبركاته ❤️",
    "سلام": "وعليكم السلام ❤️",
    "هاي": "هاي يا جميل 👋",
    "هلا": "هلا والله 🌷",
    "اهلا": "أهلاً وسهلاً ❤️",
    "اهلا بيك": "منورنا يا جميل ✨",
    "صباح الخير": "صباح النور والسرور ☀️",
    "مساء الخير": "مساء النور 🌙",
    "شكرا": "العفو يا حبيبي ❤️",
    "شكراً": "العفو ❤️",
    "بحبك": "وأنا بحبكم كلكم ❤️😂",
    "بوت": "نعم؟ 👀",
    "مريومه": "عيون مريومه ❤️",
    "مريم": "أيوه يا جميل 🌷",
    "فينك": "أنا موجود أهو 😂",
    "عامل ايه": "تمام الحمد لله ❤️",
    "اخبارك": "زي الفل 🌸",
    "هههه": "😂😂😂",
    "😂": "😂❤️",
    "تصبح على خير": "وأنت من أهله 🌙❤️",
    "باي": "باي يا جميل 👋❤️",
}


# ============================================================
# CUSTOM REPLIES
# ============================================================

@bot.on_message(
    filters.group & filters.text & filters.regex(
        r"^أضف رد\s+(.+?)\s*=\s*(.+)$"
    )
)
async def add_custom_reply(_, message):

    if not await require_admin(message):
        return

    match = re.match(
        r"^أضف رد\s+(.+?)\s*=\s*(.+)$",
        message.text,
        re.S
    )

    if not match:
        return

    trigger = normalize(match.group(1))
    reply = match.group(2).strip()

    chat_id = str(message.chat.id)

    if chat_id not in custom_replies:
        custom_replies[chat_id] = {}

    if len(custom_replies[chat_id]) >= 500:
        await message.reply_text(
            "❌ وصلت للحد الأقصى: 500 رد."
        )
        return

    custom_replies[chat_id][trigger] = reply

    save_json(
        CUSTOM_REPLIES_FILE,
        custom_replies
    )

    await message.reply_text(
        f"✅ تم إضافة الرد:\n"
        f"🔹 الكلمة: {trigger}\n"
        f"🔸 الرد: {reply}"
    )


@bot.on_message(
    filters.group & filters.text & filters.regex(
        r"^مسح رد\s+(.+)$"
    )
)
async def delete_custom_reply(_, message):

    if not await require_admin(message):
        return

    trigger = normalize(
        message.text.split(" ", 2)[2]
    )

    chat_id = str(message.chat.id)

    if (
        chat_id in custom_replies
        and trigger in custom_replies[chat_id]
    ):
        del custom_replies[chat_id][trigger]

        save_json(
            CUSTOM_REPLIES_FILE,
            custom_replies
        )

        await message.reply_text(
            "✅ تم مسح الرد."
        )
    else:
        await message.reply_text(
            "❌ الرد مش موجود."
        )


# ============================================================
# RANKS
# ============================================================

@bot.on_message(
    filters.group & filters.text & filters.regex(
        r"^رتبتي$"
    )
)
async def my_rank(_, message):

    member = await bot.get_chat_member(
        message.chat.id,
        message.from_user.id
    )

    status = str(member.status).lower()

    if "owner" in status:
        rank = "👑 مالك المجموعة"
    elif "administrator" in status:
        rank = "🛡️ مشرف"
    else:
        rank = "👤 عضو"

    await message.reply_text(
        f"🎖️ رتبتك: {rank}"
    )


@bot.on_message(
    filters.group & filters.text & filters.regex(
        r"^المشرفين$"
    )
)
async def admins_list(_, message):

    admins = []

    try:
        async for member in bot.get_chat_members(
            message.chat.id,
            filter=ChatMembersFilter.ADMINISTRATORS
        ):
            if member.user:
                admins.append(
                    f"• {member.user.mention}"
                )

    except Exception as e:
        await message.reply_text(
            f"❌ حصل خطأ: {e}"
        )
        return

    if not admins:
        await message.reply_text(
            "❌ مش قادر أجيب قائمة المشرفين."
        )
        return

    await message.reply_text(
        "👑 مشرفين المجموعة:\n\n"
        + "\n".join(admins)
    )


@bot.on_message(
    filters.group & filters.text & filters.regex(
        r"^ترقية$"
    )
)
async def promote_user(_, message):

    if not await require_admin(message):
        return

    if not await require_bot_admin(message):
        return

    target = await get_target_user(message)

    if not target:
        await message.reply_text(
            "❌ اعمل رد على الشخص واكتب:\n"
            "ترقية"
        )
        return

    try:
        await bot.promote_chat_member(
            message.chat.id,
            target.id,
            privileges=ChatPrivileges(
                can_manage_chat=True,
                can_delete_messages=True,
                can_manage_video_chats=True,
                can_restrict_members=True,
                can_promote_members=False,
                can_change_info=True,
                can_invite_users=True,
                can_pin_messages=True,
            )
        )

        await message.reply_text(
            f"✅ تم ترقية {target.mention} 🛡️"
        )

    except Exception as e:
        await message.reply_text(
            f"❌ مقدرتش أرقي العضو.\n"
            f"`{e}`"
        )


@bot.on_message(
    filters.group & filters.text & filters.regex(
        r"^تنزيل$"
    )
)
async def demote_user(_, message):

    if not await require_admin(message):
        return

    if not await require_bot_admin(message):
        return

    target = await get_target_user(message)

    if not target:
        await message.reply_text(
            "❌ اعمل رد على الشخص واكتب:\n"
            "تنزيل"
        )
        return

    try:
        await bot.promote_chat_member(
            message.chat.id,
            target.id,
            privileges=ChatPrivileges(
                can_manage_chat=False,
                can_delete_messages=False,
                can_manage_video_chats=False,
                can_restrict_members=False,
                can_promote_members=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False,
            )
        )

        await message.reply_text(
            f"✅ تم تنزيل {target.mention} من الإشراف."
        )

    except Exception as e:
        await message.reply_text(
            f"❌ حصل خطأ:\n`{e}`"
        )


# ============================================================
# MODERATION
# ============================================================

@bot.on_message(
    filters.group & filters.text & filters.regex(
        r"^طرد$"
    )
)
async def kick_user(_, message):

    if not await require_admin(message):
        return

    if not await require_bot_admin(message):
        return

    target = await get_target_user(message)

    if not target:
        await message.reply_text(
            "❌ اعمل رد على الشخص واكتب: طرد"
        )
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

        await message.reply_text(
            f"🚪 تم طرد {target.mention}."
        )

    except Exception as e:
        await message.reply_text(
            f"❌ حصل خطأ:\n`{e}`"
        )


@bot.on_message(
    filters.group & filters.text & filters.regex(
        r"^حظر$"
    )
)
async def ban_user(_, message):

    if not await require_admin(message):
        return

    if not await require_bot_admin(message):
        return

    target = await get_target_user(message)

    if not target:
        await message.reply_text(
            "❌ اعمل رد على الشخص واكتب: حظر"
        )
        return

    try:
        await bot.ban_chat_member(
            message.chat.id,
            target.id
        )

        await message.reply_text(
            f"🔨 تم حظر {target.mention}."
        )

    except Exception as e:
        await message.reply_text(
            f"❌ حصل خطأ:\n`{e}`"
        )


@bot.on_message(
    filters.group & filters.text & filters.regex(
        r"^فك حظر$"
    )
)
async def unban_user(_, message):

    if not await require_admin(message):
        return

    if not await require_bot_admin(message):
        return

    target = await get_target_user(message)

    if not target:
        await message.reply_text(
            "❌ اعمل رد على الشخص واكتب: فك حظر"
        )
        return

    try:
        await bot.unban_chat_member(
            message.chat.id,
            target.id
        )

        await message.reply_text(
            f"✅ تم فك حظر {target.mention}."
        )

    except Exception as e:
        await message.reply_text(
            f"❌ حصل خطأ:\n`{e}`"
        )


@bot.on_message(
    filters.group & filters.text & filters.regex(
        r"^كتم$"
    )
)
async def mute_user(_, message):

    if not await require_admin(message):
        return

    if not await require_bot_admin(message):
        return

    target = await get_target_user(message)

    if not target:
        await message.reply_text(
            "❌ اعمل رد على الشخص واكتب: كتم"
        )
        return

    try:
        await bot.restrict_chat_member(
            message.chat.id,
            target.id,
            permissions=ChatPermissions(
                can_send_messages=False
            )
        )

        await message.reply_text(
            f"🔇 تم كتم {target.mention}."
        )

    except Exception as e:
        await message.reply_text(
            f"❌ حصل خطأ:\n`{e}`"
        )


@bot.on_message(
    filters.group & filters.text & filters.regex(
        r"^فك كتم$"
    )
)
async def unmute_user(_, message):

    if not await require_admin(message):
        return

    if not await require_bot_admin(message):
        return

    target = await get_target_user(message)

    if not target:
        await message.reply_text(
            "❌ اعمل رد على الشخص واكتب: فك كتم"
        )
        return

    try:
        await bot.restrict_chat_member(
            message.chat.id,
            target.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            )
        )

        await message.reply_text(
            f"🔊 تم فك كتم {target.mention}."
        )

    except Exception as e:
        await message.reply_text(
            f"❌ حصل خطأ:\n`{e}`"
        )


# ============================================================
# WARNINGS
# ============================================================

@bot.on_message(
    filters.group & filters.text & filters.regex(
        r"^تحذير$"
    )
)
async def warn_user(_, message):

    if not await require_admin(message):
        return

    target = await get_target_user(message)

    if not target:
        await message.reply_text(
            "❌ اعمل رد على الشخص واكتب: تحذير"
        )
        return

    chat_id = str(message.chat.id)
    user_id = str(target.id)

    if chat_id not in warnings_data:
        warnings_data[chat_id] = {}

    warnings_data[chat_id][user_id] = (
        warnings_data[chat_id].get(user_id, 0) + 1
    )

    count = warnings_data[chat_id][user_id]

    save_json(
        WARNINGS_FILE,
        warnings_data
    )

    await message.reply_text(
        f"⚠️ تم تحذير {target.mention}\n"
        f"عدد التحذيرات: {count}/3"
    )

    if count >= 3 and await bot_is_admin(message.chat.id):
        try:
            await bot.ban_chat_member(
                message.chat.id,
                target.id
            )

            await message.reply_text(
                f"🔨 {target.mention} وصل 3 تحذيرات وتم حظره."
            )

        except Exception:
            pass


@bot.on_message(
    filters.group & filters.text & filters.regex(
        r"^تحذيرات$"
    )
)
async def warnings_list(_, message):

    target = await get_target_user(message)

    if not target:
        target = message.from_user

    count = warnings_data.get(
        str(message.chat.id),
        {}
    ).get(
        str(target.id),
        0
    )

    await message.reply_text(
        f"⚠️ تحذيرات {target.mention}: {count}"
    )


@bot.on_message(
    filters.group & filters.text & filters.regex(
        r"^مسح تحذيرات$"
    )
)
async def clear_warnings(_, message):

    if not await require_admin(message):
        return

    target = await get_target_user(message)

    if not target:
        await message.reply_text(
            "❌ اعمل رد على الشخص واكتب: مسح تحذيرات"
        )
        return

    chat_id = str(message.chat.id)

    if chat_id in warnings_data:
        warnings_data[chat_id].pop(
            str(target.id),
            None
        )

    save_json(
        WARNINGS_FILE,
        warnings_data
    )

    await message.reply_text(
        f"✅ تم مسح تحذيرات {target.mention}."
    )


# ============================================================
# PIN
# ============================================================

@bot.on_message(
    filters.group & filters.text & filters.regex(
        r"^تثبيت$"
    )
)
async def pin_message(_, message):

    if not await require_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "❌ اعمل رد على الرسالة اللي عايز تثبتها."
        )
        return

    try:
        await bot.pin_chat_message(
            message.chat.id,
            message.reply_to_message.id,
            disable_notification=True
        )

        await message.reply_text(
            "📌 تم تثبيت الرسالة."
        )

    except Exception as e:
        await message.reply_text(
            f"❌ حصل خطأ:\n`{e}`"
        )


@bot.on_message(
    filters.group & filters.text & filters.regex(
        r"^إلغاء تثبيت$"
    )
)
async def unpin_message(_, message):

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
            f"❌ حصل خطأ:\n`{e}`"
        )


# ============================================================
# LOCKS
# ============================================================

LOCK_MAP = {
    "الروابط": "links",
    "الصور": "photos",
    "الفيديو": "videos",
    "الملصقات": "stickers",
    "الصوت": "voice",
    "السب": "bad_words",
}


@bot.on_message(
    filters.group & filters.text & filters.regex(
        r"^قفل\s+"
    )
)
async def lock_handler(_, message):

    if not await require_admin(message):
        return

    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        await message.reply_text(
            "❌ مثال: قفل الروابط"
        )
        return

    name = parts[1].strip()

    if name not in LOCK_MAP:
        await message.reply_text(
            "❌ الاختيارات:\n"
            "الروابط\n"
            "الصور\n"
            "الفيديو\n"
            "الملصقات\n"
            "الصوت\n"
            "السب"
        )
        return

    settings = get_settings(message.chat.id)
    settings[LOCK_MAP[name]] = True

    save_json(
        SETTINGS_FILE,
        settings_data
    )

    await message.reply_text(
        f"🔒 تم قفل {name}."
    )


@bot.on_message(
    filters.group & filters.text & filters.regex(
        r"^فتح\s+"
    )
)
async def unlock_handler(_, message):

    if not await require_admin(message):
        return

    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        await message.reply_text(
            "❌ مثال: فتح الروابط"
        )
        return

    name = parts[1].strip()

    if name not in LOCK_MAP:
        await message.reply_text(
            "❌ الاختيار غير موجود."
        )
        return

    settings = get_settings(message.chat.id)
    settings[LOCK_MAP[name]] = False

    save_json(
        SETTINGS_FILE,
        settings_data
    )

    await message.reply_text(
        f"🔓 تم فتح {name}."
    )


# ============================================================
# PROTECTION
# ============================================================

@bot.on_message(filters.group)
async def protection_handler(_, message):

    if not message.from_user:
        return

    if await is_admin(
        message.chat.id,
        message.from_user.id
    ):
        return

    settings = get_settings(
        message.chat.id
    )

    # --------------------------------------------------------
    # LINKS
    # --------------------------------------------------------

    if settings.get("links"):
        text = message.text or message.caption or ""

        if re.search(
            r"(https?://|t\.me/|www\.)",
            text,
            re.I
        ):
            try:
                await message.delete()
            except Exception:
                pass

            return

    # --------------------------------------------------------
    # BAD WORDS
    # --------------------------------------------------------

    if settings.get("bad_words"):
        text = normalize(
            message.text or message.caption or ""
        )

        for word in BAD_WORDS:
            if normalize(word) in text:
                try:
                    await message.delete()
                except Exception:
                    pass

                return

    # --------------------------------------------------------
    # PHOTOS
    # --------------------------------------------------------

    if settings.get("photos") and message.photo:
        try:
            await message.delete()
        except Exception:
            pass

        return

    # --------------------------------------------------------
    # VIDEOS
    # --------------------------------------------------------

    if settings.get("videos") and message.video:
        try:
            await message.delete()
        except Exception:
            pass

        return

    # --------------------------------------------------------
    # STICKERS
    # --------------------------------------------------------

    if settings.get("stickers") and message.sticker:
        try:
            await message.delete()
        except Exception:
            pass

        return

    # --------------------------------------------------------
    # VOICE
    # --------------------------------------------------------

    if settings.get("voice") and message.voice:
        try:
            await message.delete()
        except Exception:
            pass

        return


# ============================================================
# MUSIC - SEARCH
# ============================================================

async def search_song(name):

    def search():
        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": False,
            "noplaylist": True,
        }

        with yt_dlp.YoutubeDL(options) as ydl:

            info = ydl.extract_info(
                f"scsearch1:{name}",
                download=False
            )

            if not info:
                return None

            entries = info.get("entries")

            if not entries:
                return None

            entry = entries[0]

            return {
                "title": entry.get(
                    "title",
                    name
                ),
                "url": (
                    entry.get("webpage_url")
                    or entry.get("url")
                ),
                "duration": entry.get(
                    "duration"
                ),
            }

    try:
        return await asyncio.to_thread(search)

    except Exception as e:
        print(
            f"SEARCH ERROR: {e}"
        )
        return None


async def get_stream_url(page_url):

    def extract():

        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "format": "bestaudio/best",
            "noplaylist": True,
        }

        with yt_dlp.YoutubeDL(options) as ydl:

            info = ydl.extract_info(
                page_url,
                download=False
            )

            return {
                "url": info.get("url"),
                "title": info.get("title"),
                "duration": info.get("duration"),
            }

    try:
        return await asyncio.to_thread(
            extract
        )

    except Exception as e:
        print(
            f"STREAM ERROR: {e}"
        )
        return None


def format_duration(seconds):

    if not seconds:
        return "غير معروف"

    seconds = int(seconds)

    minutes = seconds // 60
    seconds = seconds % 60

    return f"{minutes:02d}:{seconds:02d}"


# ============================================================
# MUSIC - NOW PLAYING
# ============================================================

def music_keyboard(chat_id):

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⏭ تخطي",
                    callback_data=f"skip:{chat_id}"
                ),
                InlineKeyboardButton(
                    "⏹ إيقاف",
                    callback_data=f"stop:{chat_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    "📋 القائمة",
                    callback_data=f"queue:{chat_id}"
                )
            ],
        ]
    )


async def send_now_playing(
    chat_id,
    song,
    requester
):

    title = song.get(
        "title",
        "أغنية غير معروفة"
    )

    duration = format_duration(
        song.get("duration")
    )

    requester_text = (
        requester.mention
        if requester
        else "غير معروف"
    )

    caption = (
        "🎶 **مريومه الدلوعه**\n\n"
        f"🎵 **{title}**\n"
        f"⏱ المدة: `{duration}`\n"
        f"👤 طلبها: {requester_text}\n\n"
        "🔊 جاري التشغيل في المكالمة الصوتية..."
    )

    try:
        if os.path.exists(PHOTO_PATH):

            await bot.send_photo(
                chat_id,
                PHOTO_PATH,
                caption=caption,
                reply_markup=music_keyboard(
                    chat_id
                )
            )

        else:

            await bot.send_message(
                chat_id,
                caption,
                reply_markup=music_keyboard(
                    chat_id
                )
            )

    except Exception as e:

        print(
            f"NOW PLAYING ERROR: {e}"
        )

        await bot.send_message(
            chat_id,
            caption,
            reply_markup=music_keyboard(
                chat_id
            )
        )


# ============================================================
# MUSIC - PLAY
# ============================================================

async def play_song(
    chat_id,
    song,
    requester
):

    stream_info = await get_stream_url(
        song["url"]
    )

    if not stream_info:
        await bot.send_message(
            chat_id,
            "❌ مقدرتش أجيب الصوت من المصدر."
        )
        return False

    stream_url = stream_info.get("url")

    if not stream_url:
        await bot.send_message(
            chat_id,
            "❌ رابط الصوت غير متاح."
        )
        return False

    song["stream_url"] = stream_url

    if stream_info.get("duration"):
        song["duration"] = stream_info[
            "duration"
        ]

    try:

        # مهم:
        # play في PyTgCalls الحديثة async
        await calls.play(
            chat_id,
            MediaStream(
                stream_url,
                video_flags=MediaStream.Flags.IGNORE
            ),
            GroupCallConfig(
                auto_start=True
            )
        )

        current_song[chat_id] = song

        await send_now_playing(
            chat_id,
            song,
            requester
        )

        return True

    except Exception as e:

        print(
            f"PLAY ERROR: {e}"
        )

        await bot.send_message(
            chat_id,
            "❌ حصل خطأ أثناء تشغيل الأغنية.\n\n"
            f"`{e}`"
        )

        return False


async def play_next(chat_id):

    if not music_queues[chat_id]:
        current_song.pop(
            chat_id,
            None
        )
        return

    song = music_queues[chat_id].popleft()

    await play_song(
        chat_id,
        song,
        song.get("requester")
    )


# ============================================================
# MUSIC COMMANDS
# ============================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^تشغيل(?:\s+(.+))?$")
)
async def music_play_handler(_, message):

    match = re.match(
        r"^تشغيل(?:\s+(.+))?$",
        message.text.strip()
    )

    if not match:
        return

    name = match.group(1)

    # --------------------------------------------------------
    # تشغيل بدون اسم
    # --------------------------------------------------------

    if not name:

        pending_song[
            message.chat.id
        ] = message.from_user.id

        await message.reply_text(
            "🎵 قول اسم الأغنية اللي عايز تشغلها."
        )

        return

    # --------------------------------------------------------
    # تشغيل اسم الأغنية
    # --------------------------------------------------------

    await message.reply_text(
        f"🔎 بدور على: **{name}**"
    )

    result = await search_song(name)

    if not result:
        await message.reply_text(
            "❌ ملقتش الأغنية."
        )
        return

    song = {
        "title": result["title"],
        "url": result["url"],
        "duration": result.get("duration"),
        "requester": message.from_user,
    }

    chat_id = message.chat.id

    if chat_id in current_song:

        music_queues[chat_id].append(
            song
        )

        position = len(
            music_queues[chat_id]
        )

        await message.reply_text(
            f"✅ اتضافت للقائمة.\n"
            f"🎵 {song['title']}\n"
            f"📋 ترتيبها: {position}"
        )

        return

    await play_song(
        chat_id,
        song,
        message.from_user
    )


# ============================================================
# MUSIC - PENDING SONG NAME
# ============================================================

@bot.on_message(
    filters.group
    & filters.text
    & ~filters.regex(
        r"^(تشغيل|تخطي|وقف|إيقاف|القائمة)$"
    )
)
async def pending_song_handler(_, message):

    chat_id = message.chat.id

    if chat_id not in pending_song:
        return

    user_id = pending_song[chat_id]

    if (
        message.from_user.id
        != user_id
    ):
        return

    del pending_song[chat_id]

    name = message.text.strip()

    if not name:
        return

    await message.reply_text(
        f"🔎 بدور على: **{name}**"
    )

    result = await search_song(name)

    if not result:

        await message.reply_text(
            "❌ ملقتش الأغنية."
        )

        return

    song = {
        "title": result["title"],
        "url": result["url"],
        "duration": result.get("duration"),
        "requester": message.from_user,
    }

    if chat_id in current_song:

        music_queues[chat_id].append(
            song
        )

        await message.reply_text(
            "✅ الأغنية اتضافت للقائمة 🎵\n"
            f"📋 رقمها: {len(music_queues[chat_id])}"
        )

        return

    await play_song(
        chat_id,
        song,
        message.from_user
    )


# ============================================================
# SKIP
# ============================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^تخطي$")
)
async def skip_handler(_, message):

    chat_id = message.chat.id

    if not await require_admin(message):
        return

    try:
        await calls.leave_call(
            chat_id
        )
    except Exception:
        pass

    current_song.pop(
        chat_id,
        None
    )

    if music_queues[chat_id]:

        await message.reply_text(
            "⏭ تم التخطي، بشغل اللي بعدها..."
        )

        await play_next(
            chat_id
        )

    else:

        await message.reply_text(
            "⏭ تم التخطي.\n"
            "📭 مفيش أغاني في القائمة."
        )


# ============================================================
# STOP
# ============================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(
        r"^(وقف|إيقاف)$"
    )
)
async def stop_handler(_, message):

    if not await require_admin(message):
        return

    chat_id = message.chat.id

    try:
        await calls.leave_call(
            chat_id
        )
    except Exception:
        pass

    current_song.pop(
        chat_id,
        None
    )

    music_queues[chat_id].clear()

    await message.reply_text(
        "⏹ تم إيقاف التشغيل ومسح القائمة."
    )


# ============================================================
# QUEUE
# ============================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(
        r"^القائمة$"
    )
)
async def queue_handler(_, message):

    chat_id = message.chat.id

    lines = []

    if chat_id in current_song:

        current = current_song[chat_id]

        lines.append(
            "🎶 التشغيل الآن:\n"
            f"▶️ {current['title']}"
        )

    if music_queues[chat_id]:

        lines.append(
            "\n📋 القائمة:"
        )

        for i, song in enumerate(
            music_queues[chat_id],
            1
        ):
            lines.append(
                f"{i}. {song['title']}"
            )

    if not lines:

        await message.reply_text(
            "📭 القائمة فاضية."
        )

        return

    await message.reply_text(
        "\n".join(lines)
    )


# ============================================================
# MUSIC CALLBACKS
# ============================================================

@bot.on_callback_query(
    filters.regex(
        r"^(skip|stop|queue):(-?\d+)$"
    )
)
async def music_callback(_, query):

    match = re.match(
        r"^(skip|stop|queue):(-?\d+)$",
        query.data
    )

    if not match:
        return

    action = match.group(1)
    chat_id = int(
        match.group(2)
    )

    if query.message.chat.id != chat_id:
        await query.answer(
            "❌ الزر مش تابع للمجموعة دي.",
            show_alert=True
        )
        return

    if not await is_admin(
        chat_id,
        query.from_user.id
    ):
        await query.answer(
            "❌ الزر ده للمشرفين فقط.",
            show_alert=True
        )
        return

    if action == "skip":

        try:
            await calls.leave_call(
                chat_id
            )
        except Exception:
            pass

        current_song.pop(
            chat_id,
            None
        )

        if music_queues[chat_id]:

            await query.answer(
                "⏭ تخطي"
            )

            await play_next(
                chat_id
            )

        else:

            await query.answer(
                "القائمة فاضية.",
                show_alert=True
            )

    elif action == "stop":

        try:
            await calls.leave_call(
                chat_id
            )
        except Exception:
            pass

        current_song.pop(
            chat_id,
            None
        )

        music_queues[chat_id].clear()

        await query.answer(
            "⏹ تم الإيقاف."
        )

    elif action == "queue":

        songs = music_queues[chat_id]

        if not songs:

            await query.answer(
                "📭 القائمة فاضية.",
                show_alert=True
            )

            return

        text = "📋 القائمة:\n\n"

        for i, song in enumerate(
            songs,
            1
        ):
            text += (
                f"{i}. {song['title']}\n"
            )

        await query.answer(
            text[:190],
            show_alert=True
        )


# ============================================================
# HELP
# ============================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(
        r"^مساعدة$|^الاوامر$|^الأوامر$"
    )
)
async def help_handler(_, message):

    text = """
🎀 **أوامر مريومه الدلوعه**

🎵 **الموسيقى**
• تشغيل
• تشغيل اسم الأغنية
• تخطي
• وقف
• إيقاف
• القائمة

👑 **الرتب**
• رتبتي
• المشرفين
• ترقية
• تنزيل

🛡️ **الإدارة**
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
• أضف رد الكلمة = الرد
• مسح رد الكلمة

مثال:
`أضف رد مريم = ❤️ مريومه الدلوعه`
"""

    await message.reply_text(
        text
    )


# ============================================================
# GENERAL AUTO REPLIES
# ============================================================

@bot.on_message(
    filters.group
    & filters.text
)
async def auto_reply_handler(_, message):

    if not message.from_user:
        return

    text = normalize(
        message.text
    )

    # لا تكرر رد أوامر البوت
    command_words = {
        "تشغيل",
        "تخطي",
        "وقف",
        "إيقاف",
        "القائمة",
        "رتبتي",
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
        "مساعدة",
        "الاوامر",
        "الأوامر",
    }

    if text in {
        normalize(x)
        for x in command_words
    }:
        return

    # custom replies
    chat_id = str(
        message.chat.id
    )

    if (
        chat_id in custom_replies
        and text in custom_replies[chat_id]
    ):

        await message.reply_text(
            custom_replies[chat_id][text]
        )

        return

    # built-in
    if text in {
        normalize(x)
        for x in BUILTIN_REPLIES
    }:

        for key, reply in BUILTIN_REPLIES.items():

            if normalize(key) == text:

                await message.reply_text(
                    reply
                )

                return


# ============================================================
# MAIN
# ============================================================

async def main():

    global BOT_ME

    print("Starting assistant...")

    await assistant.start()

    print("Starting voice calls...")

    # ========================================================
    # التصحيح المهم:
    # كان:
    # calls.start()
    #
    # والصحيح:
    # ========================================================

    await calls.start()

    print("Starting bot...")

    await bot.start()

    BOT_ME = await bot.get_me()

    print(
        f"MariamMusicBot is running as @{BOT_ME.username}"
    )

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
