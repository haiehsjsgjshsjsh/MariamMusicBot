import os
import re
import json
import glob
import asyncio
from pathlib import Path

import static_ffmpeg
static_ffmpeg.add_paths()

import yt_dlp

from pyrogram import Client, filters, idle
from pyrogram.enums import ChatMembersFilter
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatPermissions,
    ChatPrivileges,
)

from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, GroupCallConfig


# =========================================================
# إعدادات
# =========================================================

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
SESSION_STRING = os.environ["SESSION_STRING"]

PHOTO_PATH = "IMG_20260922_130735_050.jpg"

DATA_DIR = Path("data")
DOWNLOAD_DIR = Path("downloads")

DATA_DIR.mkdir(exist_ok=True)
DOWNLOAD_DIR.mkdir(exist_ok=True)


# =========================================================
# Pyrogram clients
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


# =========================================================
# PyTgCalls
# =========================================================

calls = None


# =========================================================
# ملفات البيانات
# =========================================================

CUSTOM_REPLIES_FILE = DATA_DIR / "custom_replies.json"
GROUP_SETTINGS_FILE = DATA_DIR / "group_settings.json"
WARNINGS_FILE = DATA_DIR / "warnings.json"


def load_json(path, default):
    try:
        if not path.exists():
            return default

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception:
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )


custom_replies = load_json(CUSTOM_REPLIES_FILE, {})
group_settings = load_json(GROUP_SETTINGS_FILE, {})
warnings_data = load_json(WARNINGS_FILE, {})


# =========================================================
# إعدادات الميوزك
# =========================================================

music_queues = {}
waiting_for_song = set()
current_songs = {}


# =========================================================
# كلمات ممنوعة
# =========================================================
# ضع الكلمات التي تريد منعها هنا

BAD_WORDS = {
    "كلمة_ممنوعة_1",
    "كلمة_ممنوعة_2",
}


# =========================================================
# إعدادات المجموعة الافتراضية
# =========================================================

DEFAULT_SETTINGS = {
    "enabled": False,
    "links": False,
    "photos": False,
    "videos": False,
    "stickers": False,
    "voice": False,
    "bad_words": False,
}


def get_settings(chat_id):
    key = str(chat_id)

    if key not in group_settings:
        group_settings[key] = DEFAULT_SETTINGS.copy()
        save_json(GROUP_SETTINGS_FILE, group_settings)

    return group_settings[key]


# =========================================================
# استخراج حالة العضو
# =========================================================

async def get_member_status(chat_id, user_id):
    try:
        member = await bot.get_chat_member(
            chat_id,
            user_id,
        )

        status = getattr(member, "status", "")

        value = getattr(
            status,
            "value",
            status,
        )

        return str(value).lower()

    except Exception:
        return ""


# =========================================================
# هل العضو مالك؟
# =========================================================

async def is_owner(message):
    if not message.from_user:
        return False

    status = await get_member_status(
        message.chat.id,
        message.from_user.id,
    )

    return status in {
        "owner",
        "creator",
    }


# =========================================================
# هل العضو مشرف؟
# =========================================================

async def is_admin(message):
    if not message.from_user:
        return False

    status = await get_member_status(
        message.chat.id,
        message.from_user.id,
    )

    return status in {
        "owner",
        "creator",
        "administrator",
        "admin",
    }


# =========================================================
# معرفة المستخدم المستهدف
# =========================================================

async def get_target_user(message):
    if not message.reply_to_message:
        return None

    return message.reply_to_message.from_user


# =========================================================
# تفعيل / تعطيل البوت
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^تفعيل البوت$")
)
async def enable_bot(client, message):

    if not await is_admin(message):
        await message.reply_text(
            "❌ الأمر ده للمشرفين فقط."
        )
        return

    settings = get_settings(message.chat.id)
    settings["enabled"] = True

    save_json(
        GROUP_SETTINGS_FILE,
        group_settings,
    )

    await message.reply_text(
        "✅ تم تفعيل البوت في المجموعة."
    )


@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^تعطيل البوت$")
)
async def disable_bot(client, message):

    if not await is_admin(message):
        await message.reply_text(
            "❌ الأمر ده للمشرفين فقط."
        )
        return

    settings = get_settings(message.chat.id)
    settings["enabled"] = False

    save_json(
        GROUP_SETTINGS_FILE,
        group_settings,
    )

    await message.reply_text(
        "⛔ تم تعطيل البوت في المجموعة."
    )


# =========================================================
# رتبتي
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^رتبتي$")
)
async def my_rank(client, message):

    status = await get_member_status(
        message.chat.id,
        message.from_user.id,
    )

    if status in {"owner", "creator"}:
        rank = "👑 مالك المجموعة"

    elif status in {"administrator", "admin"}:
        rank = "🛡️ مشرف"

    elif status in {"member"}:
        rank = "👤 عضو"

    elif status == "restricted":
        rank = "🔒 عضو مقيّد"

    else:
        rank = "👤 عضو"

    await message.reply_text(
        f"📌 رتبتك:\n\n{rank}"
    )


# =========================================================
# المالك
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^المالك$")
)
async def group_owner(client, message):

    try:
        async for member in bot.get_chat_members(
            message.chat.id,
            filter=ChatMembersFilter.ADMINISTRATORS,
        ):

            status = getattr(
                member,
                "status",
                "",
            )

            value = getattr(
                status,
                "value",
                status,
            )

            value = str(value).lower()

            if value in {
                "owner",
                "creator",
            }:

                user = member.user

                await message.reply_text(
                    f"👑 مالك المجموعة:\n"
                    f"{user.mention}"
                )
                return

        await message.reply_text(
            "❌ مش قادر أحدد مالك المجموعة."
        )

    except Exception as e:

        await message.reply_text(
            "❌ حصل خطأ أثناء معرفة المالك."
        )


# =========================================================
# المشرفين
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^المشرفين$")
)
async def admins_list(client, message):

    try:

        text = "🛡️ مشرفين المجموعة:\n\n"
        count = 0

        async for member in bot.get_chat_members(
            message.chat.id,
            filter=ChatMembersFilter.ADMINISTRATORS,
        ):

            status = getattr(
                member,
                "status",
                "",
            )

            value = getattr(
                status,
                "value",
                status,
            )

            value = str(value).lower()

            if value in {
                "administrator",
                "admin",
            }:

                count += 1

                user = member.user

                text += (
                    f"{count}. "
                    f"{user.mention}\n"
                )

        if count == 0:
            text += "لا يوجد مشرفين."

        await message.reply_text(text)

    except Exception:

        await message.reply_text(
            "❌ حصل خطأ أثناء جلب المشرفين."
        )


# =========================================================
# ترقية
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^ترقية$")
)
async def promote_user(client, message):

    if not await is_owner(message):
        await message.reply_text(
            "❌ الترقية للمالك فقط."
        )
        return

    target = await get_target_user(message)

    if not target:
        await message.reply_text(
            "↩️ اعمل رد على الشخص واكتب: ترقية"
        )
        return

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
            target.id,
            privileges=privileges,
        )

        await message.reply_text(
            f"✅ تمت ترقية {target.mention} إلى مشرف."
        )

    except Exception as e:

        await message.reply_text(
            f"❌ مقدرتش أرقّيه.\n\n{e}"
        )


# =========================================================
# تنزيل
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^تنزيل$")
)
async def demote_user(client, message):

    if not await is_owner(message):
        await message.reply_text(
            "❌ تنزيل المشرفين للمالك فقط."
        )
        return

    target = await get_target_user(message)

    if not target:
        await message.reply_text(
            "↩️ اعمل رد على الشخص واكتب: تنزيل"
        )
        return

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
            target.id,
            privileges=privileges,
        )

        await message.reply_text(
            f"✅ تم تنزيل {target.mention}."
        )

    except Exception as e:

        await message.reply_text(
            f"❌ مقدرتش أنزله.\n\n{e}"
        )


# =========================================================
# طرد
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^طرد$")
)
async def kick_user(client, message):

    if not await is_admin(message):
        await message.reply_text(
            "❌ الأمر للمشرفين فقط."
        )
        return

    target = await get_target_user(message)

    if not target:
        await message.reply_text(
            "↩️ اعمل رد على الشخص واكتب: طرد"
        )
        return

    try:

        await bot.ban_chat_member(
            message.chat.id,
            target.id,
        )

        await bot.unban_chat_member(
            message.chat.id,
            target.id,
        )

        await message.reply_text(
            f"🚫 تم طرد {target.mention}."
        )

    except Exception as e:

        await message.reply_text(
            f"❌ مقدرتش أطرده.\n\n{e}"
        )


# =========================================================
# حظر
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^حظر$")
)
async def ban_user(client, message):

    if not await is_admin(message):
        await message.reply_text(
            "❌ الأمر للمشرفين فقط."
        )
        return

    target = await get_target_user(message)

    if not target:
        await message.reply_text(
            "↩️ اعمل رد على الشخص واكتب: حظر"
        )
        return

    try:

        await bot.ban_chat_member(
            message.chat.id,
            target.id,
        )

        await message.reply_text(
            f"🔨 تم حظر {target.mention}."
        )

    except Exception as e:

        await message.reply_text(
            f"❌ مقدرتش أحظره.\n\n{e}"
        )


# =========================================================
# فك حظر
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^فك حظر$")
)
async def unban_user(client, message):

    if not await is_admin(message):
        await message.reply_text(
            "❌ الأمر للمشرفين فقط."
        )
        return

    target = await get_target_user(message)

    if not target:
        await message.reply_text(
            "↩️ اعمل رد على الشخص واكتب: فك حظر"
        )
        return

    try:

        await bot.unban_chat_member(
            message.chat.id,
            target.id,
        )

        await message.reply_text(
            f"✅ تم فك حظر {target.mention}."
        )

    except Exception as e:

        await message.reply_text(
            f"❌ حصل خطأ.\n\n{e}"
        )


# =========================================================
# كتم
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^كتم$")
)
async def mute_user(client, message):

    if not await is_admin(message):
        await message.reply_text(
            "❌ الأمر للمشرفين فقط."
        )
        return

    target = await get_target_user(message)

    if not target:
        await message.reply_text(
            "↩️ اعمل رد على الشخص واكتب: كتم"
        )
        return

    try:

        permissions = ChatPermissions(
            can_send_messages=False,
        )

        await bot.restrict_chat_member(
            message.chat.id,
            target.id,
            permissions=permissions,
        )

        await message.reply_text(
            f"🔇 تم كتم {target.mention}."
        )

    except Exception as e:

        await message.reply_text(
            f"❌ مقدرتش أكتمه.\n\n{e}"
        )


# =========================================================
# فك كتم
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^فك كتم$")
)
async def unmute_user(client, message):

    if not await is_admin(message):
        await message.reply_text(
            "❌ الأمر للمشرفين فقط."
        )
        return

    target = await get_target_user(message)

    if not target:
        await message.reply_text(
            "↩️ اعمل رد على الشخص واكتب: فك كتم"
        )
        return

    try:

        permissions = ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_send_polls=True,
            can_add_web_page_previews=True,
            can_invite_users=True,
        )

        await bot.restrict_chat_member(
            message.chat.id,
            target.id,
            permissions=permissions,
        )

        await message.reply_text(
            f"🔊 تم فك كتم {target.mention}."
        )

    except Exception as e:

        await message.reply_text(
            f"❌ مقدرتش أفك الكتم.\n\n{e}"
        )


# =========================================================
# التحذيرات
# =========================================================

def warning_key(chat_id, user_id):
    return f"{chat_id}:{user_id}"


@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^تحذير$")
)
async def warn_user(client, message):

    if not await is_admin(message):
        await message.reply_text(
            "❌ الأمر للمشرفين فقط."
        )
        return

    target = await get_target_user(message)

    if not target:
        await message.reply_text(
            "↩️ اعمل رد على الشخص واكتب: تحذير"
        )
        return

    key = warning_key(
        message.chat.id,
        target.id,
    )

    warnings_data[key] = (
        int(warnings_data.get(key, 0)) + 1
    )

    save_json(
        WARNINGS_FILE,
        warnings_data,
    )

    count = warnings_data[key]

    await message.reply_text(
        f"⚠️ تم تحذير {target.mention}\n"
        f"عدد التحذيرات: {count}"
    )


@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^تحذيرات$")
)
async def show_warnings(client, message):

    target = await get_target_user(message)

    user = (
        target
        if target
        else message.from_user
    )

    key = warning_key(
        message.chat.id,
        user.id,
    )

    count = warnings_data.get(key, 0)

    await message.reply_text(
        f"⚠️ تحذيرات {user.mention}: {count}"
    )


@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^مسح تحذيرات$")
)
async def clear_warnings(client, message):

    if not await is_admin(message):
        await message.reply_text(
            "❌ الأمر للمشرفين فقط."
        )
        return

    target = await get_target_user(message)

    if not target:
        await message.reply_text(
            "↩️ اعمل رد على الشخص واكتب: مسح تحذيرات"
        )
        return

    key = warning_key(
        message.chat.id,
        target.id,
    )

    warnings_data.pop(key, None)

    save_json(
        WARNINGS_FILE,
        warnings_data,
    )

    await message.reply_text(
        f"✅ تم مسح تحذيرات {target.mention}."
    )


# =========================================================
# التثبيت
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^تثبيت$")
)
async def pin_message(client, message):

    if not await is_admin(message):
        await message.reply_text(
            "❌ الأمر للمشرفين فقط."
        )
        return

    if not message.reply_to_message:
        await message.reply_text(
            "↩️ اعمل رد على الرسالة التي تريد تثبيتها."
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
            f"❌ مقدرتش أثبتها.\n\n{e}"
        )


@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^إلغاء تثبيت$")
)
async def unpin_message(client, message):

    if not await is_admin(message):
        await message.reply_text(
            "❌ الأمر للمشرفين فقط."
        )
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
            f"❌ حصل خطأ.\n\n{e}"
        )


# =========================================================
# إعدادات الحماية
# =========================================================

PROTECTION_COMMANDS = {
    "الروابط": "links",
    "الصور": "photos",
    "الفيديو": "videos",
    "الملصقات": "stickers",
    "الصوت": "voice",
    "السب": "bad_words",
}


@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(
        r"^(قفل|فتح) (الروابط|الصور|الفيديو|الملصقات|الصوت|السب)$"
    )
)
async def protection_command(client, message):

    if not await is_admin(message):
        await message.reply_text(
            "❌ الأمر للمشرفين فقط."
        )
        return

    match = re.match(
        r"^(قفل|فتح) (الروابط|الصور|الفيديو|الملصقات|الصوت|السب)$",
        message.text.strip(),
    )

    if not match:
        return

    action = match.group(1)
    name = match.group(2)

    setting = PROTECTION_COMMANDS[name]

    settings = get_settings(
        message.chat.id
    )

    settings[setting] = (
        action == "قفل"
    )

    save_json(
        GROUP_SETTINGS_FILE,
        group_settings,
    )

    if action == "قفل":
        await message.reply_text(
            f"🔒 تم قفل {name}."
        )
    else:
        await message.reply_text(
            f"🔓 تم فتح {name}."
        )


# =========================================================
# إضافة رد
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^اضف رد ")
)
async def add_reply(client, message):

    if not await is_admin(message):
        await message.reply_text(
            "❌ إضافة الردود للمشرفين فقط."
        )
        return

    text = message.text.strip()

    content = text[
        len("اضف رد "):
    ]

    if "=" not in content:
        await message.reply_text(
            "❌ استخدم:\n"
            "اضف رد الكلمة = الرد"
        )
        return

    trigger, reply = content.split(
        "=",
        1,
    )

    trigger = trigger.strip()
    reply = reply.strip()

    if not trigger or not reply:
        await message.reply_text(
            "❌ لازم تكتب الكلمة والرد."
        )
        return

    chat_key = str(message.chat.id)

    if chat_key not in custom_replies:
        custom_replies[chat_key] = {}

    if (
        trigger not in custom_replies[chat_key]
        and len(custom_replies[chat_key]) >= 500
    ):
        await message.reply_text(
            "❌ وصلت للحد الأقصى: 500 رد."
        )
        return

    custom_replies[chat_key][trigger] = reply

    save_json(
        CUSTOM_REPLIES_FILE,
        custom_replies,
    )

    await message.reply_text(
        f"✅ تم إضافة الرد:\n"
        f"الكلمة: {trigger}\n"
        f"الرد: {reply}"
    )


# =========================================================
# مسح رد
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^مسح رد ")
)
async def delete_reply(client, message):

    if not await is_admin(message):
        await message.reply_text(
            "❌ الأمر للمشرفين فقط."
        )
        return

    trigger = message.text[
        len("مسح رد "):
    ].strip()

    chat_key = str(message.chat.id)

    if (
        chat_key in custom_replies
        and trigger in custom_replies[chat_key]
    ):

        del custom_replies[chat_key][trigger]

        save_json(
            CUSTOM_REPLIES_FILE,
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
# البحث عن الأغنية
# =========================================================

def search_and_download(song_name):

    queries = [
        f"scsearch1:{song_name}",
        f"ytsearch1:{song_name}",
    ]

    for query in queries:

        try:

            ydl_options = {
                "format": "bestaudio/best",
                "outtmpl": str(
                    DOWNLOAD_DIR / "%(id)s.%(ext)s"
                ),
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "extractor_args": {
                    "youtube": {
                        "player_client": [
                            "android",
                        ]
                    }
                },
            }

            with yt_dlp.YoutubeDL(
                ydl_options
            ) as ydl:

                info = ydl.extract_info(
                    query,
                    download=True,
                )

                if not info:
                    continue

                if "entries" in info:
                    entries = info.get(
                        "entries"
                    )

                    if not entries:
                        continue

                    info = entries[0]

                song_id = info.get("id")

                if not song_id:
                    continue

                files = glob.glob(
                    str(
                        DOWNLOAD_DIR
                        / f"{song_id}.*"
                    )
                )

                if not files:
                    continue

                return {
                    "path": files[0],
                    "title": info.get(
                        "title",
                        song_name,
                    ),
                    "duration": info.get(
                        "duration",
                        0,
                    ),
                    "url": info.get(
                        "webpage_url",
                        "",
                    ),
                }

        except Exception:
            continue

    return None


async def download_song(song_name):

    return await asyncio.to_thread(
        search_and_download,
        song_name,
    )


# =========================================================
# تشغيل أغنية
# =========================================================

async def play_song(
    chat_id,
    song,
    requester,
):

    global calls

    if calls is None:
        raise RuntimeError(
            "PyTgCalls لم يتم تشغيله."
        )

    if not song.get("path"):
        raise RuntimeError(
            "ملف الأغنية غير موجود."
        )

    # مهم جدًا:
    # PyTgCalls لازم يكون started قبل play
    stream = MediaStream(
        song["path"],
        video_flags=MediaStream.Flags.IGNORE,
    )

    await calls.play(
        chat_id,
        stream,
        GroupCallConfig(
            auto_start=True,
        ),
    )

    current_songs[chat_id] = {
        **song,
        "requester": requester,
    }


# =========================================================
# تشغيل الأغنية التالية
# =========================================================

async def play_next(chat_id):

    queue = music_queues.get(
        chat_id,
        [],
    )

    if not queue:
        current_songs.pop(
            chat_id,
            None,
        )
        return False

    item = queue.pop(0)

    song = item["song"]
    requester = item["requester"]

    try:

        await play_song(
            chat_id,
            song,
            requester,
        )

        return True

    except Exception as e:

        current_songs.pop(
            chat_id,
            None,
        )

        try:
            await bot.send_message(
                chat_id,
                f"❌ حصل خطأ في تشغيل الأغنية:\n\n{e}",
            )
        except Exception:
            pass

        return False


# =========================================================
# تشغيل
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^تشغيل(?:\s+(.+))?$")
)
async def music_play_command(
    client,
    message,
):

    settings = get_settings(
        message.chat.id
    )

    if not settings["enabled"]:
        await message.reply_text(
            "⛔ البوت غير مفعّل في المجموعة.\n"
            "اكتب: تفعيل البوت"
        )
        return

    match = re.match(
        r"^تشغيل(?:\s+(.+))?$",
        message.text.strip(),
    )

    song_name = (
        match.group(1).strip()
        if match and match.group(1)
        else None
    )

    if not song_name:

        waiting_for_song.add(
            message.chat.id
        )

        await message.reply_text(
            "🎵 قول اسم الأغنية."
        )
        return

    await handle_song_request(
        message,
        song_name,
    )


# =========================================================
# استقبال اسم الأغنية بعد تشغيل
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
)
async def song_name_handler(
    client,
    message,
):

    chat_id = message.chat.id

    if chat_id not in waiting_for_song:
        return

    text = message.text.strip()

    if not text:
        return

    if text in {
        "تشغيل",
        "تخطي",
        "وقف",
        "إيقاف",
    }:
        return

    waiting_for_song.discard(
        chat_id
    )

    settings = get_settings(
        chat_id
    )

    if not settings["enabled"]:
        return

    await handle_song_request(
        message,
        text,
    )


# =========================================================
# تنفيذ طلب الأغنية
# =========================================================

async def handle_song_request(
    message,
    song_name,
):

    await message.reply_text(
        f"🔎 بدور على:\n"
        f"**{song_name}**"
    )

    song = await download_song(
        song_name
    )

    if not song:

        await message.reply_text(
            "❌ مقدرتش ألاقي الأغنية."
        )
        return

    chat_id = message.chat.id

    requester = (
        message.from_user.mention
        if message.from_user
        else "مستخدم"
    )

    if chat_id not in music_queues:
        music_queues[chat_id] = []

    # لو فيه أغنية شغالة، نحط الجديدة في القائمة
    if chat_id in current_songs:

        music_queues[chat_id].append(
            {
                "song": song,
                "requester": requester,
            }
        )

        position = len(
            music_queues[chat_id]
        )

        await message.reply_text(
            f"➕ اتضافت للقائمة.\n"
            f"📍 الترتيب: {position}\n"
            f"🎵 {song['title']}"
        )

        return

    # أول أغنية
    try:

        await play_song(
            chat_id,
            song,
            requester,
        )

        await send_now_playing(
            message,
            song,
            requester,
        )

    except Exception as e:

        await message.reply_text(
            "❌ حصل خطأ في تشغيل الأغنية:\n\n"
            f"{e}"
        )


# =========================================================
# رسالة الآن التشغيل
# =========================================================

async def send_now_playing(
    message,
    song,
    requester,
):

    duration = song.get(
        "duration",
        0,
    )

    if duration:

        minutes = int(duration // 60)
        seconds = int(duration % 60)

        duration_text = (
            f"{minutes}:{seconds:02d}"
        )

    else:
        duration_text = "غير معروف"

    caption = (
        "🎵 **مريومه الدلوعه**\n\n"
        f"🎶 الأغنية: **{song['title']}**\n"
        f"⏱ المدة: **{duration_text}**\n"
        f"👤 الطلب بواسطة: {requester}"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⏭ تخطي",
                    callback_data="music_skip",
                ),
                InlineKeyboardButton(
                    "⏹ وقف",
                    callback_data="music_stop",
                ),
            ],
        ]
    )

    if os.path.exists(PHOTO_PATH):

        await message.reply_photo(
            PHOTO_PATH,
            caption=caption,
            reply_markup=keyboard,
        )

    else:

        await message.reply_text(
            caption,
            reply_markup=keyboard,
        )


# =========================================================
# تخطي
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^تخطي$")
)
async def skip_song(client, message):

    if not await is_admin(message):
        await message.reply_text(
            "❌ تخطي الأغاني للمشرفين فقط."
        )
        return

    chat_id = message.chat.id

    if not current_songs.get(chat_id):
        await message.reply_text(
            "❌ مفيش أغنية شغالة."
        )
        return

    try:

        await calls.leave_call(
            chat_id
        )

    except Exception:
        pass

    current_songs.pop(
        chat_id,
        None,
    )

    if await play_next(chat_id):

        song = current_songs.get(
            chat_id
        )

        if song:

            await message.reply_text(
                f"⏭ تم التخطي.\n"
                f"🎵 شغال الآن: **{song['title']}**"
            )

    else:

        await message.reply_text(
            "⏭ تم التخطي.\n"
            "📭 القائمة فاضية."
        )


# =========================================================
# وقف
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^(وقف|إيقاف)$")
)
async def stop_song(client, message):

    if not await is_admin(message):
        await message.reply_text(
            "❌ إيقاف الأغاني للمشرفين فقط."
        )
        return

    chat_id = message.chat.id

    try:

        await calls.leave_call(
            chat_id
        )

    except Exception:
        pass

    music_queues.pop(
        chat_id,
        None,
    )

    current_songs.pop(
        chat_id,
        None,
    )

    await message.reply_text(
        "⏹ تم إيقاف الأغاني ومسح القائمة."
    )


# =========================================================
# القائمة
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^القائمة$")
)
async def music_queue(client, message):

    chat_id = message.chat.id

    queue = music_queues.get(
        chat_id,
        [],
    )

    current = current_songs.get(
        chat_id
    )

    text = "🎵 **قائمة التشغيل**\n\n"

    if current:
        text += (
            f"▶️ الآن:\n"
            f"**{current['title']}**\n\n"
        )

    if not queue:

        text += "📭 مفيش أغاني في الانتظار."

    else:

        for index, item in enumerate(
            queue,
            start=1,
        ):

            text += (
                f"{index}. "
                f"{item['song']['title']}\n"
            )

    await message.reply_text(text)


# =========================================================
# أزرار الميوزك
# =========================================================

@bot.on_callback_query(
    filters.regex(
        r"^music_(skip|stop)$"
    )
)
async def music_buttons(
    client,
    callback_query,
):

    chat_id = callback_query.message.chat.id

    # نتأكد أن ضاغط الزر مشرف
    status = await get_member_status(
        chat_id,
        callback_query.from_user.id,
    )

    if status not in {
        "owner",
        "creator",
        "administrator",
        "admin",
    }:

        await callback_query.answer(
            "❌ الزر للمشرفين فقط.",
            show_alert=True,
        )
        return

    action = callback_query.matches[0].group(1)

    await callback_query.answer()

    if action == "stop":

        try:
            await calls.leave_call(
                chat_id
            )
        except Exception:
            pass

        music_queues.pop(
            chat_id,
            None,
        )

        current_songs.pop(
            chat_id,
            None,
        )

        await callback_query.message.reply_text(
            "⏹ تم إيقاف الأغاني."
        )

    elif action == "skip":

        try:
            await calls.leave_call(
                chat_id
            )
        except Exception:
            pass

        current_songs.pop(
            chat_id,
            None,
        )

        if await play_next(chat_id):

            song = current_songs.get(
                chat_id
            )

            if song:

                await callback_query.message.reply_text(
                    f"⏭ تم التخطي.\n"
                    f"🎵 **{song['title']}**"
                )

        else:

            await callback_query.message.reply_text(
                "📭 القائمة فاضية."
            )


# =========================================================
# الردود المخصصة
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
)
async def custom_reply_handler(
    client,
    message,
):

    text = message.text.strip()

    chat_key = str(
        message.chat.id
    )

    replies = custom_replies.get(
        chat_key,
        {},
    )

    if text in replies:

        await message.reply_text(
            replies[text]
        )


# =========================================================
# حماية الروابط والكلمات
# =========================================================

URL_PATTERN = re.compile(
    r"(https?://|www\.|t\.me/|telegram\.me/)",
    re.IGNORECASE,
)


@bot.on_message(
    filters.group
)
async def protection_handler(
    client,
    message,
):

    if not message.from_user:
        return

    settings = get_settings(
        message.chat.id
    )

    # المشرفين مستثنين
    status = await get_member_status(
        message.chat.id,
        message.from_user.id,
    )

    if status in {
        "owner",
        "creator",
        "administrator",
        "admin",
    }:
        return

    try:

        # الروابط
        if (
            settings["links"]
            and message.text
            and URL_PATTERN.search(
                message.text
            )
        ):

            await message.delete()
            return

        # الكلمات
        if (
            settings["bad_words"]
            and message.text
        ):

            lower_text = (
                message.text.lower()
            )

            for word in BAD_WORDS:

                if word.lower() in lower_text:

                    await message.delete()
                    return

        # الصور
        if (
            settings["photos"]
            and message.photo
        ):

            await message.delete()
            return

        # الفيديو
        if (
            settings["videos"]
            and message.video
        ):

            await message.delete()
            return

        # الملصقات
        if (
            settings["stickers"]
            and message.sticker
        ):

            await message.delete()
            return

        # الصوت
        if (
            settings["voice"]
            and (
                message.voice
                or message.audio
            )
        ):

            await message.delete()
            return

    except Exception:
        pass


# =========================================================
# ترحيب الأعضاء
# =========================================================

@bot.on_message(
    filters.group
    & filters.new_chat_members
)
async def welcome_new_members(
    client,
    message,
):

    for user in message.new_chat_members:

        if user.is_bot:
            continue

        await message.reply_text(
            f"👋 أهلاً وسهلاً "
            f"{user.mention}\n"
            f"نورت المجموعة ❤️"
        )


# =========================================================
# المساعدة
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
    & filters.regex(r"^(مساعدة|الاوامر|الأوامر)$")
)
async def help_command(
    client,
    message,
):

    text = """
🎀 **مساعدة مريومه الدلوعه**

🎵 **الميوزك**
• تشغيل
• تشغيل اسم الأغنية
• تخطي
• وقف
• إيقاف
• القائمة

👑 **الإدارة**
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

🛡️ **الحماية**
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

🤖 **الردود**
• اضف رد الكلمة = الرد
• مسح رد الكلمة

⚙️ **البوت**
• تفعيل البوت
• تعطيل البوت
"""

    await message.reply_text(text)


# =========================================================
# تشغيل البوت
# =========================================================

async def main():

    global calls

    print("🚀 Starting MariamMusicBot...")

    await bot.start()

    print("✅ Bot started")

    await assistant.start()

    print("✅ Assistant started")

    # مهم جدًا:
    # إنشاء PyTgCalls بعد دخول نفس الـevent loop
    calls = PyTgCalls(
        assistant
    )

    # مهم جدًا:
    # لازم يبدأ قبل calls.play()
    await calls.start()

    print("✅ PyTgCalls started")

    print("🎵 Music system ready")

    await idle()

    try:
        await calls.stop()
    except Exception:
        pass

    await assistant.stop()
    await bot.stop()


# =========================================================
# Start
# =========================================================

if __name__ == "__main__":
    asyncio.run(main())
