import os
import re
import json
import asyncio
from pathlib import Path
from collections import defaultdict, deque

import static_ffmpeg
static_ffmpeg.add_paths()

import yt_dlp

from pyrogram import Client, filters, enums
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
# DATA
# =========================================================

DATA_DIR = Path("data")
MUSIC_DIR = Path("music_cache")

DATA_DIR.mkdir(exist_ok=True)
MUSIC_DIR.mkdir(exist_ok=True)

CUSTOM_FILE = DATA_DIR / "custom_replies.json"
SETTINGS_FILE = DATA_DIR / "group_settings.json"
WARN_FILE = DATA_DIR / "warnings.json"


def load_json(path, default):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass

    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


custom_replies = load_json(
    CUSTOM_FILE,
    {}
)

group_settings = load_json(
    SETTINGS_FILE,
    {}
)

warnings = load_json(
    WARN_FILE,
    {}
)


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

# مهم:
# لا تعمل PyTgCalls هنا.
# هنعمله داخل main() بعد دخول الـ Event Loop.
calls = None


# =========================================================
# MUSIC MEMORY
# =========================================================

queues = defaultdict(deque)
current_song = {}

waiting_song = set()

download_locks = {}


# =========================================================
# SETTINGS
# =========================================================

DEFAULT_SETTINGS = {
    "enabled": True,

    "links": False,
    "photos": False,
    "videos": False,
    "stickers": False,
    "voice": False,

    "bad_words": True,
}


# اكتب الكلمات الممنوعة اللي عايزها هنا
BAD_WORDS = {
    "كلمة_ممنوعة_1",
    "كلمة_ممنوعة_2",
}


def get_settings(chat_id):

    key = str(chat_id)

    if key not in group_settings:
        group_settings[key] = DEFAULT_SETTINGS.copy()
        save_json(
            SETTINGS_FILE,
            group_settings
        )

    else:

        changed = False

        for k, v in DEFAULT_SETTINGS.items():

            if k not in group_settings[key]:
                group_settings[key][k] = v
                changed = True

        if changed:
            save_json(
                SETTINGS_FILE,
                group_settings
            )

    return group_settings[key]


# =========================================================
# HELPERS
# =========================================================

def is_group(message):

    if not message.chat:
        return False

    return message.chat.type in (
        enums.ChatType.GROUP,
        enums.ChatType.SUPERGROUP,
    )


async def is_admin(chat_id, user_id):

    try:

        member = await bot.get_chat_member(
            chat_id,
            user_id
        )

        status = str(
            member.status
        ).lower()

        return status in (
            "owner",
            "creator",
            "administrator",
            "admin",
        )

    except Exception:
        return False


async def is_owner(chat_id, user_id):

    try:

        member = await bot.get_chat_member(
            chat_id,
            user_id
        )

        status = str(
            member.status
        ).lower()

        return status in (
            "owner",
            "creator",
        )

    except Exception:
        return False


async def require_admin(message):

    if not message.from_user:

        await message.reply_text(
            "❌ مش قادر أحدد المستخدم."
        )

        return False

    if not await is_admin(
        message.chat.id,
        message.from_user.id
    ):

        await message.reply_text(
            "❌ الأمر ده للمشرفين فقط."
        )

        return False

    return True


async def enabled(message):

    if not is_group(message):
        return True

    return get_settings(
        message.chat.id
    )["enabled"]


async def safe_delete(message):

    try:
        await message.delete()
    except Exception:
        pass


# =========================================================
# FIND TARGET USER
# =========================================================

async def get_target_user(message):

    if (
        message.reply_to_message
        and message.reply_to_message.from_user
    ):
        return message.reply_to_message.from_user

    return None


# =========================================================
# MUSIC SEARCH / DOWNLOAD
# =========================================================

def clean_name(text):

    text = re.sub(
        r'[\\/:*?"<>|]+',
        "",
        text
    )

    text = text.strip()

    return text[:80] or "song"


async def download_song(query):

    safe = clean_name(query)

    if query not in download_locks:
        download_locks[query] = asyncio.Lock()

    async with download_locks[query]:

        existing = list(
            MUSIC_DIR.glob(
                f"{safe}.*"
            )
        )

        if existing:
            return str(existing[0])

        # SoundCloud أولاً
        sources = [
            f"scsearch1:{query}",
            f"ytsearch1:{query}",
        ]

        last_error = None

        for source in sources:

            output = str(
                MUSIC_DIR /
                f"{safe}.%(ext)s"
            )

            options = {
                "format": "bestaudio/best",
                "outtmpl": output,
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "retries": 2,
                "fragment_retries": 2,
                "socket_timeout": 30,
                "overwrites": False,
            }

            if source.startswith("ytsearch"):

                options["extractor_args"] = {
                    "youtube": {
                        "player_client": [
                            "android"
                        ]
                    }
                }

            try:

                def run_download():

                    with yt_dlp.YoutubeDL(
                        options
                    ) as ydl:

                        return ydl.extract_info(
                            source,
                            download=True
                        )

                info = await asyncio.to_thread(
                    run_download
                )

                if info:

                    files = list(
                        MUSIC_DIR.glob(
                            f"{safe}.*"
                        )
                    )

                    if files:
                        return str(files[0])

            except Exception as e:

                last_error = e

        raise RuntimeError(
            "مش قادر ألاقي الأغنية حالياً."
        ) from last_error


# =========================================================
# PLAY MUSIC
# =========================================================

async def play_song(chat_id):

    global calls

    if calls is None:
        return

    if not queues[chat_id]:

        current_song.pop(
            chat_id,
            None
        )

        return

    song = queues[
        chat_id
    ].popleft()

    current_song[
        chat_id
    ] = song

    try:

        await calls.play(

            chat_id,

            MediaStream(
                song["path"],
                video_flags=
                MediaStream.Flags.IGNORE,
            ),

            GroupCallConfig(
                auto_start=True
            )
        )

        await send_now_playing(
            chat_id,
            song
        )

    except Exception as e:

        current_song.pop(
            chat_id,
            None
        )

        try:

            await song["message"].reply_text(
                "❌ حصل خطأ في تشغيل الأغنية:\n\n"
                f"`{str(e)[:700]}`"
            )

        except Exception:
            pass


# =========================================================
# NOW PLAYING
# =========================================================

async def send_now_playing(
    chat_id,
    song
):

    requester = song.get(
        "requester",
        "غير معروف"
    )

    text = (
        "🎶 **مريومه الدلوعه**\n\n"
        f"🎵 **الأغنية:** {song['title']}\n"
        f"👤 **الطلب:** {requester}\n\n"
        "▶️ الأغنية شغالة الآن"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⏭ تخطي",
                    callback_data="music_skip"
                ),
                InlineKeyboardButton(
                    "⏹ وقف",
                    callback_data="music_stop"
                ),
            ],
            [
                InlineKeyboardButton(
                    "📋 القائمة",
                    callback_data="music_queue"
                )
            ]
        ]
    )

    try:

        if os.path.exists(
            PHOTO_PATH
        ):

            await bot.send_photo(
                chat_id,
                PHOTO_PATH,
                caption=text,
                reply_markup=keyboard
            )

        else:

            await bot.send_message(
                chat_id,
                text,
                reply_markup=keyboard
            )

    except Exception:
        pass


# =========================================================
# ADD SONG
# =========================================================

async def add_song(
    message,
    query
):

    if not await enabled(message):

        await message.reply_text(
            "⛔ البوت متعطل في المجموعة."
        )

        return

    status = await message.reply_text(
        f"🔎 بدور على:\n**{query}**"
    )

    try:

        path = await download_song(
            query
        )

        requester = (
            message.from_user.mention
            if message.from_user
            else "غير معروف"
        )

        song = {
            "title": query,
            "path": path,
            "requester": requester,
            "message": message,
        }

        chat_id = message.chat.id

        was_empty = (
            chat_id not in current_song
            and not queues[chat_id]
        )

        queues[
            chat_id
        ].append(song)

        await safe_delete(
            status
        )

        if was_empty:

            await play_song(
                chat_id
            )

        else:

            await message.reply_text(
                "✅ اتضافت للقائمة.\n\n"
                f"🎵 {query}\n"
                f"📌 رقمها: "
                f"{len(queues[chat_id])}"
            )

    except Exception as e:

        await safe_delete(
            status
        )

        await message.reply_text(
            "❌ مش قادر أشغل الأغنية.\n\n"
            f"{str(e)[:600]}"
        )


# =========================================================
# MUSIC COMMANDS
# =========================================================

@bot.on_message(
    filters.group & filters.text,
    group=1
)
async def music_commands(
    _,
    message
):

    text = message.text.strip()

    if not await enabled(message):
        return

    # -----------------------------
    # تشغيل
    # -----------------------------

    if text == "تشغيل":

        waiting_song.add(
            message.chat.id
        )

        await message.reply_text(
            "🎵 قول اسم الأغنية"
        )

        return

    # -----------------------------
    # تشغيل + اسم
    # -----------------------------

    if text.startswith("تشغيل "):

        query = text[
            len("تشغيل "):
        ].strip()

        if query:

            await add_song(
                message,
                query
            )

        return

    # -----------------------------
    # تخطي
    # -----------------------------

    if text in (
        "تخطي",
        "التالي"
    ):

        if not await require_admin(
            message
        ):
            return

        try:

            await calls.leave_call(
                message.chat.id
            )

        except Exception:
            pass

        current_song.pop(
            message.chat.id,
            None
        )

        if queues[
            message.chat.id
        ]:

            await play_song(
                message.chat.id
            )

        else:

            await message.reply_text(
                "📭 مفيش أغاني تانية."
            )

        return

    # -----------------------------
    # وقف
    # -----------------------------

    if text in (
        "وقف",
        "إيقاف"
    ):

        if not await require_admin(
            message
        ):
            return

        try:

            await calls.leave_call(
                message.chat.id
            )

        except Exception:
            pass

        queues[
            message.chat.id
        ].clear()

        current_song.pop(
            message.chat.id,
            None
        )

        await message.reply_text(
            "⏹ تم إيقاف الميوزك."
        )

        return

    # -----------------------------
    # القائمة
    # -----------------------------

    if text == "القائمة":

        lines = [
            "🎵 **قائمة الأغاني**"
        ]

        now = current_song.get(
            message.chat.id
        )

        if now:

            lines.append(
                f"▶️ الآن: **{now['title']}**"
            )

        queue = queues[
            message.chat.id
        ]

        if queue:

            for i, song in enumerate(
                queue,
                1
            ):

                lines.append(
                    f"{i}. {song['title']}"
                )

        if not now and not queue:

            lines.append(
                "📭 القائمة فاضية."
            )

        await message.reply_text(
            "\n".join(lines)
        )


# =========================================================
# SONG NAME AFTER "تشغيل"
# =========================================================

@bot.on_message(
    filters.group & filters.text,
    group=2
)
async def waiting_song_handler(
    _,
    message
):

    chat_id = message.chat.id

    if chat_id not in waiting_song:
        return

    text = message.text.strip()

    if text in (
        "تشغيل",
        "وقف",
        "إيقاف",
        "تخطي",
        "التالي",
        "القائمة"
    ):
        return

    waiting_song.discard(
        chat_id
    )

    await add_song(
        message,
        text
    )


# =========================================================
# MUSIC BUTTONS
# =========================================================

@bot.on_callback_query()
async def music_buttons(
    _,
    query
):

    try:
        await query.answer()
    except Exception:
        pass

    chat_id = query.message.chat.id

    # -----------------------------
    # تخطي
    # -----------------------------

    if query.data == "music_skip":

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

        if queues[chat_id]:

            await play_song(
                chat_id
            )

        else:

            await query.message.reply_text(
                "📭 مفيش أغاني تانية."
            )

    # -----------------------------
    # وقف
    # -----------------------------

    elif query.data == "music_stop":

        try:

            await calls.leave_call(
                chat_id
            )

        except Exception:
            pass

        queues[
            chat_id
        ].clear()

        current_song.pop(
            chat_id,
            None
        )

        await query.message.reply_text(
            "⏹ تم إيقاف الميوزك."
        )

    # -----------------------------
    # القائمة
    # -----------------------------

    elif query.data == "music_queue":

        lines = [
            "🎵 **القائمة**"
        ]

        now = current_song.get(
            chat_id
        )

        if now:

            lines.append(
                f"▶️ الآن: {now['title']}"
            )

        for i, song in enumerate(
            queues[chat_id],
            1
        ):

            lines.append(
                f"{i}. {song['title']}"
            )

        if not now and not queues[chat_id]:

            lines.append(
                "📭 القائمة فاضية."
            )

        await query.message.reply_text(
            "\n".join(lines)
        )


# =========================================================
# ACTIVATE / DEACTIVATE
# =========================================================

@bot.on_message(
    filters.group & filters.text,
    group=3
)
async def activation(
    _,
    message
):

    text = message.text.strip()

    if text not in (
        "تفعيل البوت",
        "تعطيل البوت"
    ):
        return

    if not await require_admin(
        message
    ):
        return

    settings = get_settings(
        message.chat.id
    )

    if text == "تفعيل البوت":

        settings["enabled"] = True

        await message.reply_text(
            "✅ تم تفعيل البوت."
        )

    else:

        settings["enabled"] = False

        await message.reply_text(
            "⛔ تم تعطيل البوت."
        )

    save_json(
        SETTINGS_FILE,
        group_settings
    )


# =========================================================
# ADD REPLY / DELETE REPLY
# =========================================================

@bot.on_message(
    filters.group & filters.text,
    group=4
)
async def reply_commands(
    _,
    message
):

    text = message.text.strip()

    # -----------------------------
    # إضافة رد
    # -----------------------------

    if text.startswith("اضف رد "):

        if not await require_admin(
            message
        ):
            return

        data = text[
            len("اضف رد "):
        ].strip()

        if "=" not in data:

            await message.reply_text(
                "❌ استخدم:\n\n"
                "`اضف رد الكلمة = الرد`"
            )

            return

        trigger, reply = data.split(
            "=",
            1
        )

        trigger = trigger.strip()
        reply = reply.strip()

        if not trigger or not reply:

            await message.reply_text(
                "❌ اكتب الكلمة والرد."
            )

            return

        chat_key = str(
            message.chat.id
        )

        custom_replies.setdefault(
            chat_key,
            {}
        )

        # الحد الأقصى 500
        if (
            trigger not in
            custom_replies[chat_key]
            and len(
                custom_replies[chat_key]
            ) >= 500
        ):

            await message.reply_text(
                "❌ وصلت للحد الأقصى وهو 500 رد."
            )

            return

        custom_replies[
            chat_key
        ][trigger] = reply

        save_json(
            CUSTOM_FILE,
            custom_replies
        )

        await message.reply_text(
            "✅ تم إضافة الرد."
        )

        return

    # -----------------------------
    # حذف رد
    # -----------------------------

    if text.startswith("مسح رد "):

        if not await require_admin(
            message
        ):
            return

        trigger = text[
            len("مسح رد "):
        ].strip()

        chat_key = str(
            message.chat.id
        )

        data = custom_replies.get(
            chat_key,
            {}
        )

        if trigger not in data:

            await message.reply_text(
                "❌ الرد مش موجود."
            )

            return

        del data[trigger]

        save_json(
            CUSTOM_FILE,
            custom_replies
        )

        await message.reply_text(
            "✅ تم مسح الرد."
        )


# =========================================================
# AUTO REPLIES
# =========================================================

@bot.on_message(
    filters.group & filters.text,
    group=5
)
async def automatic_replies(
    _,
    message
):

    if not await enabled(message):
        return

    text = message.text.strip()

    if text.startswith(
        (
            "اضف رد ",
            "مسح رد ",
        )
    ):
        return

    data = custom_replies.get(
        str(message.chat.id),
        {}
    )

    for trigger, reply in data.items():

        if trigger.lower() in text.lower():

            await message.reply_text(
                reply
            )

            break


# =========================================================
# PROTECTION
# =========================================================

@bot.on_message(
    filters.group,
    group=6
)
async def protection(
    _,
    message
):

    if not await enabled(message):
        return

    if not message.from_user:
        return

    # المشرفين مستثنين
    if await is_admin(
        message.chat.id,
        message.from_user.id
    ):
        return

    settings = get_settings(
        message.chat.id
    )

    text = (
        message.text
        or message.caption
        or ""
    ).lower()

    # -----------------------------
    # روابط
    # -----------------------------

    if settings["links"]:

        if (
            "http://" in text
            or "https://" in text
            or "t.me/" in text
            or "www." in text
        ):

            await safe_delete(
                message
            )

            return

    # -----------------------------
    # سب
    # -----------------------------

    if settings["bad_words"]:

        for word in BAD_WORDS:

            if word.lower() in text:

                await safe_delete(
                    message
                )

                return

    # -----------------------------
    # صور
    # -----------------------------

    if (
        settings["photos"]
        and message.photo
    ):

        await safe_delete(
            message
        )

        return

    # -----------------------------
    # فيديو
    # -----------------------------

    if (
        settings["videos"]
        and message.video
    ):

        await safe_delete(
            message
        )

        return

    # -----------------------------
    # ملصقات
    # -----------------------------

    if (
        settings["stickers"]
        and message.sticker
    ):

        await safe_delete(
            message
        )

        return

    # -----------------------------
    # صوت
    # -----------------------------

    if settings["voice"]:

        if (
            message.voice
            or message.audio
        ):

            await safe_delete(
                message
            )

            return


# =========================================================
# PROTECTION COMMANDS
# =========================================================

@bot.on_message(
    filters.group & filters.text,
    group=7
)
async def protection_commands(
    _,
    message
):

    text = message.text.strip()

    commands = {

        "قفل الروابط":
            ("links", True),

        "فتح الروابط":
            ("links", False),

        "قفل الصور":
            ("photos", True),

        "فتح الصور":
            ("photos", False),

        "قفل الفيديو":
            ("videos", True),

        "فتح الفيديو":
            ("videos", False),

        "قفل الملصقات":
            ("stickers", True),

        "فتح الملصقات":
            ("stickers", False),

        "قفل الصوت":
            ("voice", True),

        "فتح الصوت":
            ("voice", False),

        "قفل السب":
            ("bad_words", True),

        "فتح السب":
            ("bad_words", False),
    }

    if text not in commands:
        return

    if not await require_admin(
        message
    ):
        return

    key, value = commands[text]

    settings = get_settings(
        message.chat.id
    )

    settings[key] = value

    save_json(
        SETTINGS_FILE,
        group_settings
    )

    await message.reply_text(
        f"✅ تم تنفيذ: {text}"
    )


# =========================================================
# ADMINISTRATION
# =========================================================

@bot.on_message(
    filters.group & filters.text,
    group=8
)
async def administration(
    _,
    message
):

    text = message.text.strip()

    # -----------------------------
    # رتبتي
    # -----------------------------

    if text == "رتبتي":

        if not message.from_user:
            return

        try:

            member = await bot.get_chat_member(
                message.chat.id,
                message.from_user.id
            )

            status = str(
                member.status
            ).lower()

            names = {

                "owner":
                    "👑 المالك",

                "creator":
                    "👑 المالك",

                "administrator":
                    "🛡️ مشرف",

                "admin":
                    "🛡️ مشرف",

                "member":
                    "👤 عضو",

                "restricted":
                    "🔇 مقيد",

                "left":
                    "🚪 خارج المجموعة",

                "banned":
                    "🚫 محظور",
            }

            await message.reply_text(
                "📌 رتبتك: "
                + names.get(
                    status,
                    "غير معروف"
                )
            )

        except Exception as e:

            await message.reply_text(
                f"❌ {str(e)[:300]}"
            )

        return

    # -----------------------------
    # المالك
    # -----------------------------

    if text == "المالك":

        try:

            async for member in bot.get_chat_members(
                message.chat.id,
                filter=enums.ChatMembersFilter.ADMINISTRATORS
            ):

                status = str(
                    member.status
                ).lower()

                if status in (
                    "owner",
                    "creator"
                ):

                    await message.reply_text(
                        "👑 مالك المجموعة:\n"
                        f"{member.user.mention}"
                    )

                    return

            await message.reply_text(
                "❌ مش قادر أحدد المالك."
            )

        except Exception as e:

            await message.reply_text(
                f"❌ {str(e)[:400]}"
            )

        return

    # -----------------------------
    # المشرفين
    # -----------------------------

    if text == "المشرفين":

        lines = [
            "🛡️ **مشرفين المجموعة:**"
        ]

        try:

            async for member in bot.get_chat_members(
                message.chat.id,
                filter=enums.ChatMembersFilter.ADMINISTRATORS
            ):

                lines.append(
                    f"• {member.user.mention}"
                )

            await message.reply_text(
                "\n".join(lines)
            )

        except Exception as e:

            await message.reply_text(
                f"❌ {str(e)[:400]}"
            )

        return

    # -----------------------------
    # باقي أوامر الإدارة
    # -----------------------------

    if text not in (
        "ترقية",
        "تنزيل",
        "طرد",
        "حظر",
        "فك حظر",
        "كتم",
        "فك كتم",
    ):
        return

    if not await require_admin(
        message
    ):
        return

    user = await get_target_user(
        message
    )

    if not user:

        await message.reply_text(
            "❌ اعمل Reply على الشخص الأول."
        )

        return

    if user.is_bot:

        await message.reply_text(
            "❌ مينفعش أطبق الأمر على بوت."
        )

        return

    try:

        # -----------------------------
        # ترقية
        # -----------------------------

        if text == "ترقية":

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
                user.id,
                privileges=privileges
            )

            await message.reply_text(
                f"✅ تمت ترقية {user.mention}"
            )

        # -----------------------------
        # تنزيل
        # -----------------------------

        elif text == "تنزيل":

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
                user.id,
                privileges=privileges
            )

            await message.reply_text(
                f"✅ تم تنزيل {user.mention}"
            )

        # -----------------------------
        # طرد
        # -----------------------------

        elif text == "طرد":

            await bot.ban_chat_member(
                message.chat.id,
                user.id
            )

            await bot.unban_chat_member(
                message.chat.id,
                user.id
            )

            await message.reply_text(
                f"🚪 تم طرد {user.mention}"
            )

        # -----------------------------
        # حظر
        # -----------------------------

        elif text == "حظر":

            await bot.ban_chat_member(
                message.chat.id,
                user.id
            )

            await message.reply_text(
                f"🚫 تم حظر {user.mention}"
            )

        # -----------------------------
        # فك حظر
        # -----------------------------

        elif text == "فك حظر":

            await bot.unban_chat_member(
                message.chat.id,
                user.id
            )

            await message.reply_text(
                f"✅ تم فك حظر {user.mention}"
            )

        # -----------------------------
        # كتم
        # -----------------------------

        elif text == "كتم":

            await bot.restrict_chat_member(
                message.chat.id,
                user.id,
                ChatPermissions(
                    can_send_messages=False
                )
            )

            await message.reply_text(
                f"🔇 تم كتم {user.mention}"
            )

        # -----------------------------
        # فك كتم
        # -----------------------------

        elif text == "فك كتم":

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
                user.id,
                permissions=permissions
            )

            await message.reply_text(
                f"🔊 تم فك كتم {user.mention}"
            )

    except Exception as e:

        await message.reply_text(
            "❌ الأمر فشل:\n\n"
            f"`{str(e)[:600]}`"
        )


# =========================================================
# WARNINGS
# =========================================================

@bot.on_message(
    filters.group & filters.text,
    group=9
)
async def warnings_handler(
    _,
    message
):

    text = message.text.strip()

    if text not in (
        "تحذير",
        "تحذيرات",
        "مسح تحذيرات",
    ):
        return

    if not await require_admin(
        message
    ):
        return

    user = await get_target_user(
        message
    )

    if not user:

        await message.reply_text(
            "❌ اعمل Reply على الشخص."
        )

        return

    chat_key = str(
        message.chat.id
    )

    user_key = str(
        user.id
    )

    warnings.setdefault(
        chat_key,
        {}
    )

    if text == "تحذير":

        count = (
            warnings[
                chat_key
            ].get(
                user_key,
                0
            ) + 1
        )

        warnings[
            chat_key
        ][user_key] = count

        save_json(
            WARN_FILE,
            warnings
        )

        await message.reply_text(
            f"⚠️ تحذير لـ {user.mention}\n"
            f"📊 التحذيرات: {count}"
        )

    elif text == "تحذيرات":

        count = warnings[
            chat_key
        ].get(
            user_key,
            0
        )

        await message.reply_text(
            f"⚠️ تحذيرات {user.mention}: "
            f"{count}"
        )

    else:

        warnings[
            chat_key
        ].pop(
            user_key,
            None
        )

        save_json(
            WARN_FILE,
            warnings
        )

        await message.reply_text(
            f"✅ تم مسح تحذيرات {user.mention}"
        )


# =========================================================
# PIN
# =========================================================

@bot.on_message(
    filters.group & filters.text,
    group=10
)
async def pin_handler(
    _,
    message
):

    text = message.text.strip()

    if text not in (
        "تثبيت",
        "إلغاء تثبيت",
    ):
        return

    if not await require_admin(
        message
    ):
        return

    try:

        if text == "تثبيت":

            if not message.reply_to_message:

                await message.reply_text(
                    "❌ اعمل Reply على الرسالة."
                )

                return

            await bot.pin_chat_message(
                message.chat.id,
                message.reply_to_message.id,
                disable_notification=True
            )

            await message.reply_text(
                "📌 تم التثبيت."
            )

        else:

            await bot.unpin_chat_message(
                message.chat.id
            )

            await message.reply_text(
                "📌 تم إلغاء التثبيت."
            )

    except Exception as e:

        await message.reply_text(
            f"❌ {str(e)[:400]}"
        )


# =========================================================
# WELCOME
# =========================================================

@bot.on_message(
    filters.new_chat_members
)
async def welcome(
    _,
    message
):

    if not await enabled(message):
        return

    for user in message.new_chat_members:

        if user.is_bot:
            continue

        await message.reply_text(
            "👋 أهلاً وسهلاً "
            f"{user.mention} ❤️\n\n"
            "🌷 نورت المجموعة"
        )


# =========================================================
# HELP
# =========================================================

@bot.on_message(
    filters.group & filters.text,
    group=11
)
async def help_command(
    _,
    message
):

    if message.text.strip() != "مساعدة":
        return

    await message.reply_text(

        "📖 **أوامر مريومه الدلوعه**\n\n"

        "🎵 **الميوزك**\n"
        "• تشغيل\n"
        "• تشغيل اسم الأغنية\n"
        "• تخطي\n"
        "• وقف\n"
        "• إيقاف\n"
        "• القائمة\n\n"

        "🤖 **الردود التلقائية**\n"
        "• اضف رد الكلمة = الرد\n"
        "• مسح رد الكلمة\n"
        "• حتى 500 رد لكل مجموعة\n\n"

        "👑 **الإدارة**\n"
        "• رتبتي\n"
        "• المالك\n"
        "• المشرفين\n"
        "• ترقية\n"
        "• تنزيل\n"
        "• طرد\n"
        "• حظر\n"
        "• فك حظر\n"
        "• كتم\n"
        "• فك كتم\n\n"

        "⚠️ **التحذيرات**\n"
        "• تحذير\n"
        "• تحذيرات\n"
        "• مسح تحذيرات\n\n"

        "📌 **التثبيت**\n"
        "• تثبيت\n"
        "• إلغاء تثبيت\n\n"

        "🛡️ **الحماية**\n"
        "• قفل الروابط\n"
        "• فتح الروابط\n"
        "• قفل الصور\n"
        "• فتح الصور\n"
        "• قفل الفيديو\n"
        "• فتح الفيديو\n"
        "• قفل الملصقات\n"
        "• فتح الملصقات\n"
        "• قفل الصوت\n"
        "• فتح الصوت\n"
        "• قفل السب\n"
        "• فتح السب\n\n"

        "⚙️ **التحكم**\n"
        "• تفعيل البوت\n"
        "• تعطيل البوت"
    )


# =========================================================
# START
# =========================================================

@bot.on_message(
    filters.command("start")
)
async def start_command(
    _,
    message
):

    await message.reply_text(

        "🎀 أهلاً بيك في "
        "مريومه الدلوعه ❤️\n\n"

        "🎵 لتشغيل أغنية:\n"
        "`تشغيل`\n\n"

        "🤖 لإضافة رد:\n"
        "`اضف رد الكلمة = الرد`\n\n"

        "📖 لمعرفة الأوامر:\n"
        "`مساعدة`"
    )


# =========================================================
# MAIN
# =========================================================

async def main():

    global calls

    print("================================")
    print("Starting MariamMusicBot...")
    print("================================")

    # البوت
    await bot.start()

    print("✅ Bot started")

    # حساب المساعد
    await assistant.start()

    print("✅ Assistant started")

    # مهم جداً:
    # إنشاء PyTgCalls بعد دخول asyncio.run()
    calls = PyTgCalls(
        assistant
    )

    # تشغيل PyTgCalls
    calls.start()

    print("✅ PyTgCalls started")
    print("================================")
    print("🎵 Music: ON")
    print("👑 Admin: ON")
    print("🛡️ Protection: ON")
    print("🤖 Auto replies: ON")
    print("================================")

    # إبقاء البرنامج شغال
    await asyncio.Event().wait()


if __name__ == "__main__":

    asyncio.run(
        main()
    )
