import os
import json
import random
import asyncio
from pathlib import Path
from collections import defaultdict, deque

import static_ffmpeg
static_ffmpeg.add_paths()

import pyrogram
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ChatType

try:
    from pytgcalls import PyTgCalls
    from pytgcalls.types import MediaStream, GroupCallConfig
except Exception:
    PyTgCalls = None
    MediaStream = None
    GroupCallConfig = None


# ==================================================
# الإعدادات
# ==================================================

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
SESSION_STRING = os.environ["SESSION_STRING"]

PHOTO_PATH = "IMG_20260922_130735_050.jpg"
CUSTOM_REPLIES_FILE = "custom_replies.json"

# لو عندك اشتراك إجباري حط يوزر القناة/الجروب هنا
# مثال:
# REQUIRED_CHAT = "@MyChannel"
#
# لو مش عايز اشتراك إجباري خليه فاضي.
REQUIRED_CHAT = os.getenv("REQUIRED_CHAT", "").strip()


# ==================================================
# تشغيل البوت والمساعد
# ==================================================

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

calls = PyTgCalls(assistant) if PyTgCalls else None


# ==================================================
# البيانات
# ==================================================

queues = defaultdict(deque)
current_tracks = {}
current_messages = {}

warnings = defaultdict(lambda: defaultdict(int))


WELCOME_MESSAGES = [
    "👋 أهلًا وسهلًا {name} ❤️ نورت الجروب!",
    "🌷 يا مرحبًا بـ {name} ❤️ نورت/ي المكان!",
    "💕 أهلًا {name} نتمنى لك وقت جميل معانا!",
    "✨ نورت/ي يا {name}!",
]


# ==================================================
# الردود الأساسية
# ==================================================

BUILTIN_REPLIES = {

    "السلام عليكم":
        "وعليكم السلام ورحمة الله وبركاته ❤️",

    "سلام عليكم":
        "وعليكم السلام يا جميل 🌷",

    "صباح الخير":
        "صباح النور والسرور ☀️❤️",

    "مساء الخير":
        "مساء النور يا جميل 🌙❤️",

    "ازيك":
        "الحمد لله تمام ❤️ وإنت؟",

    "إزيك":
        "الحمد لله تمام ❤️ وإنت؟",

    "عامل ايه":
        "تمام الحمد لله 😄",

    "عامل اي":
        "تمام الحمد لله 😄",

    "اخبارك":
        "تمام الحمد لله ❤️",

    "أخبارك":
        "تمام يا جميل ❤️",

    "اخباركم":
        "كلنا تمام ❤️",

    "أخباركم":
        "كلنا تمام ❤️",

    "شكرا":
        "العفو يا جميل ❤️",

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

    "😂":
        "😂❤️",

    "تصبح على خير":
        "وأنت من أهله 🌙❤️",

    "تصبحي على خير":
        "وأنتِ من أهله 🌙❤️",

    "منور":
        "ده نورك يا نجم ❤️",

    "منورة":
        "ده نورك يا قمر ❤️",

    "نورت":
        "ده نورك ❤️",

    "نورتي":
        "ده نورك يا قمر ❤️",

    "حلو":
        "إنت الأحلى 😎❤️",

    "حلوة":
        "إنتِ الأحلى ❤️",

    "جميل":
        "الجمال جمالك ❤️",

    "جميلة":
        "إنتِ الأجمل ❤️",

    "صح":
        "بالظبط 👌",

    "غلط":
        "ممكن نراجعها تاني 😄",

    "ايوه":
        "تمام ❤️",

    "أيوه":
        "تمام ❤️",

    "اه":
        "أيوه يا جميل 😄",

    "آه":
        "أيوه يا جميل 😄",

    "نعم":
        "نعم يا نجم ❤️",

    "لا":
        "براحتك 😂",

    "موافق":
        "تمام اتفقنا ❤️",

    "يا جماعة":
        "معاكم يا جماعة 👀❤️",

    "شباب":
        "قولوا يا شباب 😎",

    "حد هنا":
        "أيوه موجودين 👀❤️",

    "يا بنت":
        "نعم يا قمر 😂❤️",

    "يا معلم":
        "أؤمر يا معلم 😎",

    "يا معلمة":
        "أؤمري يا معلمة ❤️",

    "يا ملك":
        "تحت أمرك يا ملك 👑",

    "يا ملكة":
        "تحت أمرك يا ملكة 👑",

    "مبسوط":
        "دايمًا مبسوط يا رب ❤️",

    "مبسوطة":
        "دايمًا مبسوطة يا رب ❤️",

    "فرحان":
        "ربنا يديم الفرحة ❤️",

    "فرحانة":
        "ربنا يديم الفرحة ❤️",

    "زعلان":
        "مالك بس؟ ❤️",

    "زعلانة":
        "مالك بس يا قمر؟ ❤️",

    "تعبان":
        "سلامتك يا بطل ❤️",

    "تعبانة":
        "سلامتك يا قمر ❤️",

    "خايف":
        "متخافش إحنا معاك ❤️",

    "خايفة":
        "متخافيش إحنا معاكي ❤️",

    "مكسوف":
        "مفيش كسوف بينا 😂❤️",

    "مكسوفة":
        "مفيش كسوف بينا 😂❤️",

    "عاش":
        "عاش يا نجم 🔥",

    "برافو":
        "برافو عليك 👏❤️",

    "كفو":
        "تسلم يا بطل ❤️",

    "أحسنت":
        "تسلم ❤️",

    "شاطر":
        "تسلم يا بطل 😎",

    "شطورة":
        "تسلمي يا قمر ❤️",
}


# ==================================================
# ردود إضافية
# ==================================================

EXTRA_TRIGGERS = [
    "اخبارك",
    "أخبارك",
    "اخباركم",
    "أخباركم",
    "عاملين ايه",
    "عاملين اي",
    "حامد",
    "جامدة",
    "حلو",
    "حلوة",
    "جميل",
    "جميلة",
    "صح",
    "غلط",
    "ايوه",
    "أيوه",
    "اه",
    "آه",
    "نعم",
    "لا",
    "موافق",
    "يا جماعة",
    "شباب",
    "حد هنا",
    "يا بنت",
    "يا معلم",
    "يا معلمة",
    "يا ملك",
    "يا ملكة",
    "مبسوط",
    "مبسوطة",
    "فرحان",
    "فرحانة",
    "زعلان",
    "زعلانة",
    "تعبان",
    "تعبانة",
    "خايف",
    "خايفة",
    "مكسوف",
    "مكسوفة",
    "منور",
    "منورة",
    "نورتي",
    "نورت",
    "حامد اوي",
    "حلو اوي",
    "عاش",
    "برافو",
    "كفو",
    "أحسنت",
    "شطورة",
    "شاطر",
]


for trigger in EXTRA_TRIGGERS:
    BUILTIN_REPLIES.setdefault(
        trigger,
        random.choice([
            "تمام يا جميل ❤️",
            "يا سلام 😄❤️",
            "أيوه يا نجم 👀",
            "منورين يا جماعة ❤️",
            "حاضر 😎",
            "😂❤️",
        ])
    )


# ==================================================
# نظام الردود المخصصة
# ==================================================

def load_custom_replies():

    path = Path(CUSTOM_REPLIES_FILE)

    if not path.exists():
        return {}

    try:

        data = json.loads(
            path.read_text(encoding="utf-8")
        )

        if isinstance(data, dict):
            return data

    except Exception:
        pass

    return {}


custom_replies = load_custom_replies()


def save_custom_replies():

    Path(CUSTOM_REPLIES_FILE).write_text(
        json.dumps(
            custom_replies,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


# ==================================================
# أدوات مساعدة
# ==================================================

def normalize(text):

    return " ".join(
        (text or "").strip().lower().split()
    )


def chat_key(chat_id):

    return str(chat_id)


async def is_admin(message):

    if message.chat.type == ChatType.PRIVATE:
        return True

    try:

        member = await bot.get_chat_member(
            message.chat.id,
            message.from_user.id
        )

        return member.status in (
            "administrator",
            "owner"
        )

    except Exception:

        return False


async def is_user_joined(user_id):

    if not REQUIRED_CHAT:
        return True

    try:

        member = await bot.get_chat_member(
            REQUIRED_CHAT,
            user_id
        )

        return member.status not in (
            "kicked",
            "left"
        )

    except Exception:

        return False


def verification_keyboard():

    buttons = []

    if REQUIRED_CHAT:

        buttons.append([
            InlineKeyboardButton(
                "📢 انضم للمجموعة",
                url=f"https://t.me/{REQUIRED_CHAT.lstrip('@')}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "✅ تحقق",
            callback_data="check_join"
        )
    ])

    return InlineKeyboardMarkup(buttons)


async def send_verification(message):

    text = (
        "👋 أهلاً بيك!\n\n"
        "لاستخدام البوت، اضغط على زر الانضمام "
        "ثم اضغط «✅ تحقق»."
    )

    await message.reply_text(
        text,
        reply_markup=verification_keyboard()
    )


# ==================================================
# البحث عن الأغاني
# ==================================================

async def search_soundcloud(query):

    import yt_dlp

    options = {
        "quiet": True,
        "no_warnings": True,
        "default_search": "scsearch1",
        "extract_flat": False,
    }

    def search():

        with yt_dlp.YoutubeDL(options) as ydl:

            info = ydl.extract_info(
                f"scsearch1:{query}",
                download=False
            )

            entries = info.get("entries") or []

            if entries:
                return entries[0]

            return None

    return await asyncio.to_thread(search)


async def get_audio_url(info):

    import yt_dlp

    webpage_url = (
        info.get("webpage_url")
        or info.get("url")
    )

    if not webpage_url:
        return None

    options = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "noplaylist": True,
    }

    def extract():

        with yt_dlp.YoutubeDL(options) as ydl:

            data = ydl.extract_info(
                webpage_url,
                download=False
            )

            return data.get("url")

    return await asyncio.to_thread(extract)


def format_duration(seconds):

    try:
        seconds = int(seconds or 0)
    except Exception:
        return "غير معروف"

    return (
        f"{seconds // 60}:"
        f"{seconds % 60:02d}"
    )


# ==================================================
# أزرار الموسيقى
# ==================================================

def track_keyboard():

    return InlineKeyboardMarkup([
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
                "📜 القائمة",
                callback_data="music_queue"
            )
        ]
    ])


# ==================================================
# تشغيل أغنية
# ==================================================

async def play_track(
    chat_id,
    track,
    request_message=None
):

    if calls is None:

        raise RuntimeError(
            "PyTgCalls غير مثبت"
        )

    audio_url = await get_audio_url(track)

    if not audio_url:

        raise RuntimeError(
            "تعذر الحصول على رابط الصوت"
        )

    stream = MediaStream(
        audio_url,
        video_flags=MediaStream.Flags.IGNORE
    )

    config = GroupCallConfig(
        auto_start=True
    )

    await calls.play(
        chat_id,
        stream,
        config
    )

    current_tracks[chat_id] = track

    title = (
        track.get("title")
        or "أغنية بدون اسم"
    )

    duration = format_duration(
        track.get("duration")
    )

    username = "غير معروف"

    if (
        request_message
        and request_message.from_user
    ):

        username = (
            request_message
            .from_user
            .mention
        )

    caption = (
        "🎵 **مريومه الدلوعه**\n\n"
        f"🎶 **الأغنية:** {title}\n"
        f"⏱ **المدة:** {duration}\n"
        f"👤 **الطلب:** {username}"
    )

    if request_message:

        try:

            sent = await request_message.reply_photo(
                PHOTO_PATH,
                caption=caption,
                reply_markup=track_keyboard()
            )

            current_messages[chat_id] = sent.id

        except Exception:

            sent = await request_message.reply_text(
                caption,
                reply_markup=track_keyboard()
            )

            current_messages[chat_id] = sent.id


async def play_next(
    chat_id,
    source_message=None
):

    if not queues[chat_id]:

        current_tracks.pop(
            chat_id,
            None
        )

        return

    track = queues[chat_id].popleft()

    try:

        await play_track(
            chat_id,
            track,
            source_message
        )

    except Exception as error:

        if source_message:

            await source_message.reply_text(
                "❌ حصل خطأ أثناء التشغيل:\n"
                f"`{error}`"
            )

        if queues[chat_id]:

            await play_next(
                chat_id,
                source_message
            )


async def stop_music(chat_id):

    if calls is not None:

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

    current_messages.pop(
        chat_id,
        None
    )


# ==================================================
# التحقق الخاص
# ==================================================

@bot.on_callback_query(
    filters.regex("^check_join$")
)
async def check_join_callback(
    client,
    query: CallbackQuery
):

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
                "تقدر دلوقتي تضيفني لمجموعتك "
                "وتستخدم أوامر البوت."
            )

        except Exception:
            pass

    else:

        await query.answer(
            "❌ لسه ما تمش الانضمام.",
            show_alert=True
        )


@bot.on_message(
    filters.private
    & filters.command("start")
)
async def start_private(
    client,
    message
):

    if await is_user_joined(
        message.from_user.id
    ):

        await message.reply_text(
            "🎵 أهلاً بيك في مريومه الدلوعه ❤️\n\n"
            "أضفني لمجموعتك وابدأ بـ «تشغيل»."
        )

    else:

        await send_verification(
            message
        )


# ==================================================
# ترحيب الأعضاء الجدد
# ==================================================

@bot.on_message(
    filters.group
    & filters.new_chat_members
)
async def welcome_handler(
    client,
    message
):

    for member in message.new_chat_members:

        if member.is_bot:
            continue

        name = (
            member.first_name
            or "يا جميل"
        )

        text = random.choice(
            WELCOME_MESSAGES
        )

        text = text.replace(
            "{name}",
            name
        )

        await message.reply_text(
            text
        )


# ==================================================
# أزرار الموسيقى
# ==================================================

@bot.on_callback_query(
    filters.regex("^music_skip$")
)
async def callback_skip(
    client,
    query
):

    if not await is_admin(
        query.message
    ):

        return await query.answer(
            "❌ للأدمن فقط",
            show_alert=True
        )

    await query.answer(
        "⏭ تخطي"
    )

    chat_id = query.message.chat.id

    if calls is not None:

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
async def callback_stop(
    client,
    query
):

    if not await is_admin(
        query.message
    ):

        return await query.answer(
            "❌ للأدمن فقط",
            show_alert=True
        )

    await query.answer(
        "⏹ تم الإيقاف"
    )

    await stop_music(
        query.message.chat.id
    )

    await query.message.reply_text(
        "⏹ تم إيقاف التشغيل ومسح القائمة."
    )


@bot.on_callback_query(
    filters.regex("^music_queue$")
)
async def callback_queue(
    client,
    query
):

    chat_id = query.message.chat.id

    items = list(
        queues[chat_id]
    )

    if not items:

        return await query.answer(
            "📜 القائمة فاضية",
            show_alert=True
        )

    text = (
        "📜 **قائمة التشغيل:**\n\n"
    )

    for i, item in enumerate(
        items,
        1
    ):

        text += (
            f"{i}. "
            f"{item.get('title', 'بدون اسم')}\n"
        )

    await query.message.reply_text(
        text
    )


# ==================================================
# أوامر الجروبات
# ==================================================

@bot.on_message(
    filters.group
    & filters.text
)
async def group_handler(
    client,
    message
):

    text = (
        message.text
        or ""
    ).strip()

    low = normalize(
        text
    )

    # ----------------------------------------------
    # إضافة رد
    # ----------------------------------------------

    if low.startswith(
        "أضف رد "
    ):

        if not await is_admin(
            message
        ):

            return await message.reply_text(
                "❌ الأمر ده للأدمن فقط."
            )

        raw = text[
            len("أضف رد "):
        ].strip()

        if "=" not in raw:

            return await message.reply_text(
                "❌ الصيغة الصحيحة:\n\n"
                "`أضف رد الكلمة = الرد`"
            )

        trigger, reply = raw.split(
            "=",
            1
        )

        trigger = normalize(
            trigger
        )

        reply = reply.strip()

        if not trigger or not reply:

            return await message.reply_text(
                "❌ اكتب الكلمة والرد."
            )

        key = chat_key(
            message.chat.id
        )

        custom_replies.setdefault(
            key,
            {}
        )

        if (
            trigger
            not in custom_replies[key]
            and len(custom_replies[key]) >= 500
        ):

            return await message.reply_text(
                "❌ وصلت للحد الأقصى: "
                "500 رد في المجموعة."
            )

        custom_replies[key][trigger] = reply

        save_custom_replies()

        return await message.reply_text(
            "✅ تم إضافة الرد.\n\n"
            f"الكلمة: `{trigger}`\n"
            f"الرد: {reply}"
        )


    # ----------------------------------------------
    # حذف رد
    # ----------------------------------------------

    if low.startswith(
        "حذف رد "
    ):

        if not await is_admin(
            message
        ):

            return await message.reply_text(
                "❌ الأمر ده للأدمن فقط."
            )

        trigger = normalize(
            text[len("حذف رد "):]
        )

        key = chat_key(
            message.chat.id
        )

        if trigger in custom_replies.get(
            key,
            {}
        ):

            del custom_replies[key][
                trigger
            ]

            save_custom_replies()

            return await message.reply_text(
                "✅ تم حذف الرد."
            )

        return await message.reply_text(
            "❌ الرد ده مش موجود."
        )


    # ----------------------------------------------
    # عرض الردود
    # ----------------------------------------------

    if low == "الردود":

        key = chat_key(
            message.chat.id
        )

        data = custom_replies.get(
            key,
            {}
        )

        if not data:

            return await message.reply_text(
                "📭 مفيش ردود مضافة."
            )

        lines = [
            "📜 **الردود المضافة:**\n"
        ]

        for i, trigger in enumerate(
            data.keys(),
            1
        ):

            lines.append(
                f"{i}. `{trigger}`"
            )

        return await message.reply_text(
            "\n".join(lines)
        )


    # ----------------------------------------------
    # عدد الردود
    # ----------------------------------------------

    if low == "عدد الردود":

        key = chat_key(
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


    # ----------------------------------------------
    # مسح الردود
    # ----------------------------------------------

    if low == "مسح الردود":

        if not await is_admin(
            message
        ):

            return await message.reply_text(
                "❌ الأمر ده للأدمن فقط."
            )

        key = chat_key(
            message.chat.id
        )

        custom_replies[key] = {}

        save_custom_replies()

        return await message.reply_text(
            "🗑 تم مسح كل الردود."
        )


    # ----------------------------------------------
    # تشغيل
    # ----------------------------------------------

    if low == "تشغيل":

        return await message.reply_text(
            "🎵 قول اسم الأغنية."
        )


    # ----------------------------------------------
    # تشغيل + اسم الأغنية
    # ----------------------------------------------

    if low.startswith(
        "تشغيل "
    ):

        query = text[
            len("تشغيل "):
        ].strip()

        if not query:

            return await message.reply_text(
                "🎵 قول اسم الأغنية."
            )

        try:

            result = await search_soundcloud(
                query
            )

        except Exception as error:

            return await message.reply_text(
                "❌ فشل البحث:\n"
                f"`{error}`"
            )

        if not result:

            return await message.reply_text(
                "❌ ملقتش الأغنية."
            )

        queues[
            message.chat.id
        ].append(
            result
        )

        title = (
            result.get("title")
            or query
        )

        if message.chat.id in current_tracks:

            return await message.reply_text(
                "✅ اتضافت للقائمة:\n"
                f"🎵 {title}"
            )

        await message.reply_text(
            "🔎 تم العثور على:\n"
            f"🎵 {title}\n"
            "▶️ جاري التشغيل..."
        )

        return await play_next(
            message.chat.id,
            message
        )


    # ----------------------------------------------
    # تخطي
    # ----------------------------------------------

    if low == "تخطي":

        if not await is_admin(
            message
        ):

            return await message.reply_text(
                "❌ التخطي للأدمن فقط."
            )

        if calls is not None:

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


    # ----------------------------------------------
    # وقف / إيقاف
    # ----------------------------------------------

    if low in (
        "وقف",
        "إيقاف"
    ):

        if not await is_admin(
            message
        ):

            return await message.reply_text(
                "❌ الأمر ده للأدمن فقط."
            )

        await stop_music(
            message.chat.id
        )

        return await message.reply_text(
            "⏹ تم إيقاف التشغيل ومسح القائمة."
        )


    # ----------------------------------------------
    # القائمة
    # ----------------------------------------------

    if low == "القائمة":

        items = list(
            queues[
                message.chat.id
            ]
        )

        if not items:

            return await message.reply_text(
                "📭 القائمة فاضية."
            )

        lines = [
            "📜 **قائمة التشغيل:**\n"
        ]

        for i, item in enumerate(
            items,
            1
        ):

            lines.append(
                f"{i}. "
                f"{item.get('title', 'بدون اسم')}"
            )

        return await message.reply_text(
            "\n".join(lines)
        )


    # ----------------------------------------------
    # الردود المخصصة
    # ----------------------------------------------

    key = chat_key(
        message.chat.id
    )

    custom = custom_replies.get(
        key,
        {}
    )

    if low in custom:

        return await message.reply_text(
            custom[low]
        )


    # ----------------------------------------------
    # الردود الجاهزة
    # ----------------------------------------------

    if low in BUILTIN_REPLIES:

        return await message.reply_text(
            BUILTIN_REPLIES[low]
        )


# ==================================================
# تشغيل البرنامج
# ==================================================

async def main():

    await assistant.start()

    await bot.start()

    print(
        "MariamMusicBot is running."
    )

    if calls is not None:

        calls.start()

    await asyncio.Event().wait()


if __name__ == "__main__":

    asyncio.run(
        main()
    )
