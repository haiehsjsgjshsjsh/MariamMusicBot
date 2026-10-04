import os
import re
import asyncio
import json
import time
from collections import defaultdict, deque

import yt_dlp

from pyrogram import Client, filters, idle
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from pytgcalls import PyTgCalls
from pytgcalls import filters as call_filters
from pytgcalls.types import ChatUpdate
from pytgcalls.types import StreamEnded
from pytgcalls.types import MediaStream
from pytgcalls.types import AudioQuality
from pytgcalls.types import VideoQuality


# =========================================================
# الإعدادات
# =========================================================

API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

# اسم البوت
BOT_NAME = "MariamMusicBot"

# رابط الاشتراك / التحقق
REQUIRED_CHANNEL = "mariamqueennuriii"

# ملف حفظ البيانات
DATA_FILE = "bot_data.json"


# =========================================================
# التأكد من المتغيرات
# =========================================================

if not API_ID:
    raise RuntimeError("API_ID غير موجود")

if not API_HASH:
    raise RuntimeError("API_HASH غير موجود")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN غير موجود")

if not SESSION_STRING:
    raise RuntimeError(
        "SESSION_STRING غير موجود. "
        "حساب التشغيل يحتاج Session String."
    )


# =========================================================
# البوت
# =========================================================

bot = Client(
    "mariam_music_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)


# =========================================================
# حساب تشغيل المكالمة الصوتية
# =========================================================

music_user = Client(
    "mariam_music_user",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
)


# =========================================================
# PyTgCalls
# =========================================================

call = PyTgCalls(music_user)


# =========================================================
# البيانات
# =========================================================

queues = defaultdict(deque)
current_song = {}
active_chats = set()

custom_replies = {}
anti_bad_words = True

chat_settings = defaultdict(
    lambda: {
        "enabled": True,
        "welcome": True,
    }
)


# =========================================================
# الألعاب
# =========================================================

games = [
    "حجر ورق مقص",
    "XO",
    "تخمين الرقم",
    "سؤال وجواب",
    "صح أو خطأ",
    "مين الأسرع",
    "حظك اليوم",
    "رقم الحظ",
    "عملة",
    "نرد",
    "أعلى رقم",
    "أقل رقم",
    "اختار رقم",
    "تحدي السرعة",
    "تحدي الذكاء",
    "لغز",
    "ألغاز",
    "خمن الكلمة",
    "خمن الشخصية",
    "خمن الأغنية",
    "خمن الدولة",
    "خمن الحيوان",
    "خمن الفيلم",
    "خمن اللاعب",
    "معلومات عامة",
    "ثقافة عامة",
    "رياضيات",
    "حساب سريع",
    "جمع",
    "طرح",
    "ضرب",
    "قسمة",
    "زوجي فردي",
    "الأرقام",
    "ترتيب الأرقام",
    "ذاكرة",
    "تذكر الرقم",
    "اختبار التركيز",
    "اختبار الذكاء",
    "اختبار الشخصية",
    "صراحة",
    "جرأة",
    "أسئلة محرجة",
    "مين يعرفني",
    "مين الأكثر",
    "مين أقل",
    "مين يفوز",
    "منافسة",
    "تحدي",
    "بطولة",
    "سباق",
    "سباق أرقام",
    "سباق كلمات",
    "كلمة السر",
    "الكلمة المفقودة",
    "الحرف الناقص",
    "الحروف",
    "الكلمات",
    "كلمات متقاطعة",
    "أكمل الجملة",
    "أكمل المثل",
    "الأمثال",
    "لغز اليوم",
    "لغز سريع",
    "سؤال سريع",
    "اختيار عشوائي",
    "اختار بين",
    "يمين أو شمال",
    "نعم أو لا",
    "ليل أو نهار",
    "بحر أو بر",
    "قهوة أو شاي",
    "بيتزا أو برجر",
    "قطط أو كلاب",
    "صباح أو مساء",
    "حار أو بارد",
    "صيف أو شتاء",
    "كرة القدم",
    "تحدي كرة القدم",
    "مين اللاعب",
    "مين النادي",
    "مين الهداف",
    "الدوري",
    "المباراة",
    "توقع النتيجة",
    "توقع الفائز",
    "كرة السلة",
    "التنس",
    "سباق السيارات",
    "السيارات",
    "BMW أو Mercedes",
    "اختبار السيارات",
    "تحدي السيارات",
    "اسم السيارة",
    "تخمين العمر",
    "تخمين الوزن",
    "تخمين الطول",
    "تخمين السعر",
    "السعر الأعلى",
    "السعر الأقل",
    "مزاد",
    "كنز",
    "صيد الكنز",
    "الهروب",
    "المحقق",
    "الجريمة",
    "من القاتل",
    "العميل السري",
    "الجاسوس",
    "المغامرة",
    "اختيار الطريق",
    "الجزيرة",
    "البقاء",
    "الزومبي",
    "الوحش",
    "الساحر",
    "المحارب",
    "الأميرة",
    "الملك",
    "الكنز المفقود",
    "المتاهة",
    "الباب",
    "ثلاثة أبواب",
    "صندوق الحظ",
    "صندوق المفاجأة",
]


# =========================================================
# كلمات ممنوعة
# =========================================================

BAD_WORDS = {
    "شتيمة",
    "شتيمه",
    "كلب",
    "حمار",
    "غبي",
    "غبية",
}


# =========================================================
# حفظ البيانات
# =========================================================

def load_data():
    global custom_replies

    if not os.path.exists(DATA_FILE):
        return

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        custom_replies = data.get("custom_replies", {})

    except Exception:
        custom_replies = {}


def save_data():
    try:
        data = {
            "custom_replies": custom_replies,
        }

        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2,
            )

    except Exception as e:
        print("خطأ حفظ البيانات:", e)


# =========================================================
# دالة معرفة المشرف
# =========================================================

async def is_admin(message):
    try:
        member = await bot.get_chat_member(
            message.chat.id,
            message.from_user.id,
        )

        return member.status in (
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR,
        )

    except Exception:
        return False


# =========================================================
# تفعيل البوت
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^(تفعيل البوت|تفعيل)$")
)
async def activate_bot(client, message):

    if not await is_admin(message):
        await message.reply_text(
            "❌ الأمر ده للمشرفين فقط."
        )
        return

    chat_settings[message.chat.id]["enabled"] = True

    await message.reply_text(
        "✅ تم تفعيل البوت في المجموعة."
    )


# =========================================================
# تعطيل البوت
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^(تعطيل البوت|تعطيل)$")
)
async def deactivate_bot(client, message):

    if not await is_admin(message):
        await message.reply_text(
            "❌ الأمر ده للمشرفين فقط."
        )
        return

    chat_settings[message.chat.id]["enabled"] = False

    await message.reply_text(
        "⛔ تم تعطيل البوت في المجموعة."
    )


# =========================================================
# الأوامر
# =========================================================

@bot.on_message(
    filters.command("الأوامر") |
    filters.regex(r"^الأوامر$")
)
async def commands_list(client, message):

    text = """
📋 أوامر MariamMusicBot

🎵 الموسيقى:

تشغيل
تشغيل اسم الأغنية
تخطي
إيقاف
وقف
وقف التشغيل
الأغنية
الاغنية
الطابور

👑 الإدارة:

طرد
ترقية
تنزيل رتبة
تفعيل البوت
تعطيل البوت

🛡 الحماية:

منع السب
السماح بالسب

💬 الردود:

اضف رد الكلمة الرد
مسح الرد الكلمة

🎮 الألعاب:

العاب

⚙️ عام:

الأوامر
"""

    await message.reply_text(text)


# =========================================================
# قائمة الألعاب
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^العاب$")
)
async def games_list(client, message):

    text = "🎮 قائمة الألعاب:\n\n"

    for i, game in enumerate(games, 1):
        text += f"{i}. {game}\n"

    text += (
        "\n💡 اكتب اسم اللعبة لبدء لعبة."
    )

    await message.reply_text(text)


# =========================================================
# إضافة رد
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^اضف رد ")
)
async def add_reply(client, message):

    if not await is_admin(message):
        await message.reply_text(
            "❌ الأمر ده للمشرفين فقط."
        )
        return

    text = message.text

    parts = text.split(maxsplit=2)

    if len(parts) < 3:
        await message.reply_text(
            "❌ الاستخدام:\n"
            "اضف رد الكلمة الرد"
        )
        return

    keyword = parts[1].strip().lower()
    reply = parts[2].strip()

    custom_replies[keyword] = reply

    save_data()

    await message.reply_text(
        f"✅ تم إضافة الرد للكلمة: {keyword}"
    )


# =========================================================
# مسح رد
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^مسح الرد ")
)
async def delete_reply(client, message):

    if not await is_admin(message):
        await message.reply_text(
            "❌ الأمر ده للمشرفين فقط."
        )
        return

    parts = message.text.split(maxsplit=2)

    if len(parts) < 3:
        await message.reply_text(
            "❌ الاستخدام:\n"
            "مسح الرد الكلمة"
        )
        return

    keyword = parts[2].strip().lower()

    if keyword not in custom_replies:
        await message.reply_text(
            "❌ الرد ده مش موجود."
        )
        return

    del custom_replies[keyword]

    save_data()

    await message.reply_text(
        "✅ تم حذف الرد."
    )


# =========================================================
# منع السب
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^منع السب$")
)
async def enable_bad_words(client, message):

    global anti_bad_words

    if not await is_admin(message):
        return

    anti_bad_words = True

    await message.reply_text(
        "🛡️ تم تفعيل منع السب."
    )


@bot.on_message(
    filters.group &
    filters.regex(r"^السماح بالسب$")
)
async def disable_bad_words(client, message):

    global anti_bad_words

    if not await is_admin(message):
        return

    anti_bad_words = False

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
async def kick_user(client, message):

    if not await is_admin(message):
        await message.reply_text(
            "❌ الأمر للمشرفين فقط."
        )
        return

    if not message.reply_to_message:
        await message.reply_text(
            "↩️ اعمل رد على رسالة الشخص واكتب: طرد"
        )
        return

    user = message.reply_to_message.from_user

    try:
        await bot.ban_chat_member(
            message.chat.id,
            user.id,
        )

        await bot.unban_chat_member(
            message.chat.id,
            user.id,
        )

        await message.reply_text(
            f"🚫 تم طرد {user.mention}"
        )

    except Exception as e:
        await message.reply_text(
            "❌ مقدرتش أطرد العضو.\n"
            "تأكد إن البوت عنده صلاحية الحظر."
        )


# =========================================================
# ترقية
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^ترقية$")
)
async def promote_user(client, message):

    if not await is_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "↩️ اعمل رد على رسالة الشخص واكتب: ترقية"
        )
        return

    user = message.reply_to_message.from_user

    try:
        await bot.promote_chat_member(
            message.chat.id,
            user.id,
            can_manage_chat=True,
            can_delete_messages=True,
            can_restrict_members=True,
            can_invite_users=True,
            can_pin_messages=True,
            can_manage_video_chats=True,
        )

        await message.reply_text(
            f"👑 تمت ترقية {user.mention}"
        )

    except Exception:
        await message.reply_text(
            "❌ مقدرتش أرقّيه."
        )


# =========================================================
# تنزيل رتبة
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^(تنزيل رتبة|تنزيل)$")
)
async def demote_user(client, message):

    if not await is_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "↩️ اعمل رد على رسالة الشخص واكتب: تنزيل رتبة"
        )
        return

    user = message.reply_to_message.from_user

    try:
        await bot.promote_chat_member(
            message.chat.id,
            user.id,
            can_manage_chat=False,
            can_delete_messages=False,
            can_restrict_members=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_manage_video_chats=False,
        )

        await message.reply_text(
            f"📉 تم تنزيل رتبة {user.mention}"
        )

    except Exception:
        await message.reply_text(
            "❌ مقدرتش أنزل رتبته."
        )


# =========================================================
# البحث عن أغنية
# =========================================================

def search_youtube(query):

    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(options) as ydl:

        result = ydl.extract_info(
            "ytsearch1:" + query,
            download=False,
        )

        entries = result.get("entries", [])

        if not entries:
            return None

        return entries[0]


# =========================================================
# تشغيل الأغنية
# =========================================================

async def play_song(chat_id, song):

    url = song.get("webpage_url")

    if not url:
        url = song.get("url")

    title = song.get(
        "title",
        "أغنية بدون اسم",
    )

    try:

        stream = MediaStream(
            url,
            AudioQuality.HIGH,
            VideoQuality.HD_720p,
            video_flags=MediaStream.Flags.IGNORE,
        )

        await call.play(
            chat_id,
            stream,
        )

        current_song[chat_id] = song
        active_chats.add(chat_id)

        return True

    except Exception as e:

        print(
            "PLAY ERROR:",
            repr(e),
        )

        return False


# =========================================================
# تشغيل التالي
# =========================================================

async def play_next(chat_id):

    if not queues[chat_id]:

        current_song.pop(chat_id, None)

        active_chats.discard(chat_id)

        return

    song = queues[chat_id].popleft()

    ok = await play_song(
        chat_id,
        song,
    )

    if not ok:

        await bot.send_message(
            chat_id,
            "❌ حصل خطأ أثناء تشغيل الأغنية."
        )

        await play_next(chat_id)

        return

    title = song.get(
        "title",
        "بدون اسم",
    )

    await bot.send_message(
        chat_id,
        f"🎵 الآن تعمل:\n\n"
        f"🎶 {title}\n\n"
        f"▶️ استمتعوا ❤️"
    )


# =========================================================
# تشغيل
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^تشغيل(?:\s+(.+))?$")
)
async def play_handler(client, message):

    chat_id = message.chat.id

    if not chat_settings[chat_id]["enabled"]:
        return

    match = re.match(
        r"^تشغيل(?:\s+(.+))?$",
        message.text,
    )

    if not match:
        return

    query = match.group(1)

    if not query:

        await message.reply_text(
            "🎵 قول اسم الأغنية بعد تشغيل.\n\n"
            "مثال:\n"
            "تشغيل مخصماك"
        )

        return

    searching = await message.reply_text(
        f"🔎 بدور على:\n{query}"
    )

    try:

        song = await asyncio.to_thread(
            search_youtube,
            query,
        )

    except Exception as e:

        print(
            "SEARCH ERROR:",
            repr(e),
        )

        await searching.edit_text(
            "❌ حصل خطأ في البحث عن الأغنية."
        )

        return

    if not song:

        await searching.edit_text(
            "❌ مش لاقي الأغنية."
        )

        return

    title = song.get(
        "title",
        "بدون اسم",
    )

    queues[chat_id].append(song)

    await searching.edit_text(
        f"✅ تم العثور عليها:\n"
        f"🎵 {title}"
    )

    if chat_id not in active_chats:

        await play_next(chat_id)

    else:

        await bot.send_message(
            chat_id,
            "➕ تمت إضافة الأغنية للطابور."
        )


# =========================================================
# تخطي
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^تخطي$")
)
async def skip_handler(client, message):

    chat_id = message.chat.id

    if not active_chats.__contains__(chat_id):

        await message.reply_text(
            "❌ مفيش أغنية شغالة."
        )

        return

    try:

        await call.leave_call(
            chat_id,
        )

    except Exception as e:

        print(
            "SKIP LEAVE ERROR:",
            repr(e),
        )

    current_song.pop(
        chat_id,
        None,
    )

    active_chats.discard(
        chat_id,
    )

    await message.reply_text(
        "⏭️ تم تخطي الأغنية."
    )

    await asyncio.sleep(1)

    await play_next(chat_id)


# =========================================================
# إيقاف
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^(إيقاف|وقف|وقف التشغيل)$")
)
async def stop_handler(client, message):

    chat_id = message.chat.id

    try:

        await call.leave_call(
            chat_id,
        )

    except Exception as e:

        print(
            "STOP ERROR:",
            repr(e),
        )

    queues[chat_id].clear()

    current_song.pop(
        chat_id,
        None,
    )

    active_chats.discard(
        chat_id,
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
async def now_playing(client, message):

    song = current_song.get(
        message.chat.id
    )

    if not song:

        await message.reply_text(
            "❌ مفيش أغنية شغالة."
        )

        return

    title = song.get(
        "title",
        "بدون اسم",
    )

    await message.reply_text(
        f"🎵 الأغنية الحالية:\n\n"
        f"🎶 {title}"
    )


# =========================================================
# الطابور
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^الطابور$")
)
async def queue_handler(client, message):

    chat_id = message.chat.id

    text = "📋 طابور الأغاني:\n\n"

    song = current_song.get(chat_id)

    if song:

        text += (
            "▶️ تعمل الآن:\n"
            f"🎵 {song.get('title', 'بدون اسم')}\n\n"
        )

    if not queues[chat_id]:

        text += "📭 مفيش أغاني في الانتظار."

    else:

        for i, item in enumerate(
            list(queues[chat_id]),
            1,
        ):

            text += (
                f"{i}. "
                f"{item.get('title', 'بدون اسم')}\n"
            )

    await message.reply_text(text)


# =========================================================
# انتهاء الأغنية
# =========================================================

@call.on_update(
    call_filters.stream_end()
)
async def stream_end_handler(
    _,
    update: StreamEnded,
):

    chat_id = update.chat_id

    current_song.pop(
        chat_id,
        None,
    )

    active_chats.discard(
        chat_id,
    )

    await play_next(chat_id)


# =========================================================
# خروج / طرد الحساب من المكالمة
# =========================================================

@call.on_update(
    call_filters.chat_update(
        ChatUpdate.Status.LEFT_GROUP |
        ChatUpdate.Status.KICKED,
    )
)
async def call_left_handler(
    _,
    update: ChatUpdate,
):

    chat_id = update.chat_id

    current_song.pop(
        chat_id,
        None,
    )

    active_chats.discard(
        chat_id,
    )


# =========================================================
# الردود التلقائية + الحماية
# =========================================================

@bot.on_message(
    filters.group &
    filters.text,
    group=50,
)
async def auto_reply_handler(client, message):

    if not message.text:
        return

    if not chat_settings[
        message.chat.id
    ]["enabled"]:

        return

    text = message.text.strip()

    # منع السب
    if anti_bad_words:

        lower_text = text.lower()

        for word in BAD_WORDS:

            if word in lower_text:

                try:
                    await message.delete()
                except Exception:
                    pass

                return

    # الردود المضافة
    key = text.lower()

    if key in custom_replies:

        try:

            await message.reply_text(
                custom_replies[key]
            )

        except Exception as e:

            print(
                "REPLY ERROR:",
                repr(e),
            )


# =========================================================
# الترحيب
# =========================================================

@bot.on_message(
    filters.group &
    filters.new_chat_members,
)
async def welcome_handler(client, message):

    if not chat_settings[
        message.chat.id
    ]["welcome"]:

        return

    for user in message.new_chat_members:

        if user.is_bot:
            continue

        await message.reply_text(
            f"👋 أهلاً {user.mention}\n\n"
            f"💜 نورت المجموعة.\n"
            f"🎵 استمتع مع {BOT_NAME}."
        )


# =========================================================
# ألعاب بسيطة
# =========================================================

@bot.on_message(
    filters.group &
    filters.regex(r"^نرد$")
)
async def dice_game(client, message):

    import random

    number = random.randint(1, 6)

    await message.reply_text(
        f"🎲 النرد وقع على: {number}"
    )


@bot.on_message(
    filters.group &
    filters.regex(r"^(عملة|عملة معدنية)$")
)
async def coin_game(client, message):

    import random

    result = random.choice(
        ["وجه 🪙", "كتابة 🪙"]
    )

    await message.reply_text(
        f"🪙 النتيجة: {result}"
    )


@bot.on_message(
    filters.group &
    filters.regex(r"^حظك اليوم$")
)
async def luck_game(client, message):

    import random

    percentage = random.randint(
        1,
        100,
    )

    await message.reply_text(
        f"🍀 نسبة حظك اليوم: {percentage}%"
    )


# =========================================================
# تشغيل البرنامج
# =========================================================

async def main():

    load_data()

    print(
        "================================"
    )

    print(
        "MariamMusicBot starting..."
    )

    print(
        "================================"
    )

    await bot.start()

    await music_user.start()

    call.start()

    me = await bot.get_me()

    print(
        f"BOT: @{me.username}"
    )

    print(
        "Bot started successfully."
    )

    print(
        "Music account connected."
    )

    print(
        "PyTgCalls started."
    )

    await idle()

    call.stop()

    await music_user.stop()

    await bot.stop()


if __name__ == "__main__":

    asyncio.run(
        main()
    )
