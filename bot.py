import os
import json
import asyncio
import random
from collections import defaultdict, deque

import yt_dlp

from pyrogram import Client, filters, idle
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from pytgcalls import PyTgCalls
from pytgcalls import filters as call_filters
from pytgcalls.types import MediaStream
from pytgcalls.types import AudioQuality
from pytgcalls.types import StreamEnded


# =========================================================
# الإعدادات
# =========================================================

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")

DATA_FILE = "bot_data.json"

CHANNEL_USERNAME = "mariamqueennuriii"


# =========================================================
# التأكد من البيانات
# =========================================================

if API_ID == 0:
    raise RuntimeError("API_ID غير موجود")

if not API_HASH:
    raise RuntimeError("API_HASH غير موجود")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN غير موجود")

if not SESSION_STRING:
    raise RuntimeError(
        "SESSION_STRING غير موجود"
    )


# =========================================================
# Bot
# =========================================================

bot = Client(
    "MariamMusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)


# =========================================================
# حساب تشغيل الموسيقى
# =========================================================

music_user = Client(
    "MariamMusicUser",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
)


# =========================================================
# PyTgCalls
# =========================================================

call = PyTgCalls(music_user)


# =========================================================
# بيانات الموسيقى
# =========================================================

queues = defaultdict(deque)

current_song = {}

playing = set()


# =========================================================
# إعدادات الجروبات
# =========================================================

enabled_chats = defaultdict(lambda: True)

anti_bad_words = defaultdict(lambda: True)


# =========================================================
# الردود التلقائية
# =========================================================

custom_replies = {}


# =========================================================
# كلمات ممنوعة
# =========================================================

BAD_WORDS = {
    "شتيمة",
    "شتيمه",
    "حمار",
    "حيوان",
    "غبي",
    "غبية",
}


# =========================================================
# الألعاب
# =========================================================

GAMES = [
    "حجر ورق مقص",
    "XO",
    "تخمين الرقم",
    "صح أو خطأ",
    "سؤال وجواب",
    "حظك اليوم",
    "نرد",
    "عملة",
    "لغز",
    "ألغاز",
    "تحدي",
    "صراحة",
    "جرأة",
    "مين الأكثر",
    "خمن الكلمة",
    "خمن الحيوان",
    "خمن الدولة",
    "خمن اللاعب",
    "خمن الأغنية",
    "خمن الفيلم",
    "معلومات عامة",
    "ثقافة عامة",
    "رياضيات",
    "حساب سريع",
    "اختبار الذكاء",
    "اختبار التركيز",
    "اختيار عشوائي",
    "نعم أو لا",
    "يمين أو شمال",
    "بحر أو بر",
    "ليل أو نهار",
    "صيف أو شتاء",
    "قهوة أو شاي",
    "قطط أو كلاب",
    "كرة القدم",
    "توقع النتيجة",
    "توقع الفائز",
    "السيارات",
    "تحدي السيارات",
    "BMW أو Mercedes",
    "سباق",
    "سباق أرقام",
    "سباق كلمات",
    "كلمة السر",
    "الحرف الناقص",
    "أكمل الجملة",
    "أكمل المثل",
    "من القاتل",
    "المحقق",
    "الجاسوس",
    "العميل السري",
    "المغامرة",
    "الهروب",
    "الكنز",
    "صيد الكنز",
    "المتاهة",
    "الزومبي",
    "المحارب",
    "الساحر",
    "الملك",
    "الأميرة",
]


# =========================================================
# تحميل البيانات
# =========================================================

def load_data():

    global custom_replies

    if not os.path.exists(DATA_FILE):
        return

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        custom_replies = data.get(
            "custom_replies",
            {}
        )

    except Exception as error:

        print(
            "LOAD DATA ERROR:",
            repr(error)
        )


# =========================================================
# حفظ البيانات
# =========================================================

def save_data():

    try:

        data = {
            "custom_replies": custom_replies
        }

        with open(
            DATA_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2
            )

    except Exception as error:

        print(
            "SAVE DATA ERROR:",
            repr(error)
        )


# =========================================================
# التأكد من المشرف
# =========================================================

async def is_admin(message):

    if not message.from_user:
        return False

    try:

        member = await bot.get_chat_member(
            message.chat.id,
            message.from_user.id
        )

        return member.status in (
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR
        )

    except Exception as error:

        print(
            "ADMIN CHECK ERROR:",
            repr(error)
        )

        return False


# =========================================================
# START
# =========================================================

@bot.on_message(
    filters.private &
    filters.command("start")
)
async def start_handler(
    client,
    message
):

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📢 الاشتراك",
                    url="https://t.me/mariamqueennuriii"
                )
            ]
        ]
    )

    await message.reply_text(
        "👋 أهلاً بيك في MariamMusicBot ❤️\n\n"
        "🎵 بوت الموسيقى والإدارة والألعاب.\n\n"
        "📌 لإضافة البوت للجروب وتشغيل الموسيقى "
        "استخدم الأوامر الموجودة داخل الجروب.\n\n"
        "اضغط الزر للاشتراك:",
        reply_markup=keyboard
    )


# =========================================================
# الأوامر
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^الأوامر$")
)
async def commands_handler(
    client,
    message
):

    text = """
╭──── 🎵 MariamMusicBot ────╮

🎵 الموسيقى

• تشغيل
• تشغيل اسم الأغنية
• تخطي
• إيقاف
• وقف
• الأغنية
• الطابور

👑 الإدارة

• طرد
• ترقية
• تنزيل رتبة
• تفعيل البوت
• تعطيل البوت

🛡 الحماية

• منع السب
• السماح بالسب

💬 الردود

• اضف رد الكلمة الرد
• مسح الرد الكلمة

🎮 الألعاب

• العاب
• نرد
• عملة
• حظك اليوم

╰────────────────────────╯
"""

    await message.reply_text(text)


# =========================================================
# تفعيل البوت
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^(تفعيل البوت|تفعيل)$")
)
async def enable_handler(
    client,
    message
):

    if not await is_admin(message):

        await message.reply_text(
            "❌ الأمر ده للمشرفين فقط."
        )

        return

    enabled_chats[
        message.chat.id
    ] = True

    await message.reply_text(
        "✅ تم تفعيل البوت في الجروب."
    )


# =========================================================
# تعطيل البوت
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^(تعطيل البوت|تعطيل)$")
)
async def disable_handler(
    client,
    message
):

    if not await is_admin(message):

        await message.reply_text(
            "❌ الأمر ده للمشرفين فقط."
        )

        return

    enabled_chats[
        message.chat.id
    ] = False

    await message.reply_text(
        "⛔ تم تعطيل البوت في الجروب."
    )


# =========================================================
# البحث عن الأغنية
# =========================================================

def youtube_search(query):

    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }

    try:

        with yt_dlp.YoutubeDL(options) as ydl:

            result = ydl.extract_info(
                "ytsearch1:" + query,
                download=False
            )

            entries = result.get(
                "entries",
                []
            )

            if not entries:
                return None

            item = entries[0]

            return {
                "title": item.get(
                    "title",
                    "بدون اسم"
                ),
                "url": item.get(
                    "webpage_url"
                ) or item.get(
                    "original_url"
                ),
                "duration": item.get(
                    "duration"
                ),
            }

    except Exception as error:

        print(
            "YOUTUBE SEARCH ERROR:",
            repr(error)
        )

        return None


# =========================================================
# تشغيل أغنية
# =========================================================

async def play_song(
    chat_id,
    song
):

    try:

        stream = MediaStream(
            song["url"],
            AudioQuality.HIGH,
        )

        await call.play(
            chat_id,
            stream
        )

        current_song[
            chat_id
        ] = song

        playing.add(
            chat_id
        )

        return True

    except Exception as error:

        print(
            "PLAY ERROR:",
            repr(error)
        )

        return False


# =========================================================
# تشغيل التالية
# =========================================================

async def play_next(chat_id):

    if not queues[chat_id]:

        current_song.pop(
            chat_id,
            None
        )

        playing.discard(
            chat_id
        )

        return

    song = queues[
        chat_id
    ].popleft()

    success = await play_song(
        chat_id,
        song
    )

    if not success:

        await bot.send_message(
            chat_id,
            "❌ حصل خطأ أثناء تشغيل الأغنية."
        )

        await play_next(
            chat_id
        )

        return

    await bot.send_message(
        chat_id,
        "🎵 الآن تعمل:\n\n"
        f"🎶 {song['title']}\n\n"
        "▶️ استمتعوا ❤️"
    )


# =========================================================
# تشغيل
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^تشغيل(?:\s+(.+))?$")
)
async def play_handler(
    client,
    message
):

    chat_id = message.chat.id

    if not enabled_chats[chat_id]:
        return

    text = message.text.strip()

    if text == "تشغيل":

        await message.reply_text(
            "🎵 قول اسم الأغنية الأول.\n\n"
            "مثال:\n"
            "تشغيل مخصماك"
        )

        return

    query = text[
        len("تشغيل"):
    ].strip()

    if not query:

        await message.reply_text(
            "❌ اكتب اسم الأغنية."
        )

        return

    searching = await message.reply_text(
        f"🔎 بدور على:\n{query}"
    )

    song = await asyncio.to_thread(
        youtube_search,
        query
    )

    if not song:

        await searching.edit_text(
            "❌ مش لاقي الأغنية."
        )

        return

    queues[
        chat_id
    ].append(song)

    await searching.edit_text(
        "✅ تم العثور على الأغنية:\n\n"
        f"🎵 {song['title']}"
    )

    if chat_id not in playing:

        await play_next(
            chat_id
        )

    else:

        await message.reply_text(
            "➕ تمت إضافة الأغنية للطابور."
        )


# =========================================================
# تخطي
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^تخطي$")
)
async def skip_handler(
    client,
    message
):

    chat_id = message.chat.id

    if chat_id not in playing:

        await message.reply_text(
            "❌ مفيش أغنية شغالة."
        )

        return

    try:

        await call.leave_call(
            chat_id
        )

    except Exception as error:

        print(
            "SKIP ERROR:",
            repr(error)
        )

    current_song.pop(
        chat_id,
        None
    )

    playing.discard(
        chat_id
    )

    await message.reply_text(
        "⏭️ تم تخطي الأغنية."
    )

    await asyncio.sleep(1)

    await play_next(
        chat_id
    )


# =========================================================
# إيقاف
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(
        r"^(إيقاف|وقف|وقف التشغيل)$"
    )
)
async def stop_handler(
    client,
    message
):

    chat_id = message.chat.id

    try:

        await call.leave_call(
            chat_id
        )

    except Exception as error:

        print(
            "STOP ERROR:",
            repr(error)
        )

    queues[
        chat_id
    ].clear()

    current_song.pop(
        chat_id,
        None
    )

    playing.discard(
        chat_id
    )

    await message.reply_text(
        "⏹️ تم إيقاف التشغيل وإفراغ الطابور."
    )


# =========================================================
# الأغنية الحالية
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^(الأغنية|الاغنية)$")
)
async def now_playing(
    client,
    message
):

    song = current_song.get(
        message.chat.id
    )

    if not song:

        await message.reply_text(
            "❌ مفيش أغنية شغالة."
        )

        return

    await message.reply_text(
        "🎵 الأغنية الحالية:\n\n"
        f"🎶 {song['title']}"
    )


# =========================================================
# الطابور
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^الطابور$")
)
async def queue_handler(
    client,
    message
):

    chat_id = message.chat.id

    text = "📋 طابور الأغاني:\n\n"

    current = current_song.get(
        chat_id
    )

    if current:

        text += (
            "▶️ تعمل الآن:\n"
            f"🎵 {current['title']}\n\n"
        )

    songs = list(
        queues[chat_id]
    )

    if not songs:

        text += (
            "📭 مفيش أغاني في الانتظار."
        )

    else:

        for index, song in enumerate(
            songs,
            1
        ):

            text += (
                f"{index}. "
                f"{song['title']}\n"
            )

    await message.reply_text(
        text
    )


# =========================================================
# انتهاء الأغنية
# =========================================================

@call.on_update(
    call_filters.stream_end()
)
async def stream_end_handler(
    _,
    update: StreamEnded
):

    chat_id = update.chat_id

    current_song.pop(
        chat_id,
        None
    )

    playing.discard(
        chat_id
    )

    await play_next(
        chat_id
    )


# =========================================================
# إضافة رد
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^اضف رد ")
)
async def add_reply_handler(
    client,
    message
):

    if not await is_admin(message):

        await message.reply_text(
            "❌ الأمر ده للمشرفين فقط."
        )

        return

    parts = message.text.split(
        maxsplit=2
    )

    if len(parts) < 3:

        await message.reply_text(
            "❌ الاستخدام:\n"
            "اضف رد الكلمة الرد"
        )

        return

    keyword = parts[1].strip().lower()

    reply = parts[2].strip()

    custom_replies[
        keyword
    ] = reply

    save_data()

    await message.reply_text(
        "✅ تم إضافة الرد.\n\n"
        f"🔤 الكلمة: {keyword}\n"
        f"💬 الرد: {reply}"
    )


# =========================================================
# مسح رد
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^مسح الرد ")
)
async def delete_reply_handler(
    client,
    message
):

    if not await is_admin(message):

        await message.reply_text(
            "❌ الأمر ده للمشرفين فقط."
        )

        return

    parts = message.text.split(
        maxsplit=2
    )

    if len(parts) < 3:

        await message.reply_text(
            "❌ الاستخدام:\n"
            "مسح الرد الكلمة"
        )

        return

    keyword = parts[2].strip().lower()

    if keyword not in custom_replies:

        await message.reply_text(
            "❌ الرد غير موجود."
        )

        return

    del custom_replies[
        keyword
    ]

    save_data()

    await message.reply_text(
        "✅ تم مسح الرد."
    )


# =========================================================
# منع السب
# =========================================================

@bot.on_message(
    filters.group &
    filters.text,
    group=20
)
async def protection_handler(
    client,
    message
):

    chat_id = message.chat.id

    if not enabled_chats[chat_id]:
        return

    if not anti_bad_words[chat_id]:
        return

    if not message.text:
        return

    text = message.text.lower()

    for word in BAD_WORDS:

        if word in text:

            try:

                await message.delete()

            except Exception:
                pass

            return


# =========================================================
# تفعيل منع السب
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^منع السب$")
)
async def anti_bad_on(
    client,
    message
):

    if not await is_admin(message):
        return

    anti_bad_words[
        message.chat.id
    ] = True

    await message.reply_text(
        "🛡️ تم تفعيل منع السب."
    )


# =========================================================
# السماح بالسب
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^السماح بالسب$")
)
async def anti_bad_off(
    client,
    message
):

    if not await is_admin(message):
        return

    anti_bad_words[
        message.chat.id
    ] = False

    await message.reply_text(
        "⚠️ تم تعطيل منع السب."
    )


# =========================================================
# طرد
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^طرد$")
)
async def kick_handler(
    client,
    message
):

    if not await is_admin(message):

        await message.reply_text(
            "❌ الأمر للمشرفين فقط."
        )

        return

    if not message.reply_to_message:

        await message.reply_text(
            "↩️ اعمل رد على رسالة الشخص واكتب:\n"
            "طرد"
        )

        return

    user = (
        message.reply_to_message
        .from_user
    )

    try:

        await bot.ban_chat_member(
            message.chat.id,
            user.id
        )

        await bot.unban_chat_member(
            message.chat.id,
            user.id
        )

        await message.reply_text(
            f"🚫 تم طرد {user.mention}"
        )

    except Exception as error:

        print(
            "KICK ERROR:",
            repr(error)
        )

        await message.reply_text(
            "❌ مقدرتش أطرد العضو.\n"
            "تأكد إن البوت مشرف وعنده صلاحية الحظر."
        )


# =========================================================
# ترقية
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^ترقية$")
)
async def promote_handler(
    client,
    message
):

    if not await is_admin(message):
        return

    if not message.reply_to_message:

        await message.reply_text(
            "↩️ اعمل رد على رسالة الشخص واكتب:\n"
            "ترقية"
        )

        return

    user = (
        message.reply_to_message
        .from_user
    )

    try:

        await bot.promote_chat_member(
            message.chat.id,
            user.id,
            can_manage_chat=True,
            can_delete_messages=True,
            can_restrict_members=True,
            can_invite_users=True,
            can_pin_messages=True,
            can_manage_video_chats=True
        )

        await message.reply_text(
            f"👑 تمت ترقية {user.mention}"
        )

    except Exception as error:

        print(
            "PROMOTE ERROR:",
            repr(error)
        )

        await message.reply_text(
            "❌ مقدرتش أرقي العضو."
        )


# =========================================================
# تنزيل رتبة
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(
        r"^(تنزيل رتبة|تنزيل)$"
    )
)
async def demote_handler(
    client,
    message
):

    if not await is_admin(message):
        return

    if not message.reply_to_message:

        await message.reply_text(
            "↩️ اعمل رد على رسالة الشخص واكتب:\n"
            "تنزيل رتبة"
        )

        return

    user = (
        message.reply_to_message
        .from_user
    )

    try:

        await bot.promote_chat_member(
            message.chat.id,
            user.id,
            can_manage_chat=False,
            can_delete_messages=False,
            can_restrict_members=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_manage_video_chats=False
        )

        await message.reply_text(
            f"📉 تم تنزيل رتبة {user.mention}"
        )

    except Exception as error:

        print(
            "DEMOTE ERROR:",
            repr(error)
        )

        await message.reply_text(
            "❌ مقدرتش أنزل الرتبة."
        )


# =========================================================
# الألعاب
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^العاب$")
)
async def games_handler(
    client,
    message
):

    text = "🎮 الألعاب المتاحة:\n\n"

    for index, game in enumerate(
        GAMES,
        1
    ):

        text += (
            f"{index}. {game}\n"
        )

    await message.reply_text(
        text
    )


# =========================================================
# نرد
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^نرد$")
)
async def dice_handler(
    client,
    message
):

    number = random.randint(
        1,
        6
    )

    await message.reply_text(
        f"🎲 النتيجة: {number}"
    )


# =========================================================
# عملة
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(
        r"^(عملة|عملة معدنية)$"
    )
)
async def coin_handler(
    client,
    message
):

    result = random.choice(
        [
            "وجه 🪙",
            "كتابة 🪙"
        ]
    )

    await message.reply_text(
        f"🪙 النتيجة: {result}"
    )


# =========================================================
# حظك اليوم
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^حظك اليوم$")
)
async def luck_handler(
    client,
    message
):

    number = random.randint(
        1,
        100
    )

    await message.reply_text(
        f"🍀 نسبة حظك اليوم: {number}%"
    )


# =========================================================
# الردود التلقائية
# =========================================================

@bot.on_message(
    filters.group &
    filters.text,
    group=50
)
async def custom_reply_handler(
    client,
    message
):

    if not message.text:
        return

    chat_id = message.chat.id

    if not enabled_chats[chat_id]:
        return

    key = message.text.strip().lower()

    if key in custom_replies:

        try:

            await message.reply_text(
                custom_replies[key]
            )

        except Exception as error:

            print(
                "CUSTOM REPLY ERROR:",
                repr(error)
            )


# =========================================================
# الترحيب
# =========================================================

@bot.on_message(
    filters.group &
    filters.new_chat_members
)
async def welcome_handler(
    client,
    message
):

    if not enabled_chats[
        message.chat.id
    ]:
        return

    for user in message.new_chat_members:

        if user.is_bot:
            continue

        await message.reply_text(
            f"👋 أهلاً {user.mention}\n\n"
            "💜 نورت المجموعة.\n"
            "🎵 استمتعوا مع MariamMusicBot ❤️"
        )


# =========================================================
# MAIN
# =========================================================

async def main():

    print(
        "================================"
    )

    print(
        "MariamMusicBot starting..."
    )

    print(
        "================================"
    )

    load_data()

    # ---------------------------------
    # تشغيل البوت
    # ---------------------------------

    await bot.start()

    print(
        "✅ Bot connected."
    )

    # ---------------------------------
    # تشغيل حساب الموسيقى
    # ---------------------------------

    await music_user.start()

    print(
        "✅ Music account connected."
    )

    # ---------------------------------
    # تشغيل PyTgCalls
    # ---------------------------------

    await call.start()

    print(
        "✅ PyTgCalls started."
    )

    # ---------------------------------
    # بيانات البوت
    # ---------------------------------

    me = await bot.get_me()

    print(
        f"🤖 Bot: @{me.username}"
    )

    print(
        "================================"
    )

    print(
        "MariamMusicBot is ONLINE"
    )

    print(
        "================================"
    )

    # ---------------------------------
    # الانتظار
    # ---------------------------------

    await idle()

    # ---------------------------------
    # إيقاف
    # ---------------------------------

    print(
        "Stopping..."
    )

    try:

        await call.stop()

    except Exception as error:

        print(
            "CALL STOP ERROR:",
            repr(error)
        )

    try:

        await music_user.stop()

    except Exception as error:

        print(
            "MUSIC USER STOP ERROR:",
            repr(error)
        )

    try:

        await bot.stop()

    except Exception as error:

        print(
            "BOT STOP ERROR:",
            repr(error)
        )


# =========================================================
# START PROGRAM
# =========================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )
