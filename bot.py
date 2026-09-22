import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())

import os
import static_ffmpeg
import yt_dlp
import pyrogram.errors

static_ffmpeg.add_paths()


# =========================
# PyTgCalls Compatibility
# =========================

if not hasattr(pyrogram.errors, "GroupcallForbidden"):
    if hasattr(pyrogram.errors, "GroupCallForbidden"):
        pyrogram.errors.GroupcallForbidden = pyrogram.errors.GroupCallForbidden
    else:
        class GroupcallForbidden(Exception):
            pass

        pyrogram.errors.GroupcallForbidden = GroupcallForbidden


if not hasattr(pyrogram.errors, "GroupcallInvalid"):
    if hasattr(pyrogram.errors, "GroupCallInvalid"):
        pyrogram.errors.GroupcallInvalid = pyrogram.errors.GroupCallInvalid
    else:
        class GroupcallInvalid(Exception):
            pass

        pyrogram.errors.GroupcallInvalid = GroupcallInvalid


from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from pytgcalls import PyTgCalls
from pytgcalls.types import (
    MediaStream,
    GroupCallConfig
)


# =========================
# Railway Variables
# =========================

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
SESSION_STRING = os.environ["SESSION_STRING"]


# =========================
# Settings
# =========================

REQUIRED_CHAT = "@mariamqueennuriii"

REQUIRED_CHAT_LINK = (
    "https://t.me/mariamqueennuriii"
)

PHOTO_PATH = (
    "IMG_20260922_130735_050.jpg"
)


# =========================
# Bot
# =========================

bot = Client(
    "MariamMusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)


# =========================
# Assistant
# =========================

assistant = Client(
    "MariamMusicAssistant",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)


calls = PyTgCalls(assistant)


# =========================
# Data
# =========================

queues = {}

playing = {}

waiting_for_song = {}

paused = {}


# =========================
# Check Subscription
# =========================

async def is_user_joined(user_id):

    try:

        member = await bot.get_chat_member(
            REQUIRED_CHAT,
            user_id
        )

        status = str(
            member.status
        ).lower()


        if status in (
            "member",
            "administrator",
            "owner"
        ):

            return True


        if status == "restricted":

            return bool(
                getattr(
                    member,
                    "is_member",
                    False
                )
            )


        return False


    except Exception as e:

        print(
            "CHECK ERROR:",
            repr(e)
        )

        return False


# =========================
# Join Message
# =========================

async def send_join_message(message):

    try:

        me = await bot.get_me()

        username = (
            me.username
            or "MariamMusicBot"
        )

    except Exception:

        username = "MariamMusicBot"


    add_bot_link = (
        f"https://t.me/{username}"
        f"?startgroup=musicbot"
    )


    keyboard = InlineKeyboardMarkup(
        [

            [

                InlineKeyboardButton(
                    "➕ أضفني لمجموعتك",
                    url=add_bot_link
                )

            ],

            [

                InlineKeyboardButton(
                    "📢 انضم للمجموعة",
                    url=REQUIRED_CHAT_LINK
                )

            ],

            [

                InlineKeyboardButton(
                    "✅ تحقق",
                    callback_data="check_join"
                )

            ]

        ]
    )


    await message.reply_text(

        "🎵 <b>مريومه الدلوعه</b>\n\n"

        "لاستخدام البوت:\n\n"

        "1️⃣ أضفني لمجموعتك.\n"
        "2️⃣ انضم للمجموعة المطلوبة.\n"
        "3️⃣ اضغط على «✅ تحقق».\n\n"

        "بعد التحقق تقدر تستخدم البوت.",

        reply_markup=keyboard

    )


# =========================
# Search Song
# =========================

async def search_song(name):

    options = {

        "quiet": True,

        "no_warnings": True,

        "extract_flat": True,

    }


    try:

        with yt_dlp.YoutubeDL(
            options
        ) as
