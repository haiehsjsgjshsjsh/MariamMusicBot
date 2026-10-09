import os
import re
import asyncio
from typing import Dict, List

import yt_dlp

from pyrogram import Client, filters
from pyrogram.types import Message

from pytgcalls import PyTgCalls
from pytgcalls import idle
from pytgcalls.types import MediaStream
from pytgcalls.types import AudioQuality, VideoQuality


# =========================================================
#                 إعدادات البوت
# =========================================================

API_ID = 123456789
API_HASH = "PUT_API_HASH_HERE"

BOT_TOKEN = "PUT_BOT_TOKEN_HERE"

# Session String للحساب المساعد
ASSISTANT_SESSION = "PUT_ASSISTANT_SESSION_STRING_HERE"


# =========================================================
#                 ملف YouTube Cookies
# =========================================================

COOKIES_FILE = "cookies.txt"


# =========================================================
#                 إنشاء العملاء
# =========================================================

bot = Client(
    "MariamMusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

assistant = Client(
    "MariamAssistant",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=ASSISTANT_SESSION
)

call = PyTgCalls(assistant)


# =========================================================
#                 بيانات التشغيل
# =========================================================

queues: Dict[int, List[dict]] = {}
current_song: Dict[int, dict] = {}
active_chats = set()

playing_lock = {}


# =========================================================
#                 التأكد من وجود Cookies
# =========================================================

def cookies_available():
    return os.path.isfile(COOKIES_FILE)


# =========================================================
#                 تنظيف النص
# =========================================================

def clean_query(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


# =========================================================
#                 البحث في YouTube
# =========================================================

def search_youtube(query: str):

    query = clean_query(query)

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "default_search": "ytsearch1",
        "cookiefile": COOKIES_FILE,
        "nocheckcertificate": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        result = ydl.extract_info(
            f"ytsearch1:{query}",
            download=False
        )

        if not result:
            return None

        entries = result.get("entries")

        if not entries:
            return None

        video = entries[0]

        if not video:
            return None

        return {
            "title": video.get("title", "بدون عنوان"),
            "url": video.get("webpage_url"),
            "duration": video.get("duration"),
            "thumbnail": video.get("thumbnail"),
        }


# =========================================================
#                 تشغيل الأغنية
# =========================================================

async def play_song(chat_id: int, song: dict):

    if not cookies_available():
        raise Exception(
            "ملف cookies.txt غير موجود داخل المشروع."
        )

    current_song[chat_id] = song

    youtube_url = song["url"]

    # yt-dlp parameters التي سيستخدمها PyTgCalls
    ytdlp_parameters = (
        f'--cookies "{COOKIES_FILE}" '
        "--no-playlist "
        "--no-check-certificates"
    )

    stream = MediaStream(
        youtube_url,
        AudioQuality.HIGH,
        VideoQuality.HD_720p,
        ytdlp_parameters=ytdlp_parameters
    )

    await call.play(
        chat_id,
        stream
    )


# =========================================================
#                 تشغيل الأغنية التالية
# =========================================================

async def play_next(chat_id: int):

    if chat_id not in queues:
        queues[chat_id] = []

    if not queues[chat_id]:

        current_song.pop(chat_id, None)

        try:
            await call.leave_call(chat_id)
        except Exception:
            pass

        active_chats.discard(chat_id)

        return False

    song = queues[chat_id].pop(0)

    try:

        await play_song(
            chat_id,
            song
        )

        active_chats.add(chat_id)

        return True

    except Exception as e:

        print("PLAY ERROR:", repr(e))

        try:
            await bot.send_message(
                chat_id,
                "❌ حصلت مشكلة أثناء تشغيل الأغنية.\n\n"
                f"الخطأ:\n{str(e)[:700]}"
            )
        except Exception:
            pass

        return await play_next(chat_id)


# =========================================================
#                 أمر تفعيل البوت
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^(تفعيل البوت|تفعيل)$")
)
async def activate_bot(client: Client, message: Message):

    active_chats.add(message.chat.id)

    await message.reply_text(
        "✅ تم تفعيل البوت في المجموعة.\n\n"
        "🎵 اكتب:\n"
        "تشغيل + اسم الأغنية\n\n"
        "مثال:\n"
        "تشغيل عمرو دياب"
    )


# =========================================================
#                 تشغيل أغنية
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^تشغيل(?:\s+(.+))?$")
)
async def music_play(client: Client, message: Message):

    chat_id = message.chat.id

    # لو لم يتم تفعيل البوت
    if chat_id not in active_chats:

        await message.reply_text(
            "⚠️ البوت غير مفعل هنا.\n"
            "اكتب: تفعيل البوت"
        )

        return

    match = re.match(
        r"^تشغيل(?:\s+(.+))?$",
        message.text.strip()
    )

    if not match or not match.group(1):

        await message.reply_text(
            "🎵 قول اسم الأغنية الأول.\n\n"
            "مثال:\n"
            "تشغيل تملي معاك"
        )

        return

    query = clean_query(
        match.group(1)
    )

    searching = await message.reply_text(
        f"🔎 بدور على:\n{query}"
    )

    try:

        song = await asyncio.to_thread(
            search_youtube,
            query
        )

    except Exception as e:

        print("SEARCH ERROR:", repr(e))

        await searching.edit_text(
            "❌ حصل خطأ أثناء البحث في YouTube.\n\n"
            f"{str(e)[:700]}"
        )

        return

    if not song:

        await searching.edit_text(
            "❌ ملقتش الأغنية."
        )

        return

    if chat_id not in queues:
        queues[chat_id] = []

    # لو فيه أغنية شغالة
    if chat_id in current_song:

        queues[chat_id].append(song)

        position = len(queues[chat_id])

        await searching.edit_text(
            "✅ تمت إضافة الأغنية للطابور.\n\n"
            f"🎵 {song['title']}\n"
            f"📌 ترتيبها: {position}"
        )

        return

    # أول أغنية
    queues[chat_id].append(song)

    await searching.edit_text(
        "⏳ جاري تشغيل الأغنية..."
    )

    success = await play_next(chat_id)

    if success:

        await searching.edit_text(
            "▶️ بدأ التشغيل\n\n"
            f"🎵 {song['title']}\n\n"
            "⏭️ تخطي\n"
            "⏹️ إيقاف"
        )

    else:

        await searching.edit_text(
            "❌ مقدرتش أشغل الأغنية."
        )


# =========================================================
#                 تخطي
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^(تخطي|سكيب)$")
)
async def skip_song(client: Client, message: Message):

    chat_id = message.chat.id

    if chat_id not in active_chats:

        await message.reply_text(
            "⚠️ البوت غير مفعل."
        )

        return

    if chat_id not in current_song:

        await message.reply_text(
            "❌ مفيش أغنية شغالة."
        )

        return

    try:

        await call.leave_call(chat_id)

    except Exception as e:

        print("SKIP LEAVE ERROR:", repr(e))

    current_song.pop(chat_id, None)

    if chat_id not in queues:
        queues[chat_id] = []

    if queues[chat_id]:

        await message.reply_text(
            "⏭️ تم التخطي.\n"
            "▶️ جاري تشغيل الأغنية التالية..."
        )

        await play_next(chat_id)

    else:

        await message.reply_text(
            "⏭️ تم التخطي.\n"
            "❌ مفيش أغاني تانية في الطابور."
        )

        active_chats.add(chat_id)


# =========================================================
#                 إيقاف
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^(إيقاف|ايقاف|وقف)$")
)
async def stop_song(client: Client, message: Message):

    chat_id = message.chat.id

    queues[chat_id] = []

    current_song.pop(chat_id, None)

    try:

        await call.leave_call(chat_id)

    except Exception as e:

        print("STOP ERROR:", repr(e))

    await message.reply_text(
        "⏹️ تم إيقاف التشغيل.\n"
        "🗑️ تم مسح الطابور."
    )


# =========================================================
#                 الأوامر
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^(الأوامر|اوامر|/الأوامر)$")
)
async def commands_list(client: Client, message: Message):

    await message.reply_text(
        "📋 أوامر البوت\n\n"

        "🎵 الموسيقى:\n"
        "• تفعيل البوت\n"
        "• تشغيل + اسم الأغنية\n"
        "• تخطي\n"
        "• إيقاف\n\n"

        "👑 الإدارة:\n"
        "• ترقية\n"
        "• تنزيل رتبة\n"
        "• طرد\n\n"

        "💬 الردود:\n"
        "• اضف رد الكلمة الرد\n"
        "• مسح الرد الكلمة\n\n"

        "🎮 الألعاب:\n"
        "• العاب"
    )


# =========================================================
#                 حالة التشغيل
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^(الاغنية|الأغنية|الحالية|الان|الآن)$")
)
async def now_playing(client: Client, message: Message):

    chat_id = message.chat.id

    song = current_song.get(chat_id)

    if not song:

        await message.reply_text(
            "❌ مفيش أغنية شغالة حاليًا."
        )

        return

    queue_count = len(
        queues.get(chat_id, [])
    )

    await message.reply_text(
        "🎵 الأغنية الحالية\n\n"
        f"▶️ {song['title']}\n\n"
        f"📚 في الطابور: {queue_count}"
    )


# =========================================================
#                 نهاية الأغنية
# =========================================================

try:

    from pytgcalls import filters as call_filters

    @call.on_update(
        call_filters.stream_end()
    )
    async def stream_finished(_, update):

        chat_id = update.chat_id

        print(
            f"STREAM ENDED: {chat_id}"
        )

        current_song.pop(
            chat_id,
            None
        )

        await play_next(
            chat_id
        )

except Exception as e:

    print(
        "Stream end handler error:",
        repr(e)
    )


# =========================================================
#                 تشغيل البرنامج
# =========================================================

async def main():

    print(
        "================================="
    )

    print(
        "MariamMusicBot is starting..."
    )

    print(
        "================================="
    )

    if not cookies_available():

        print(
            "WARNING: cookies.txt is missing!"
        )

    await bot.start()

    await assistant.start()

    call.start()

    me = await bot.get_me()

    print(
        f"BOT ONLINE: @{me.username}"
    )

    print(
        "ASSISTANT VOICE CLIENT ONLINE"
    )

    print(
        "================================="
    )

    await idle()


if __name__ == "__main__":

    asyncio.run(
        main()
    )
