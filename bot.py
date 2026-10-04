import os
import re
import json
import random
import asyncio
import logging
from pathlib import Path

import yt_dlp
from pyrogram import Client, filters, idle
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import FloodWait
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from pytgcalls import PyTgCalls
from pytgcalls import filters as call_filters
from pytgcalls.types import MediaStream
from pytgcalls.types import GroupCallConfig
from pytgcalls.types import StreamEnded


# =========================================================
# الإعدادات
# =========================================================

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# لو مش عايز اشتراك إجباري سيبه فاضي
REQUIRED_CHANNEL = os.getenv(
    "REQUIRED_CHANNEL",
    ""
).strip()


if not API_ID:
    raise RuntimeError(
        "API_ID غير موجود في Environment Variables"
    )

if not API_HASH:
    raise RuntimeError(
        "API_HASH غير موجود في Environment Variables"
    )

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN غير موجود في Environment Variables"
    )

if not SESSION_STRING:
    raise RuntimeError(
        "SESSION_STRING غير موجود."
    )


# =========================================================
# الملفات
# =========================================================

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

REPLIES_FILE = DATA_DIR / "replies.json"
ACTIVE_FILE = DATA_DIR / "active_chats.json"
BADWORDS_FILE = DATA_DIR / "badwords.json"


# =========================================================
# Logging
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

log = logging.getLogger("MariamMusicBot")


# =========================================================
# JSON
# =========================================================

def load_json(path, default):
    try:
        if path.exists():
            return json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
    except Exception:
        pass

    return default


def save_json(path, data):
    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


auto_replies = load_json(
    REPLIES_FILE,
    {}
)

active_chats = set(
    map(
        int,
        load_json(
            ACTIVE_FILE,
            []
        )
    )
)

badword_chats = set(
    map(
        int,
        load_json(
            BADWORDS_FILE,
            []
        )
    )
)


def save_active():
    save_json(
        ACTIVE_FILE,
        sorted(active_chats)
    )


def save_badwords():
    save_json(
        BADWORDS_FILE,
        sorted(badword_chats)
    )


# =========================================================
# Telegram Clients
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

voice = PyTgCalls(assistant)


# =========================================================
# أدوات عامة
# =========================================================

async def safe_send(chat_id, text, **kwargs):
    try:
        return await bot.send_message(
            chat_id,
            text,
            **kwargs
        )

    except FloodWait as e:
        log.warning(
            "FloodWait: sleeping %s seconds",
            e.value
        )

        await asyncio.sleep(
            int(e.value) + 1
        )

        try:
            return await bot.send_message(
                chat_id,
                text,
                **kwargs
            )
        except Exception:
            return None

    except Exception as e:
        log.warning(
            "send error: %s",
            e
        )
        return None


# =========================================================
# الرتب
# =========================================================

async def get_role(message):

    if not message.from_user:
        return "مجهول"

    user_id = message.from_user.id

    if OWNER_ID and user_id == OWNER_ID:
        return "المالك"

    try:

        member = await bot.get_chat_member(
            message.chat.id,
            user_id
        )

        if member.status == ChatMemberStatus.OWNER:
            return "المالك"

        if member.status == ChatMemberStatus.ADMINISTRATOR:
            return "أدمن"

        return "عضو"

    except Exception:
        return "عضو"


async def is_admin(message):

    if not message.from_user:
        return False

    user_id = message.from_user.id

    if OWNER_ID and user_id == OWNER_ID:
        return True

    try:

        member = await bot.get_chat_member(
            message.chat.id,
            user_id
        )

        return member.status in (
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR,
        )

    except Exception:
        return False


async def require_admin(message):

    if not await is_admin(message):
        await message.reply_text(
            "❌ الأمر ده للأدمن فقط."
        )
        return False

    return True


async def get_target(message):

    if (
        message.reply_to_message
        and message.reply_to_message.from_user
    ):
        return message.reply_to_message.from_user

    return None


# =========================================================
# تفعيل البوت
# =========================================================

@bot.on_message(
    filters.group
    & filters.regex(r"^تفعيل البوت$")
)
async def activate_bot(_, message):

    if not await require_admin(message):
        return

    active_chats.add(
        message.chat.id
    )

    save_active()

    await message.reply_text(
        "✅ تم تفعيل البوت.\n\n"
        "🎵 الموسيقى جاهزة\n"
        "🎮 الألعاب جاهزة\n"
        "💬 الردود جاهزة\n"
        "🛡️ الحماية جاهزة"
    )


@bot.on_message(
    filters.group
    & filters.regex(r"^تعطيل البوت$")
)
async def deactivate_bot(_, message):

    if not await require_admin(message):
        return

    active_chats.discard(
        message.chat.id
    )

    save_active()

    await stop_music(
        message.chat.id,
        silent=True
    )

    await stop_game(
        message.chat.id
    )

    await message.reply_text(
        "🛑 تم تعطيل البوت."
    )


# =========================================================
# الموسيقى
# =========================================================

music = {}
music_locks = {}


def get_music(chat_id):

    if chat_id not in music:

        music[chat_id] = {
            "queue": [],
            "current": None,
            "playing": False,
        }

    return music[chat_id]


def get_music_lock(chat_id):

    if chat_id not in music_locks:
        music_locks[chat_id] = asyncio.Lock()

    return music_locks[chat_id]


# =========================================================
# البحث عن الأغاني
# =========================================================

async def search_song(query):

    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
        "noplaylist": True,
    }

    def search():

        with yt_dlp.YoutubeDL(options) as ydl:

            info = ydl.extract_info(
                f"ytsearch1:{query}",
                download=False
            )

            if not info:
                return None

            entries = info.get(
                "entries",
                []
            )

            if not entries:
                return None

            song = entries[0]

            return {
                "title": song.get(
                    "title",
                    query
                ),
                "url": song.get(
                    "webpage_url"
                ),
                "duration": song.get(
                    "duration",
                    0
                ),
            }

    return await asyncio.to_thread(
        search
    )


# =========================================================
# استخراج رابط الصوت
# =========================================================

async def get_audio_url(url):

    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "format": "bestaudio/best",
        "noplaylist": True,
    }

    def extract():

        with yt_dlp.YoutubeDL(options) as ydl:

            info = ydl.extract_info(
                url,
                download=False
            )

            if info.get("url"):
                return info["url"]

            formats = info.get(
                "formats",
                []
            )

            audio_formats = [
                x
                for x in formats
                if x.get("url")
                and x.get("acodec") != "none"
            ]

            if not audio_formats:
                return None

            audio_formats.sort(
                key=lambda x: (
                    x.get("abr") or 0
                ),
                reverse=True
            )

            return audio_formats[0]["url"]

    return await asyncio.to_thread(
        extract
    )


# =========================================================
# تشغيل أغنية
# =========================================================

async def play_song(chat_id, song):

    audio_url = await get_audio_url(
        song["url"]
    )

    if not audio_url:
        raise RuntimeError(
            "لم أستطع استخراج الصوت."
        )

    stream = MediaStream(
        audio_url,
        video_flags=MediaStream.Flags.IGNORE
    )

    await voice.play(
        chat_id,
        stream,
        GroupCallConfig(
            auto_start=True
        )
    )

    state = get_music(chat_id)

    state["current"] = song
    state["playing"] = True


# =========================================================
# تشغيل التالي
# =========================================================

async def play_next(chat_id):

    state = get_music(chat_id)

    if not state["queue"]:

        state["current"] = None
        state["playing"] = False

        return False

    song = state["queue"].pop(0)

    try:

        await play_song(
            chat_id,
            song
        )

        await safe_send(
            chat_id,
            "🎶 الآن يعمل:\n\n"
            f"🎵 {song['title']}\n\n"
            "⏭ تخطي\n"
            "⛔ إيقاف"
        )

        return True

    except Exception as e:

        log.exception(
            "play_next error"
        )

        await safe_send(
            chat_id,
            "❌ حصل خطأ أثناء تشغيل:\n"
            f"{song['title']}"
        )

        return await play_next(
            chat_id
        )


# =========================================================
# إضافة أغنية
# =========================================================

async def add_song(
    chat_id,
    query,
    username
):

    lock = get_music_lock(
        chat_id
    )

    async with lock:

        await safe_send(
            chat_id,
            "🔎 بدور على الأغنية..."
        )

        song = await search_song(
            query
        )

        if not song:

            await safe_send(
                chat_id,
                "❌ ملقتش الأغنية."
            )

            return

        state = get_music(
            chat_id
        )

        if (
            state["playing"]
            or state["current"]
        ):

            state["queue"].append(
                song
            )

            await safe_send(
                chat_id,
                "➕ اتضافت للقائمة:\n\n"
                f"🎵 {song['title']}\n"
                f"👤 بواسطة: {username}\n"
                f"📋 رقمها: {len(state['queue'])}"
            )

            return

        try:

            await play_song(
                chat_id,
                song
            )

            await safe_send(
                chat_id,
                "🎵 شغلت:\n\n"
                f"{song['title']}\n\n"
                "⏭ تخطي\n"
                "⛔ إيقاف"
            )

        except Exception as e:

            log.exception(
                "music error"
            )

            await safe_send(
                chat_id,
                "❌ مقدرتش أشغل الموسيقى.\n\n"
                "تأكد إن حساب SESSION_STRING "
                "موجود في الجروب ومسموح له بإدارة "
                "المحادثة الصوتية."
            )


# =========================================================
# تشغيل أمر تشغيل
# =========================================================

@bot.on_message(
    filters.group
    & filters.regex(r"^تشغيل$")
)
async def play_no_name(_, message):

    if message.chat.id not in active_chats:
        return

    await message.reply_text(
        "🎵 قول اسم الأغنية.\n\n"
        "مثال:\n"
        "تشغيل مانو"
    )


@bot.on_message(
    filters.group
    & filters.regex(r"^تشغيل\s+(.+)$")
)
async def play_handler(_, message):

    if message.chat.id not in active_chats:
        return

    query = message.matches[0].group(1).strip()

    await add_song(
        message.chat.id,
        query,
        (
            message.from_user.first_name
            if message.from_user
            else "عضو"
        )
    )


# =========================================================
# تخطي
# =========================================================

async def skip_music(chat_id):

    state = get_music(
        chat_id
    )

    if (
        not state["current"]
        and not state["queue"]
    ):

        await safe_send(
            chat_id,
            "❌ مفيش أغنية شغالة."
        )

        return

    try:
        await voice.leave_call(
            chat_id
        )
    except Exception:
        pass

    state["current"] = None
    state["playing"] = False

    if await play_next(chat_id):
        return

    await safe_send(
        chat_id,
        "⏭ خلصت قائمة التشغيل."
    )


@bot.on_message(
    filters.group
    & filters.regex(r"^(تخطي|سكيب)$")
)
async def skip_handler(_, message):

    if message.chat.id not in active_chats:
        return

    await skip_music(
        message.chat.id
    )


# =========================================================
# إيقاف الموسيقى
# =========================================================

async def stop_music(
    chat_id,
    silent=False
):

    state = get_music(
        chat_id
    )

    state["queue"].clear()
    state["current"] = None
    state["playing"] = False

    try:
        await voice.leave_call(
            chat_id
        )
    except Exception:
        pass

    if not silent:

        await safe_send(
            chat_id,
            "⛔ تم إيقاف الموسيقى."
        )


@bot.on_message(
    filters.group
    & filters.regex(r"^(إيقاف|وقف)$")
)
async def stop_music_handler(_, message):

    if message.chat.id not in active_chats:
        return

    await stop_music(
        message.chat.id
    )


# =========================================================
# قائمة التشغيل
# =========================================================

@bot.on_message(
    filters.group
    & filters.regex(r"^القائمة$")
)
async def queue_handler(_, message):

    if message.chat.id not in active_chats:
        return

    state = get_music(
        message.chat.id
    )

    lines = []

    if state["current"]:

        lines.append(
            "🎶 الآن:\n"
            f"{state['current']['title']}"
        )

    for i, song in enumerate(
        state["queue"],
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
        "📋 قائمة التشغيل:\n\n"
        + "\n".join(lines)
    )


# =========================================================
# نهاية الأغنية
# =========================================================

@voice.on_update(
    call_filters.stream_end()
)
async def stream_finished(
    _,
    update: StreamEnded
):

    chat_id = update.chat_id

    state = get_music(
        chat_id
    )

    if not state["playing"]:
        return

    state["current"] = None
    state["playing"] = False

    await play_next(
        chat_id
    )


# =========================================================
# الألعاب
# =========================================================

GAME_NAMES = [
    "جمع سريع",
    "طرح سريع",
    "ضرب سريع",
    "قسمة سريعة",
    "معادلة سهلة",
    "معادلة متوسطة",
    "معادلة صعبة",
    "خمن الرقم",
    "خمن الحرف",
    "خمن الكلمة",
    "ترتيب الحروف",
    "عكس الكلمة",
    "صح أو خطأ",
    "نعم أو لا",
    "عاصمة",
    "دولة وعاصمة",
    "عملة",
    "حيوان",
    "فاكهة",
    "خضار",
    "لون",
    "رياضة",
    "لاعب مشهور",
    "فيلم",
    "مسلسل",
    "أغنية",
    "معلومات عامة",
    "علوم",
    "فضاء",
    "تاريخ",
    "جغرافيا",
    "لغة عربية",
    "إنجليزي",
    "مرادف",
    "ضد الكلمة",
    "جمع كلمة",
    "مفرد كلمة",
    "لغز",
    "لغز سهل",
    "لغز صعب",
    "ذكاء",
    "تركيز",
    "ذاكرة",
    "سرعة كتابة",
    "كلمة من 3 حروف",
    "كلمة من 4 حروف",
    "كلمة من 5 حروف",
    "اسم ولد",
    "اسم بنت",
    "مدينة",
    "نهر",
    "بحر",
    "جبل",
    "حرف مفقود",
    "رقم مفقود",
    "نمط أرقام",
    "نمط حروف",
    "حساب العمر",
    "نسبة مئوية",
    "كسور",
    "مقارنة أرقام",
    "أكبر أم أصغر",
    "زوجي أم فردي",
    "مضاعفات",
    "قواسم",
    "مسألة وقت",
    "مسألة مسافة",
    "مسألة سرعة",
    "ألغاز منطق",
    "من أنا",
    "من الحيوان",
    "من الدولة",
    "من المدينة",
    "من الفيلم",
    "من الأغنية",
    "تخمين الإيموجي",
    "فك الإيموجي",
    "كلمة مخفية",
    "حرف البداية",
    "حرف النهاية",
    "كم عدد",
    "ما اللون",
    "ما الشكل",
    "ما الرقم",
    "ما الحرف",
    "ما الاسم",
    "ما المكان",
    "ما اللغة",
    "ما العملة",
    "ما القارة",
    "ما الكوكب",
    "ما الحيوان",
    "ما النبات",
    "ما الطعام",
    "ما الشراب",
    "ما الرياضة",
    "ما الأداة",
    "ما المهنة",
    "ما المعلومة",
    "اختيار متعدد 1",
    "اختيار متعدد 2",
    "اختيار متعدد 3",
    "اختيار متعدد 4",
    "اختيار متعدد 5",
    "تحدي الحساب",
    "تحدي الذاكرة",
    "تحدي السرعة",
    "تحدي الذكاء",
    "تحدي الكلمات",
    "تحدي الحروف",
    "تحدي الأرقام",
    "تحدي المعلومات",
    "تحدي العواصم",
    "تحدي الدول",
    "تحدي الحيوانات",
    "تحدي العلوم",
    "تحدي التاريخ",
    "تحدي الجغرافيا",
    "تحدي اللغة",
    "تحدي النجوم",
    "تحدي الأفلام",
    "تحدي الأغاني",
    "تحدي الرياضة",
    "مليونير",
    "المسابقة الكبرى",
    "سؤال وجواب",
    "سؤال اليوم",
    "اختبر نفسك",
    "اختبار الذكاء",
    "اختبار السرعة",
    "اختبار المعلومات",
    "XO",
    "حجر ورق مقص",
]


TRIVIA = [
    ("ما عاصمة مصر؟", "القاهرة"),
    (
        "ما أكبر كوكب في المجموعة الشمسية؟",
        "المشتري"
    ),
    (
        "كم عدد أيام الأسبوع؟",
        "7"
    ),
    (
        "ما الكوكب الأحمر؟",
        "المريخ"
    ),
    (
        "ما الحيوان المعروف بملك الغابة؟",
        "الأسد"
    ),
    (
        "كم عدد قارات العالم؟",
        "7"
    ),
    (
        "ما عاصمة السعودية؟",
        "الرياض"
    ),
    (
        "ما عاصمة فرنسا؟",
        "باريس"
    ),
    (
        "ما أكبر محيط؟",
        "الهادي"
    ),
    (
        "كم عدد أشهر السنة؟",
        "12"
    ),
]


WORDS = [
    "تفاحة",
    "موزة",
    "سيارة",
    "قمر",
    "كتاب",
    "مدرسة",
    "بحر",
    "نجم",
    "وردة",
    "كرسي",
]


TRUE_FALSE = [
    (
        "الشمس نجم.",
        "صح"
    ),
    (
        "القمر كوكب.",
        "غلط"
    ),
    (
        "الماء يتجمد عند صفر درجة تقريبًا.",
        "صح"
    ),
    (
        "مصر تقع في أفريقيا.",
        "صح"
    ),
    (
        "الأرض مسطحة.",
        "غلط"
    ),
]


MULTI = [
    (
        "ما عاصمة إيطاليا؟\n"
        "أ) روما\n"
        "ب) مدريد\n"
        "ج) باريس",
        "ا"
    ),
    (
        "أي كوكب أقرب للشمس؟\n"
        "أ) الأرض\n"
        "ب) عطارد\n"
        "ج) المشتري",
        "ب"
    ),
    (
        "كم عدد أرجل العنكبوت؟\n"
        "أ) 6\n"
        "ب) 8\n"
        "ج) 10",
        "ب"
    ),
]


def normalize(text):

    text = text.strip().lower()

    text = text.replace(
        "أ",
        "ا"
    )

    text = text.replace(
        "إ",
        "ا"
    )

    text = text.replace(
        "آ",
        "ا"
    )

    text = text.replace(
        "ة",
        "ه"
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text


def create_game_question(name):

    n = normalize(name)

    # -------------------------
    # جمع
    # -------------------------

    if name == "جمع سريع":

        a = random.randint(
            1,
            50
        )

        b = random.randint(
            1,
            50
        )

        return (
            f"🧮 احسب:\n"
            f"{a} + {b} = ؟",
            str(a + b)
        )

    # -------------------------
    # طرح
    # -------------------------

    if name == "طرح سريع":

        a = random.randint(
            1,
            70
        )

        b = random.randint(
            1,
            50
        )

        if b > a:
            a, b = b, a

        return (
            f"🧮 احسب:\n"
            f"{a} - {b} = ؟",
            str(a - b)
        )

    # -------------------------
    # ضرب
    # -------------------------

    if name == "ضرب سريع":

        a = random.randint(
            2,
            12
        )

        b = random.randint(
            2,
            12
        )

        return (
            f"🧮 احسب:\n"
            f"{a} × {b} = ؟",
            str(a * b)
        )

    # -------------------------
    # قسمة
    # -------------------------

    if name == "قسمة سريعة":

        b = random.randint(
            2,
            10
        )

        answer = random.randint(
            2,
            12
        )

        a = b * answer

        return (
            f"🧮 احسب:\n"
            f"{a} ÷ {b} = ؟",
            str(answer)
        )

    # -------------------------
    # معادلات
    # -------------------------

    if name in (
        "معادلة سهلة",
        "معادلة متوسطة",
        "معادلة صعبة",
        "تحدي الحساب"
    ):

        a = random.randint(
            1,
            20
        )

        b = random.randint(
            1,
            20
        )

        c = random.randint(
            1,
            10
        )

        if name == "معادلة صعبة":

            answer = (
                a * b
                + c
            )

            return (
                f"🧠 احسب:\n"
                f"{a} × {b} + {c} = ؟",
                str(answer)
            )

        answer = (
            a
            + b
            + c
        )

        return (
            f"🧠 احسب:\n"
            f"{a} + {b} + {c} = ؟",
            str(answer)
        )

    # -------------------------
    # صح وغلط
    # -------------------------

    if (
        "صح" in n
        or "نعم" in n
    ):

        question, answer = random.choice(
            TRUE_FALSE
        )

        return (
            f"❓ {question}\n\n"
            "اكتب: صح أو غلط",
            answer
        )

    # -------------------------
    # اختيار متعدد
    # -------------------------

    if (
        "اختيار" in n
        or "مليونير" in n
        or "مسابقة" in n
    ):

        return random.choice(
            MULTI
        )

    # -------------------------
    # حروف
    # -------------------------

    if "حرف" in n:

        word = random.choice(
            WORDS
        )

        return (
            f"🔤 اكتب أول حرف من:\n"
            f"{word}",
            word[0]
        )

    # -------------------------
    # عكس
    # -------------------------

    if "عكس" in n:

        word = random.choice(
            WORDS
        )

        return (
            f"🔄 اعكس الكلمة:\n"
            f"{word}",
            word[::-1]
        )

    # -------------------------
    # ترتيب
    # -------------------------

    if "ترتيب" in n:

        word = random.choice(
            WORDS
        )

        shuffled = "".join(
            random.sample(
                word,
                len(word)
            )
        )

        return (
            f"🔤 رتب الحروف:\n"
            f"{shuffled}",
            word
        )

    # -------------------------
    # زوجي وفردي
    # -------------------------

    if "زوجي" in n:

        number = random.randint(
            1,
            100
        )

        answer = (
            "زوجي"
            if number % 2 == 0
            else "فردي"
        )

        return (
            f"🔢 الرقم {number}\n"
            "زوجي ولا فردي؟",
            answer
        )

    # -------------------------
    # الأكبر
    # -------------------------

    if (
        "أكبر" in n
        or "مقارنة" in n
    ):

        a, b = random.sample(
            range(1, 100),
            2
        )

        return (
            f"🔢 مين أكبر؟\n"
            f"{a} ولا {b}؟",
            str(max(a, b))
        )

    # -------------------------
    # النسبة
    # -------------------------

    if "نسبة" in n:

        base = random.choice(
            [
                50,
                100,
                200,
                500
            ]
        )

        percent = random.choice(
            [
                10,
                20,
                25,
                50
            ]
        )

        answer = (
            base
            * percent
            // 100
        )

        return (
            f"📊 كام {percent}% "
            f"من {base}؟",
            str(answer)
        )

    # -------------------------
    # نمط أرقام
    # -------------------------

    if (
        "نمط أرقام" in n
        or "رقم مفقود" in n
    ):

        start = random.randint(
            1,
            10
        )

        step = random.randint(
            2,
            8
        )

        sequence = [
            start + i * step
            for i in range(4)
        ]

        return (
            "🔢 أكمل الرقم:\n"
            f"{sequence[0]}، "
            f"{sequence[1]}، "
            f"{sequence[2]}، ؟",
            str(sequence[3])
        )

    # -------------------------
    # إيموجي
    # -------------------------

    if "إيموجي" in n:

        pairs = [
            (
                "🍎📱",
                "ايفون"
            ),
            (
                "🌙⭐",
                "ليل"
            ),
            (
                "🔥❤️",
                "حب"
            ),
            (
                "⚽🥅",
                "كرة"
            ),
        ]

        question, answer = random.choice(
            pairs
        )

        return (
            f"🎯 خمن الكلمة:\n"
            f"{question}",
            answer
        )

    # -------------------------
    # الحيوان
    # -------------------------

    if "حيوان" in n:

        return (
            "🐾 ما الحيوان المعروف "
            "بملك الغابة؟",
            "الأسد"
        )

    # -------------------------
    # علوم
    # -------------------------

    if "علوم" in n:

        return (
            "🔬 ما الغاز الذي يحتاجه "
            "الإنسان للتنفس؟",
            "الأكسجين"
        )

    # -------------------------
    # فضاء
    # -------------------------

    if (
        "فضاء" in n
        or "كوكب" in n
        or "نجوم" in n
    ):

        return (
            "🚀 ما الكوكب الأحمر؟",
            "المريخ"
        )

    # -------------------------
    # رياضة
    # -------------------------

    if "رياضة" in n:

        return (
            "⚽ كم لاعبًا يبدأ به "
            "فريق كرة القدم داخل "
            "الملعب؟",
            "11"
        )

    # -------------------------
    # عواصم
    # -------------------------

    if "عاصمة" in n:

        return random.choice(
            [
                TRIVIA[0],
                TRIVIA[6],
                TRIVIA[7],
            ]
        )

    # -------------------------
    # جغرافيا
    # -------------------------

    if (
        "جغرافيا" in n
        or "دولة" in n
        or "قارة" in n
    ):

        return random.choice(
            TRIVIA
        )

    # -------------------------
    # ألغاز
    # -------------------------

    if (
        "لغز" in n
        or "ذكاء" in n
        or "منطق" in n
    ):

        return (
            "🧩 شيء له أسنان "
            "ولا يعض، ما هو؟",
            "المشط"
        )

    # -------------------------
    # كلمة
    # -------------------------

    if "كلمة" in n:

        word = random.choice(
            WORDS
        )

        return (
            "✍️ اكتب الكلمة:\n"
            f"{word}",
            word
        )

    # -------------------------
    # سؤال عام
    # -------------------------

    return random.choice(
        TRIVIA
    )


games = {}


async def stop_game(chat_id):

    games.pop(
        chat_id,
        None
    )


# =========================================================
# بدء لعبة
# =========================================================

async def start_game(
    message,
    game_name
):

    chat_id = message.chat.id

    if chat_id in games:

        await message.reply_text(
            "🎮 في لعبة شغالة بالفعل.\n\n"
            "جاوب على السؤال، أو اكتب:\n"
            "إيقاف اللعبة"
        )

        return

    # =====================================================
    # XO
    # =====================================================

    if game_name == "XO":

        games[chat_id] = {
            "type": "xo",
            "board": [
                " ",
                " ",
                " ",
                " ",
                " ",
                " ",
                " ",
                " ",
                " ",
            ],
            "player1": message.from_user.id,
            "player2": None,
            "turn": message.from_user.id,
        }

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🎮 انضمام للعبة XO",
                        callback_data="xo_join"
                    )
                ]
            ]
        )

        await message.reply_text(
            "❌⭕ لعبة XO بدأت!\n\n"
            "مستني لاعب ثاني.\n\n"
            "بعد الانضمام اكتب:\n"
            "XO 1\n"
            "XO 2\n"
            "...\n"
            "XO 9\n\n"
            "⛔ إيقاف اللعبة",
            reply_markup=keyboard
        )

        return

    # =====================================================
    # حجر ورق مقص
    # =====================================================

    if game_name == "حجر ورق مقص":

        games[chat_id] = {
            "type": "rps",
            "player1": message.from_user.id,
            "player2": None,
        }

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🎮 انضمام",
                        callback_data="rps_join"
                    )
                ]
            ]
        )

        await message.reply_text(
            "✊✋✌️ حجر ورق مقص\n\n"
            "اضغط انضمام عشان يدخل "
            "لاعب ثاني.",
            reply_markup=keyboard
        )

        return

    # =====================================================
    # الألعاب العادية
    # =====================================================

    question, answer = (
        create_game_question(
            game_name
        )
    )

    games[chat_id] = {
        "type": "answer",
        "name": game_name,
        "question": question,
        "answer": normalize(answer),
        "asked_by": message.from_user.id,
    }

    await message.reply_text(
        f"🎮 اللعبة: {game_name}\n\n"
        f"{question}\n\n"
        "✍️ اكتب إجابتك هنا.\n\n"
        "⛔ إيقاف اللعبة"
    )


# =========================================================
# قائمة الألعاب
# =========================================================

@bot.on_message(
    filters.group
    & filters.regex(r"^العاب$")
)
async def games_list(_, message):

    if message.chat.id not in active_chats:
        return

    text = (
        "🎮 الألعاب المتاحة:\n\n"
        f"عدد الألعاب: {len(GAME_NAMES)}\n\n"
    )

    text += " • ".join(
        GAME_NAMES
    )

    text += (
        "\n\n"
        "💡 اكتب اسم اللعبة عشان تبدأ.\n"
        "⛔ إيقاف اللعبة = إلغاء اللعبة."
    )

    await message.reply_text(
        text
    )


# =========================================================
# إيقاف اللعبة
# =========================================================

@bot.on_message(
    filters.group
    & filters.regex(
        r"^(إيقاف اللعبة|ايقاف اللعبة)$"
    )
)
async def stop_game_command(
    _,
    message
):

    if message.chat.id not in active_chats:
        return

    if message.chat.id not in games:

        await message.reply_text(
            "❌ مفيش لعبة شغالة."
        )

        return

    await stop_game(
        message.chat.id
    )

    await message.reply_text(
        "🛑 تم إيقاف اللعبة.\n\n"
        "🎮 تقدر تشغل لعبة جديدة دلوقتي."
    )


# =========================================================
# تشغيل أي لعبة من القائمة
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
)
async def game_name_handler(
    _,
    message
):

    if message.chat.id not in active_chats:
        return

    text = (
        message.text
        or ""
    ).strip()

    if text in GAME_NAMES:

        await start_game(
            message,
            text
        )


# =========================================================
# التحقق من إجابة اللعبة
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
)
async def game_answer_checker(
    _,
    message
):

    chat_id = message.chat.id

    if chat_id not in active_chats:
        return

    text = (
        message.text
        or ""
    ).strip()

    # الأوامر ليست إجابات
    ignored = {
        "الأوامر",
        "العاب",
        "تفعيل البوت",
        "تعطيل البوت",
        "إيقاف",
        "وقف",
        "تخطي",
        "سكيب",
        "القائمة",
        "إيقاف اللعبة",
        "ايقاف اللعبة",
    }

    if text in ignored:
        return

    game = games.get(
        chat_id
    )

    if not game:
        return

    if game.get("type") != "answer":
        return

    # لو المستخدم كتب اسم لعبة أخرى
    # لا نعتبرها إجابة
    if text in GAME_NAMES:
        return

    user_answer = normalize(
        text
    )

    correct_answer = game[
        "answer"
    ]

    # =====================================================
    # صح
    # =====================================================

    if user_answer == correct_answer:

        await message.reply_text(
            "✅ إجابة صحيحة! 🎉\n\n"
            f"برافو يا "
            f"{message.from_user.first_name}\n"
            "السؤال الجديد 👇"
        )

        game_name = game[
            "name"
        ]

        question, answer = (
            create_game_question(
                game_name
            )
        )

        games[chat_id] = {
            "type": "answer",
            "name": game_name,
            "question": question,
            "answer": normalize(answer),
            "asked_by": message.from_user.id,
        }

        await message.reply_text(
            f"🎮 {game_name}\n\n"
            f"{question}\n\n"
            "✍️ اكتب الإجابة.\n"
            "⛔ إيقاف اللعبة"
        )

    # =====================================================
    # غلط
    # =====================================================

    else:

        await message.reply_text(
            "❌ إجابة غلط 😄\n"
            "حاول تاني."
        )


# =========================================================
# ألعاب اللاعبين - Callback
# =========================================================

@bot.on_callback_query()
async def game_buttons(
    client,
    query
):

    chat_id = (
        query.message.chat.id
    )

    user_id = (
        query.from_user.id
    )

    game = games.get(
        chat_id
    )

    if not game:

        await query.answer(
            "اللعبة انتهت.",
            show_alert=True
        )

        return

    # =====================================================
    # RPS - انضمام
    # =====================================================

    if (
        game["type"] == "rps"
        and query.data == "rps_join"
    ):

        if (
            game["player1"]
            == user_id
        ):

            await query.answer(
                "أنت صاحب اللعبة 😄",
                show_alert=True
            )

            return

        game["player2"] = user_id
        game["choices"] = {}

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✊ حجر",
                        callback_data="rps_rock"
                    ),
                    InlineKeyboardButton(
                        "✋ ورق",
                        callback_data="rps_paper"
                    ),
                    InlineKeyboardButton(
                        "✌️ مقص",
                        callback_data="rps_scissors"
                    ),
                ]
            ]
        )

        await query.message.edit_text(
            "✊✋✌️ حجر ورق مقص\n\n"
            "كل لاعب يختار اختياره.",
            reply_markup=keyboard
        )

        await query.answer(
            "انضممت!"
        )

        return

    # =====================================================
    # RPS - اختيار
    # =====================================================

    if (
        game["type"] == "rps"
        and query.data.startswith(
            "rps_"
        )
    ):

        if user_id not in (
            game["player1"],
            game["player2"],
        ):

            await query.answer(
                "اللعبة للاعبين فقط.",
                show_alert=True
            )

            return

        choice = (
            query.data
            .replace(
                "rps_",
                ""
            )
        )

        game["choices"][
            user_id
        ] = choice

        await query.answer(
            "تم تسجيل اختيارك."
        )

        if len(
            game["choices"]
        ) < 2:

            await query.message.reply_text(
                "⏳ مستني اختيار اللاعب الثاني..."
            )

            return

        p1 = game[
            "choices"
        ][
            game["player1"]
        ]

        p2 = game[
            "choices"
        ][
            game["player2"]
        ]

        if p1 == p2:

            result = (
                "🤝 تعادل!"
            )

        elif (
            (
                p1 == "rock"
                and p2 == "scissors"
            )
            or (
                p1 == "scissors"
                and p2 == "paper"
            )
            or (
                p1 == "paper"
                and p2 == "rock"
            )
        ):

            result = (
                "🏆 اللاعب الأول كسب!"
            )

        else:

            result = (
                "🏆 اللاعب الثاني كسب!"
            )

        await query.message.reply_text(
            f"🎮 اللاعب الأول: {p1}\n"
            f"🎮 اللاعب الثاني: {p2}\n\n"
            f"{result}"
        )

        games.pop(
            chat_id,
            None
        )

        return

    # =====================================================
    # XO - انضمام
    # =====================================================

    if (
        game["type"] == "xo"
        and query.data == "xo_join"
    ):

        if (
            game["player1"]
            == user_id
        ):

            await query.answer(
                "أنت صاحب اللعبة.",
                show_alert=True
            )

            return

        game["player2"] = user_id

        await query.answer(
            "انضممت!"
        )

        await query.message.edit_text(
            "❌⭕ XO بدأت!\n\n"
            "اكتب:\n"
            "XO 1\n"
            "XO 2\n"
            "XO 3\n"
            "...\n"
            "XO 9\n\n"
            "❌ اللاعب الأول يبدأ."
        )


# =========================================================
# XO
# =========================================================

@bot.on_message(
    filters.group
    & filters.regex(
        r"^XO\s*([1-9])$"
    )
)
async def xo_move(
    _,
    message
):

    chat_id = message.chat.id

    game = games.get(
        chat_id
    )

    if (
        not game
        or game.get("type") != "xo"
    ):
        return

    if not game.get(
        "player2"
    ):

        await message.reply_text(
            "⏳ مستني لاعب ثاني."
        )

        return

    user_id = (
        message.from_user.id
    )

    if user_id not in (
        game["player1"],
        game["player2"],
    ):
        return

    if user_id != game[
        "turn"
    ]:

        await message.reply_text(
            "⏳ مش دورك."
        )

        return

    position = (
        int(
            message.matches[0].group(1)
        )
        - 1
    )

    if game[
        "board"
    ][position] != " ":

        await message.reply_text(
            "❌ المكان مستخدم."
        )

        return

    mark = (
        "❌"
        if user_id == game["player1"]
        else "⭕"
    )

    game[
        "board"
    ][position] = mark

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

    winner = None

    for a, b, c in wins:

        if (
            game["board"][a] != " "
            and game["board"][a]
            == game["board"][b]
            == game["board"][c]
        ):

            winner = mark
            break

    board = (
        f"{game['board'][0]} | "
        f"{game['board'][1]} | "
        f"{game['board'][2]}\n"
        "---------\n"
        f"{game['board'][3]} | "
        f"{game['board'][4]} | "
        f"{game['board'][5]}\n"
        "---------\n"
        f"{game['board'][6]} | "
        f"{game['board'][7]} | "
        f"{game['board'][8]}"
    )

    if winner:

        await message.reply_text(
            f"{board}\n\n"
            f"🏆 {winner} كسب!"
        )

        games.pop(
            chat_id,
            None
        )

        return

    if all(
        x != " "
        for x in game["board"]
    ):

        await message.reply_text(
            f"{board}\n\n"
            "🤝 تعادل!"
        )

        games.pop(
            chat_id,
            None
        )

        return

    game["turn"] = (
        game["player2"]
        if user_id == game["player1"]
        else game["player1"]
    )

    await message.reply_text(
        f"{board}\n\n"
        "➡️ دور اللاعب الآخر."
    )


# =========================================================
# الردود التلقائية
# =========================================================

@bot.on_message(
    filters.group
    & filters.regex(
        r"^اضف رد\s+(.+?)\s+(.+)$"
    )
)
async def add_auto_reply(
    _,
    message
):

    if not await require_admin(
        message
    ):
        return

    word = (
        message.matches[0]
        .group(1)
        .strip()
        .lower()
    )

    reply = (
        message.matches[0]
        .group(2)
        .strip()
    )

    chat_id = str(
        message.chat.id
    )

    auto_replies.setdefault(
        chat_id,
        {}
    )

    auto_replies[
        chat_id
    ][word] = reply

    save_json(
        REPLIES_FILE,
        auto_replies
    )

    await message.reply_text(
        "✅ تم إضافة الرد.\n\n"
        f"الكلمة: {word}\n"
        f"الرد: {reply}"
    )


@bot.on_message(
    filters.group
    & filters.regex(
        r"^مسح الرد\s+(.+)$"
    )
)
async def delete_auto_reply(
    _,
    message
):

    if not await require_admin(
        message
    ):
        return

    word = (
        message.matches[0]
        .group(1)
        .strip()
        .lower()
    )

    chat_id = str(
        message.chat.id
    )

    replies = auto_replies.setdefault(
        chat_id,
        {}
    )

    if word not in replies:

        await message.reply_text(
            "❌ الرد ده مش موجود."
        )

        return

    del replies[word]

    save_json(
        REPLIES_FILE,
        auto_replies
    )

    await message.reply_text(
        "✅ تم مسح الرد."
    )


# =========================================================
# تشغيل الرد التلقائي
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
)
async def auto_reply_handler(
    _,
    message
):

    chat_id = str(
        message.chat.id
    )

    replies = auto_replies.get(
        chat_id,
        {}
    )

    if not replies:
        return

    text = (
        message.text
        or ""
    ).strip().lower()

    if text in replies:

        await message.reply_text(
            replies[text]
        )


# =========================================================
# الأوامر
# =========================================================

@bot.on_message(
    filters.group
    & filters.regex(
        r"^الأوامر$"
    )
)
async def commands(
    _,
    message
):

    await message.reply_text(
        "📚 أوامر MariamMusicBot\n\n"

        "🎵 الموسيقى:\n"
        "• تشغيل + اسم الأغنية\n"
        "• تخطي\n"
        "• إيقاف\n"
        "• القائمة\n\n"

        "🎮 الألعاب:\n"
        "• العاب\n"
        "• اسم اللعبة\n"
        "• إيقاف اللعبة\n\n"

        "👮 الإدارة:\n"
        "• تفعيل البوت\n"
        "• تعطيل البوت\n"
        "• طرد بالرد\n"
        "• حظر بالرد\n"
        "• ترقية بالرد\n"
        "• تنزيل بالرد\n"
        "• منع السب\n"
        "• السماح بالسب\n\n"

        "💬 الردود:\n"
        "• اضف رد الكلمة الرد\n"
        "• مسح الرد الكلمة\n\n"

        "👤 الرتبة:\n"
        "• رتبتي"
    )


# =========================================================
# الرتبة
# =========================================================

@bot.on_message(
    filters.group
    & filters.regex(
        r"^رتبتي$"
    )
)
async def my_role(
    _,
    message
):

    role = await get_role(
        message
    )

    await message.reply_text(
        f"👤 رتبتك: {role}"
    )


# =========================================================
# الطرد والحظر
# =========================================================

@bot.on_message(
    filters.group
    & filters.regex(
        r"^(طرد|حظر)$"
    )
)
async def kick_ban(
    _,
    message
):

    if not await require_admin(
        message
    ):
        return

    target = await get_target(
        message
    )

    if not target:

        await message.reply_text(
            "↩️ اعمل رد على رسالة العضو "
            "واكتب طرد أو حظر."
        )

        return

    if (
        OWNER_ID
        and target.id == OWNER_ID
    ):

        await message.reply_text(
            "❌ مينفعش تعمل ده على المالك."
        )

        return

    command = (
        message.text.strip()
    )

    try:

        await bot.ban_chat_member(
            message.chat.id,
            target.id
        )

        if command == "طرد":

            await bot.unban_chat_member(
                message.chat.id,
                target.id
            )

            await message.reply_text(
                f"👢 تم طرد {target.first_name}."
            )

        else:

            await message.reply_text(
                f"🚫 تم حظر {target.first_name}."
            )

    except Exception:

        await message.reply_text(
            "❌ مقدرتش أنفذ الأمر.\n"
            "تأكد إن البوت أدمن وعنده "
            "صلاحية حظر الأعضاء."
        )


# =========================================================
# ترقية وتنزيل
# =========================================================

@bot.on_message(
    filters.group
    & filters.regex(
        r"^(ترقية|تنزيل)$"
    )
)
async def promote_demote(
    _,
    message
):

    if not await require_admin(
        message
    ):
        return

    target = await get_target(
        message
    )

    if not target:

        await message.reply_text(
            "↩️ اعمل رد على العضو."
        )

        return

    try:

        if message.text == "ترقية":

            await bot.promote_chat_member(
                message.chat.id,
                target.id,
                can_manage_chat=True,
                can_delete_messages=True,
                can_manage_video_chats=True,
                can_restrict_members=True,
                can_invite_users=True,
                can_pin_messages=True,
            )

            await message.reply_text(
                f"⬆️ تمت ترقية "
                f"{target.first_name}."
            )

        else:

            await bot.promote_chat_member(
                message.chat.id,
                target.id,
                can_manage_chat=False,
                can_delete_messages=False,
                can_manage_video_chats=False,
                can_restrict_members=False,
                can_invite_users=False,
                can_pin_messages=False,
            )

            await message.reply_text(
                f"⬇️ تم تنزيل "
                f"{target.first_name}."
            )

    except Exception:

        await message.reply_text(
            "❌ تأكد إن البوت أدمن "
            "وعنده صلاحية إدارة المشرفين."
        )


# =========================================================
# منع السب
# =========================================================

BAD_WORDS = {
    "كس",
    "خول",
    "شرموط",
    "شرموطة",
    "متناك",
    "منيك",
    "نيك",
    "قحبة",
}


@bot.on_message(
    filters.group
    & filters.regex(
        r"^منع السب$"
    )
)
async def enable_badwords(
    _,
    message
):

    if not await require_admin(
        message
    ):
        return

    badword_chats.add(
        message.chat.id
    )

    save_badwords()

    await message.reply_text(
        "🛡️ تم تفعيل منع السب."
    )


@bot.on_message(
    filters.group
    & filters.regex(
        r"^السماح بالسب$"
    )
)
async def disable_badwords(
    _,
    message
):

    if not await require_admin(
        message
    ):
        return

    badword_chats.discard(
        message.chat.id
    )

    save_badwords()

    await message.reply_text(
        "ℹ️ تم تعطيل منع السب."
    )


@bot.on_message(
    filters.group
    & filters.text
)
async def anti_badwords(
    _,
    message
):

    chat_id = message.chat.id

    if (
        chat_id not in active_chats
        or chat_id not in badword_chats
    ):
        return

    text = (
        message.text
        or ""
    ).lower()

    if any(
        word in text
        for word in BAD_WORDS
    ):

        try:

            await message.delete()

            await safe_send(
                chat_id,
                "🚫 ممنوع السب هنا."
            )

        except Exception:
            pass


# =========================================================
# الترحيب
# =========================================================

@bot.on_message(
    filters.group
    & filters.new_chat_members
)
async def welcome(
    _,
    message
):

    for user in message.new_chat_members:

        await safe_send(
            message.chat.id,
            f"👋 أهلاً يا {user.first_name} ❤️\n\n"
            "نورت الجروب.\n"
            "لو البوت متعطل اكتبوا:\n"
            "تفعيل البوت"
        )


# =========================================================
# /start
# =========================================================

@bot.on_message(
    filters.private
    & filters.command("start")
)
async def start_private(
    _,
    message
):

    # التحقق يتم في الخاص فقط
    # وليس مع كل رسالة في الجروب
    # لتجنب FloodWait

    if REQUIRED_CHANNEL:

        try:

            member = await bot.get_chat_member(
                REQUIRED_CHANNEL,
                message.from_user.id
            )

            if member.status in (
                ChatMemberStatus.LEFT,
                ChatMemberStatus.BANNED,
            ):

                await message.reply_text(
                    "🔒 لازم تشترك في القناة أولاً:\n\n"
                    f"https://t.me/"
                    f"{REQUIRED_CHANNEL.lstrip('@')}\n\n"
                    "وبعدها ابعت /start تاني."
                )

                return

        except FloodWait as e:

            await asyncio.sleep(
                int(e.value) + 1
            )

        except Exception:
            pass

    await message.reply_text(
        "👋 أهلاً بيك في MariamMusicBot ❤️\n\n"
        "ضيفني للجروب.\n"
        "وبعدها اكتب:\n"
        "تفعيل البوت\n\n"
        "ولعرض الأوامر:\n"
        "الأوامر"
    )


# =========================================================
# بدء البرنامج
# =========================================================

async def main():

    await bot.start()

    await assistant.start()

    voice.start()

    bot_info = await bot.get_me()

    log.info(
        "Bot started: @%s",
        bot_info.username
    )

    try:

        assistant_info = (
            await assistant.get_me()
        )

        log.info(
            "Assistant started: %s | %s",
            assistant_info.first_name,
            assistant_info.id
        )

    except Exception:
        pass

    if OWNER_ID:

        await safe_send(
            OWNER_ID,
            "✅ MariamMusicBot اشتغل بنجاح."
        )

    await idle()

    await assistant.stop()

    await bot.stop()


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        pass
