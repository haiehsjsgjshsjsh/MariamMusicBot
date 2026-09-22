import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())

import os
import yt_dlp
import pyrogram.errors

# حل توافق PyTgCalls مع Pyrogram
if not hasattr(pyrogram.errors, "GroupcallForbidden"):
    if hasattr(pyrogram.errors, "GroupCallForbidden"):
        pyrogram.errors.GroupcallForbidden = pyrogram.errors.GroupCallForbidden
    else:
        class GroupcallForbidden(Exception):
            pass

        pyrogram.errors.GroupcallForbidden = GroupcallForbidden


from pyrogram import Client, filters
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream


API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
SESSION_STRING = os.environ["SESSION_STRING"]


# البوت
bot = Client(
    "MariamMusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)


# الحساب المساعد
assistant = Client(
    "MariamMusicAssistant",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)


calls = PyTgCalls(assistant)


queues = {}
playing = {}
waiting_for_song = {}


# =========================
# البحث عن الأغنية - SoundCloud
# =========================

async def search_song(name):

    options = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
    }

    try:

        with yt_dlp.YoutubeDL(options) as ydl:

            info = await asyncio.to_thread(
                ydl.extract_info,
                f"scsearch1:{name}",
                False
            )

        if not info or not info.get("entries"):
            return None

        song = info["entries"][0]

        return {
            "title": song.get("title", "أغنية"),
            "url": song.get("webpage_url") or song.get("url"),
        }

    except Exception as e:

        print("SEARCH ERROR:", repr(e))

        return None


# =========================
# استخراج رابط الصوت
# =========================

async def get_audio(url):

    options = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
    }

    with yt_dlp.YoutubeDL(options) as ydl:

        info = await asyncio.to_thread(
            ydl.extract_info,
            url,
            False
        )

    return info["url"]


# =========================
# تشغيل الأغنية
# =========================

async def play_song(chat_id, song):

    try:

        audio_url = await get_audio(song["url"])

        await calls.play(
            chat_id,
            MediaStream(
                audio_url,
                video_flags=MediaStream.Flags.IGNORE
            )
        )

        playing[chat_id] = song

        await bot.send_message(
            chat_id,
            f"🎵 دلوقتي شغال:\n{song['title']}"
        )

    except Exception as e:

        print("PLAY ERROR:", repr(e))

        await bot.send_message(
            chat_id,
            "❌ مش قادر أشغل الأغنية.\n"
            "اتأكد إن الكول شغال."
        )


# =========================
# أمر تشغيل
# =========================

@bot.on_message(
    filters.group & filters.regex(r"^تشغيل$")
)
async def start_play(client, message):

    chat_id = message.chat.id

    waiting_for_song[chat_id] = True

    await message.reply_text(
        "🎵 قول اسم الأغنية"
    )


# =========================
# استقبال اسم الأغنية
# =========================

@bot.on_message(
    filters.group & filters.text
)
async def song_handler(client, message):

    chat_id = message.chat.id
    text = message.text.strip()

    if text in [
        "تشغيل",
        "تخطي",
        "وقف",
        "إيقاف",
        "استكمال",
        "القائمة"
    ]:
        return

    if not waiting_for_song.get(chat_id):
        return

    waiting_for_song[chat_id] = False

    song = await search_song(text)

    if not song:

        await message.reply_text(
            "❌ ملقتش الأغنية دي."
        )

        return


    if chat_id not in queues:
        queues[chat_id] = []


    # لو فيه أغنية شغالة
    if chat_id in playing:

        queues[chat_id].append(song)

        await message.reply_text(
            f"✅ اتضافت للقائمة:\n"
            f"{song['title']}"
        )

    else:

        await play_song(
            chat_id,
            song
        )


# =========================
# تخطي
# =========================

@bot.on_message(
    filters.group & filters.regex(r"^تخطي$")
)
async def skip_song(client, message):

    chat_id = message.chat.id

    if chat_id not in playing:

        await message.reply_text(
            "❌ مفيش أغنية شغالة."
        )

        return


    try:

        await calls.leave_call(chat_id)

    except Exception:

        pass


    playing.pop(chat_id, None)


    if queues.get(chat_id):

        next_song = queues[chat_id].pop(0)

        await play_song(
            chat_id,
            next_song
        )

    else:

        await message.reply_text(
            "⏭️ تم التخطي.\n"
            "مفيش أغاني تانية في القائمة."
        )


# =========================
# إيقاف
# =========================

@bot.on_message(
    filters.group & filters.regex(r"^(وقف|إيقاف)$")
)
async def stop_song(client, message):

    chat_id = message.chat.id

    try:

        await calls.leave_call(chat_id)

    except Exception:

        pass


    playing.pop(chat_id, None)

    queues[chat_id] = []

    waiting_for_song[chat_id] = False


    await message.reply_text(
        "⏹️ تم إيقاف الأغاني."
    )


# =========================
# القائمة
# =========================

@bot.on_message(
    filters.group & filters.regex(r"^القائمة$")
)
async def show_queue(client, message):

    chat_id = message.chat.id

    queue = queues.get(
        chat_id,
        []
    )


    if not queue:

        await message.reply_text(
            "📋 القائمة فاضية."
        )

        return


    text = "📋 قائمة الأغاني:\n\n"


    for i, song in enumerate(
        queue,
        1
    ):

        text += (
            f"{i}. "
            f"{song['title']}\n"
        )


    await message.reply_text(
        text
    )


# =========================
# تشغيل البوت
# =========================

print(
    "🎵 Mariam Music Bot Started..."
)


calls.start()

bot.run()
