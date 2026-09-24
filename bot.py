# ============================================================
# MariamMusicBot
# Music + Moderation + Replies + Welcome + Games
# ============================================================

import os
import json
import random
import asyncio
from pathlib import Path

import static_ffmpeg
static_ffmpeg.add_paths()

from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatPrivileges,
    ChatPermissions,
)

from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, GroupCallConfig

import yt_dlp


# ============================================================
# ENV
# ============================================================

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
SESSION_STRING = os.environ["SESSION_STRING"]

# اسم الصورة التي رفعتها في GitHub
PHOTO_PATH = "IMG_20260922_130735_050.jpg"


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


calls = None


# ============================================================
# COMPATIBILITY
# ============================================================

try:
    import pyrogram.errors

    if not hasattr(pyrogram.errors, "GroupcallForbidden"):
        if hasattr(pyrogram.errors, "GroupCallForbidden"):
            pyrogram.errors.GroupcallForbidden = (
                pyrogram.errors.GroupCallForbidden
            )
        else:
            class GroupcallForbidden(Exception):
                pass

            pyrogram.errors.GroupcallForbidden = GroupcallForbidden

    if not hasattr(pyrogram.errors, "GroupcallInvalid"):
        if hasattr(pyrogram.errors, "GroupCallInvalid"):
            pyrogram.errors.GroupcallInvalid = (
                pyrogram.errors.GroupCallInvalid
            )
        else:
            class GroupcallInvalid(Exception):
                pass

            pyrogram.errors.GroupcallInvalid = GroupcallInvalid

except Exception:
    pass


# ============================================================
# DATA
# ============================================================

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

CUSTOM_FILE = DATA_DIR / "custom_replies.json"
SETTINGS_FILE = DATA_DIR / "group_settings.json"
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
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2,
            )
    except Exception as e:
        print("SAVE ERROR:", e)


custom_replies = load_json(CUSTOM_FILE, {})
group_settings = load_json(SETTINGS_FILE, {})
warnings_data = load_json(WARNINGS_FILE, {})


# ============================================================
# RUNTIME DATA
# ============================================================

music_queue = {}
current_song = {}
waiting_song = {}

game_sessions = {}

downloaded_files = set()


# ============================================================
# BAD WORDS
# ============================================================
# ضع الكلمات التي تريد منعها هنا.
# هذه مجرد أمثلة وليست قائمة شتائم جاهزة.

BAD_WORDS = {
    "كلمة_ممنوعة_1",
    "كلمة_ممنوعة_2",
}


# ============================================================
# GAMES
# ============================================================

GAME_NAMES = [
    "اكس او",
    "حجر ورق مقص",
    "تخمين الرقم",
    "تحدي الحساب",
    "اسرع إجابة",
    "صح او خطأ",
    "خمن الكلمة",
    "خمن الحيوان",
    "خمن الدولة",
    "خمن اللاعب",
    "خمن الفيلم",
    "خمن الأغنية",
    "خمن الشخصية",
    "خمن السيارة",
    "خمن اللون",
    "خمن الرقم السري",
    "سؤال وجواب",
    "ثقافة عامة",
    "معلومات عامة",
    "تحدي الذكاء",
    "تحدي الذاكرة",
    "تحدي السرعة",
    "تحدي الحروف",
    "تحدي الكلمات",
    "كلمة من 5 حروف",
    "كلمة من 6 حروف",
    "رتب الحروف",
    "اكمل الكلمة",
    "اكمل الجملة",
    "اكمل المثل",
    "اكمل الأغنية",
    "اكمل الفيلم",
    "مين أنا",
    "مين اللاعب",
    "مين المغني",
    "مين الممثل",
    "مين الحيوان",
    "مين الدولة",
    "مين السيارة",
    "مين الشخصية",
    "مين الأسرع",
    "مين يعرف أكثر",
    "اختبار الذكاء",
    "اختبار الذاكرة",
    "اختبار السرعة",
    "اختبار الثقافة",
    "اختبار الجغرافيا",
    "اختبار التاريخ",
    "اختبار الرياضة",
    "اختبار السيارات",
    "اختبار الأفلام",
    "اختبار الأغاني",
    "اختبار الحيوانات",
    "اختبار الدول",
    "اختبار الشخصيات",
    "مسابقة عامة",
    "مسابقة رياضية",
    "مسابقة سيارات",
    "مسابقة أفلام",
    "مسابقة أغاني",
    "مسابقة حيوانات",
    "مسابقة دول",
    "مسابقة تاريخ",
    "مسابقة جغرافيا",
    "مسابقة علوم",
    "مسابقة تقنية",
    "مسابقة ألعاب",
    "مسابقة كرة قدم",
    "مسابقة كرة سلة",
    "مسابقة سباق",
    "مسابقة ذكاء",
    "مسابقة سرعة",
    "مسابقة حروف",
    "مسابقة كلمات",
    "مسابقة أرقام",
    "مسابقة ألوان",
    "مسابقة شخصيات",
    "مسابقة مشاهير",
    "تحدي كرة القدم",
    "تحدي كرة السلة",
    "تحدي السيارات",
    "تحدي الألعاب",
    "تحدي الأفلام",
    "تحدي المسلسلات",
    "تحدي الأنمي",
    "تحدي الكرتون",
    "تحدي المشاهير",
    "تحدي الأغاني",
    "تحدي الراب",
    "تحدي الميمز",
    "تحدي تيك توك",
    "تحدي يوتيوب",
    "تحدي انستجرام",
    "تحدي الكمبيوتر",
    "تحدي البرمجة",
    "تحدي الإنترنت",
    "تحدي التكنولوجيا",
    "تحدي العلوم",
    "تحدي الفضاء",
    "تحدي الطبيعة",
    "تحدي الحيوانات",
    "تحدي البحار",
    "تحدي البلدان",
    "تحدي العواصم",
    "تحدي العملات",
    "تحدي التاريخ",
    "تحدي الحضارات",
    "تحدي اللغة",
    "تحدي الإنجليزية",
    "تحدي العربية",
    "تحدي الرياضيات",
    "تحدي الجمع",
    "تحدي الطرح",
    "تحدي الضرب",
    "تحدي القسمة",
    "صيد الكلمات",
    "صيد الرقم",
    "صيد الحروف",
    "صيد اللون",
    "صيد الكلمة",
    "سباق الكلمات",
    "سباق الأرقام",
    "سباق الحروف",
    "سباق الإجابة",
    "سباق الحساب",
]


TWO_PLAYER_GAMES = {
    "اكس او",
    "حجر ورق مقص",
    "سباق الكلمات",
    "سباق الأرقام",
    "سباق الحروف",
    "سباق الإجابة",
    "تحدي السرعة",
    "تحدي الذكاء",
    "مين أنا",
    "خمن الكلمة",
    "خمن الرقم السري",
}


# ============================================================
# GAME HELPERS
# ============================================================

def normalize(text):
    return " ".join(text.strip().lower().split())


def game_key(name):
    return normalize(name)


def game_exists(name):
    key = game_key(name)

    for game in GAME_NAMES:
        if game_key(game) == key:
            return game

    return None


def user_name(user):
    if not user:
        return "لاعب"

    name = user.first_name or "لاعب"

    if user.last_name:
        name += " " + user.last_name

    return name


async def create_game(chat_id, game_name, user):
    game = game_exists(game_name)

    if not game:
        return False

    key = game_key(game)

    game_sessions[chat_id] = {
        "name": game,
        "key": key,
        "creator": user.id,
        "creator_name": user_name(user),
        "players": [user.id],
        "started": False,
        "answer": None,
        "number": None,
    }

    return True


def game_buttons(chat_id):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "👤 انضم للعبة",
                    callback_data=f"game_join:{chat_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "▶️ بدء اللعبة",
                    callback_data=f"game_start:{chat_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ إلغاء",
                    callback_data=f"game_cancel:{chat_id}",
                )
            ],
        ]
    )


async def start_game(chat_id, session):
    session["started"] = True

    name = session["name"]

    # XO
    if name == "اكس او":
        session["board"] = ["⬜"] * 9
        session["turn"] = session["players"][0]

        return (
            "❌⭕ **بدأت لعبة XO!**\n\n"
            "❌ = اللاعب الأول\n"
            "⭕ = اللاعب الثاني\n\n"
            "اختاروا رقم الخانة من 1 إلى 9."
        )

    # RPS
    if name == "حجر ورق مقص":
        return (
            "✊✋✌️ **حجر ورق مقص**\n\n"
            "كل لاعب يختار حركته من الأزرار."
        )

    # Guess number
    if name == "تخمين الرقم":
        number = random.randint(1, 100)
        session["number"] = number

        return (
            "🎯 **تخمين الرقم**\n\n"
            "أنا اخترت رقمًا من 1 إلى 100.\n"
            "اكتب تخمينك."
        )

    # Math
    if "حساب" in name or "رياضيات" in name:
        a = random.randint(2, 30)
        b = random.randint(2, 30)
        op = random.choice(["+", "-", "*"])

        if op == "+":
            answer = a + b
        elif op == "-":
            answer = a - b
        else:
            answer = a * b

        session["answer"] = str(answer)

        return (
            f"🧮 **تحدي الحساب**\n\n"
            f"كم يساوي:\n\n"
            f"`{a} {op} {b}`"
        )

    return (
        f"🎮 **{name}**\n\n"
        f"بدأت اللعبة!\n"
        f"اللاعبون: {len(session['players'])}\n\n"
        f"⚡ اكتب إجابتك للمشاركة."
    )


# ============================================================
# ADMIN HELPERS
# ============================================================

async def is_admin(client, chat_id, user_id):
    try:
        member = await client.get_chat_member(
            chat_id,
            user_id,
        )

        status = str(member.status).lower()

        return (
            "owner" in status
            or "creator" in status
            or "administrator" in status
            or status == "admin"
        )

    except Exception:
        return False


async def is_owner(client, chat_id, user_id):
    try:
        member = await client.get_chat_member(
            chat_id,
            user_id,
        )

        status = str(member.status).lower()

        return (
            "owner" in status
            or "creator" in status
        )

    except Exception:
        return False


async def require_admin(message):
    if not message.from_user:
        return False

    if await is_admin(
        bot,
        message.chat.id,
        message.from_user.id,
    ):
        return True

    await message.reply_text(
        "❌ الأمر ده للمشرفين فقط."
    )

    return False


# ============================================================
# GROUP ENABLE / DISABLE
# ============================================================

def group_enabled(chat_id):
    return bool(
        group_settings.get(
            str(chat_id),
            False,
        )
    )


def set_group_enabled(chat_id, value):
    group_settings[str(chat_id)] = value
    save_json(SETTINGS_FILE, group_settings)


# ============================================================
# SETTINGS
# ============================================================

def get_settings(chat_id):
    key = str(chat_id)

    if key not in group_settings:
        group_settings[key] = {
            "enabled": False,
            "links": False,
            "photos": False,
            "videos": False,
            "stickers": False,
            "audio": False,
            "bad_words": False,
        }
        save_json(SETTINGS_FILE, group_settings)

    # compatibility with old boolean format
    if isinstance(group_settings[key], bool):
        group_settings[key] = {
            "enabled": group_settings[key],
            "links": False,
            "photos": False,
            "videos": False,
            "stickers": False,
            "audio": False,
            "bad_words": False,
        }
        save_json(SETTINGS_FILE, group_settings)

    return group_settings[key]


# ============================================================
# WARNINGS
# ============================================================

def warning_key(chat_id, user_id):
    return f"{chat_id}:{user_id}"


def get_warning_count(chat_id, user_id):
    return int(
        warnings_data.get(
            warning_key(chat_id, user_id),
            0,
        )
    )


def add_warning(chat_id, user_id):
    key = warning_key(chat_id, user_id)

    warnings_data[key] = (
        get_warning_count(chat_id, user_id) + 1
    )

    save_json(WARNINGS_FILE, warnings_data)

    return warnings_data[key]


def clear_warnings(chat_id, user_id):
    key = warning_key(chat_id, user_id)

    warnings_data.pop(key, None)

    save_json(WARNINGS_FILE, warnings_data)


# ============================================================
# CUSTOM REPLIES
# ============================================================

def get_group_replies(chat_id):
    key = str(chat_id)

    if key not in custom_replies:
        custom_replies[key] = {}

    return custom_replies[key]


# ============================================================
# MUSIC SEARCH
# ============================================================

async def download_song(query):
    """
    SoundCloud first.
    YouTube second.
    """

    loop = asyncio.get_running_loop()

    def worker():
        output_dir = Path("downloads")
        output_dir.mkdir(exist_ok=True)

        # ----------------------------------------------------
        # SoundCloud
        # ----------------------------------------------------

        soundcloud_options = {
            "format": "bestaudio/best",
            "outtmpl": str(
                output_dir / "%(id)s.%(ext)s"
            ),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }

        try:
            with yt_dlp.YoutubeDL(
                soundcloud_options
            ) as ydl:

                info = ydl.extract_info(
                    f"scsearch1:{query}",
                    download=True,
                )

                if info and "entries" in info:
                    info = info["entries"][0]

                if info:
                    requested = Path(
                        ydl.prepare_filename(info)
                    )

                    mp3 = requested.with_suffix(".mp3")

                    if mp3.exists():
                        return {
                            "path": str(mp3),
                            "title": info.get(
                                "title",
                                query,
                            ),
                            "duration": info.get(
                                "duration",
                                0,
                            ),
                        }

        except Exception as e:
            print(
                "SoundCloud ERROR:",
                repr(e),
            )

        # ----------------------------------------------------
        # YouTube
        # ----------------------------------------------------

        youtube_options = {
            "format": "bestaudio/best",
            "outtmpl": str(
                output_dir / "%(id)s.%(ext)s"
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
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }

        with yt_dlp.YoutubeDL(
            youtube_options
        ) as ydl:

            info = ydl.extract_info(
                f"ytsearch1:{query}",
                download=True,
            )

            if info and "entries" in info:
                info = info["entries"][0]

            if not info:
                raise RuntimeError(
                    "لم يتم العثور على الأغنية"
                )

            requested = Path(
                ydl.prepare_filename(info)
            )

            mp3 = requested.with_suffix(".mp3")

            if not mp3.exists():
                raise RuntimeError(
                    "فشل استخراج ملف الصوت"
                )

            return {
                "path": str(mp3),
                "title": info.get(
                    "title",
                    query,
                ),
                "duration": info.get(
                    "duration",
                    0,
                ),
            }

    return await loop.run_in_executor(
        None,
        worker,
    )


def format_duration(seconds):
    try:
        seconds = int(seconds or 0)
    except Exception:
        seconds = 0

    minutes = seconds // 60
    seconds = seconds % 60

    return f"{minutes:02d}:{seconds:02d}"


# ============================================================
# NOW PLAYING
# ============================================================

def music_buttons(chat_id):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⏭ تخطي",
                    callback_data=f"music_skip:{chat_id}",
                ),
                InlineKeyboardButton(
                    "⏹ وقف",
                    callback_data=f"music_stop:{chat_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "📋 القائمة",
                    callback_data=f"music_queue:{chat_id}",
                ),
            ],
        ]
    )


async def send_now_playing(chat_id, song):
    duration = format_duration(
        song.get("duration", 0)
    )

    caption = (
        "🎵 **مريومه الدلوعه**\n\n"
        f"🎶 **الأغنية:** {song['title']}\n"
        f"⏱ **المدة:** {duration}\n"
        f"👤 **طلبها:** {song.get('requester', 'عضو')}\n\n"
        "🔊 يتم التشغيل في المحادثة الصوتية..."
    )

    try:
        if os.path.exists(PHOTO_PATH):
            return await bot.send_photo(
                chat_id,
                PHOTO_PATH,
                caption=caption,
                reply_markup=music_buttons(chat_id),
            )

        return await bot.send_message(
            chat_id,
            caption,
            reply_markup=music_buttons(chat_id),
        )

    except Exception as e:
        print(
            "NOW PLAYING ERROR:",
            repr(e),
        )


# ============================================================
# PLAY MUSIC
# ============================================================

async def play_next(chat_id):
    global calls

    queue = music_queue.setdefault(
        chat_id,
        [],
    )

    if not queue:
        current_song.pop(chat_id, None)

        try:
            if calls:
                await calls.leave_call(chat_id)
        except Exception:
            pass

        return

    song = queue.pop(0)
    current_song[chat_id] = song

    try:
        stream = MediaStream(
            song["path"]
        )

        await calls.play(
            chat_id,
            stream,
            GroupCallConfig(
                auto_start=True
            ),
        )

        await send_now_playing(
            chat_id,
            song,
        )

    except Exception as e:
        print(
            "PLAY ERROR:",
            repr(e),
        )

        current_song.pop(chat_id, None)

        await bot.send_message(
            chat_id,
            "❌ حصل خطأ أثناء تشغيل الأغنية.\n\n"
            f"`{e}`",
        )


async def add_song(
    chat_id,
    query,
    requester,
):
    try:
        msg = await bot.send_message(
            chat_id,
            "🔎 بدور على الأغنية...",
        )

        song = await download_song(query)

        song["requester"] = requester

        queue = music_queue.setdefault(
            chat_id,
            [],
        )

        if current_song.get(chat_id):
            queue.append(song)

            await msg.edit_text(
                "✅ تمت إضافة الأغنية للقائمة.\n"
                f"🎵 {song['title']}\n"
                f"📌 ترتيبها: {len(queue)}"
            )

        else:
            await msg.delete()
            await play_next(chat_id)

    except Exception as e:
        print(
            "ADD SONG ERROR:",
            repr(e),
        )

        await bot.send_message(
            chat_id,
            "❌ مش قادر أجيب الأغنية دلوقتي.\n\n"
            f"`{e}`",
        )


# ============================================================
# MUSIC COMMANDS
# ============================================================

async def music_play_command(message, query):
    if not group_enabled(message.chat.id):
        return

    if not query:
        waiting_song[message.chat.id] = (
            message.from_user.id
        )

        await message.reply_text(
            "🎵 قول اسم الأغنية."
        )

        return

    await add_song(
        message.chat.id,
        query,
        user_name(message.from_user),
    )


async def skip_song(chat_id):
    global calls

    try:
        if calls:
            await calls.leave_call(chat_id)
    except Exception:
        pass

    current_song.pop(chat_id, None)

    await play_next(chat_id)


async def stop_music(chat_id):
    global calls

    music_queue[chat_id] = []
    current_song.pop(chat_id, None)

    try:
        if calls:
            await calls.leave_call(chat_id)
    except Exception:
        pass


# ============================================================
# HELP
# ============================================================

HELP_TEXT = """
🎀 **أوامر مريومه الدلوعه**

🎵 **الموسيقى**
• تشغيل
• تشغيل اسم الأغنية
• تخطي
• وقف
• إيقاف
• القائمة

⚙️ **تشغيل البوت**
• تفعيل البوت
• تعطيل البوت

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

🛡 **الحماية**
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

🎮 **الألعاب**
• العاب

ℹ️ **أخرى**
• الأوامر
• مساعدة
"""


# ============================================================
# GROUP MAIN HANDLER
# ============================================================

@bot.on_message(
    filters.group & filters.text
)
async def group_handler(_, message):

    if not message.text:
        return

    text = message.text.strip()
    normalized = normalize(text)

    chat_id = message.chat.id
    user = message.from_user

    if not user:
        return

    # --------------------------------------------------------
    # ENABLE
    # --------------------------------------------------------

    if normalized == "تفعيل البوت":

        if not await require_admin(message):
            return

        set_group_enabled(
            chat_id,
            True,
        )

        settings = get_settings(chat_id)

        if isinstance(settings, dict):
            settings["enabled"] = True
            save_json(
                SETTINGS_FILE,
                group_settings,
            )

        await message.reply_text(
            "✅ تم تفعيل البوت في المجموعة."
        )

        return

    # --------------------------------------------------------
    # DISABLE
    # --------------------------------------------------------

    if normalized == "تعطيل البوت":

        if not await require_admin(message):
            return

        set_group_enabled(
            chat_id,
            False,
        )

        settings = get_settings(chat_id)

        if isinstance(settings, dict):
            settings["enabled"] = False
            save_json(
                SETTINGS_FILE,
                group_settings,
            )

        await message.reply_text(
            "⛔ تم تعطيل البوت في المجموعة."
        )

        return

    # --------------------------------------------------------
    # COMMANDS
    # --------------------------------------------------------

    if normalized in {
        "الأوامر",
        "الاوامر",
        "مساعدة",
        "ساعدني",
    }:

        await message.reply_text(
            HELP_TEXT
        )

        return

    # --------------------------------------------------------
    # BOT DISABLED
    # --------------------------------------------------------

    if not group_enabled(chat_id):
        return

    # --------------------------------------------------------
    # MUSIC
    # --------------------------------------------------------

    if normalized == "تشغيل":

        waiting_song[chat_id] = user.id

        await message.reply_text(
            "🎵 قول اسم الأغنية."
        )

        return

    if normalized.startswith("تشغيل "):

        query = text[7:].strip()

        waiting_song.pop(
            chat_id,
            None,
        )

        await music_play_command(
            message,
            query,
        )

        return

    if normalized in {
        "تخطي",
        "التالي",
    }:

        if not await require_admin(message):
            return

        await skip_song(chat_id)

        await message.reply_text(
            "⏭ تم تخطي الأغنية."
        )

        return

    if normalized in {
        "وقف",
        "إيقاف",
        "ايقاف",
    }:

        if not await require_admin(message):
            return

        await stop_music(chat_id)

        await message.reply_text(
            "⏹ تم إيقاف التشغيل ومسح القائمة."
        )

        return

    if normalized in {
        "القائمة",
        "قائمة التشغيل",
    }:

        queue = music_queue.get(
            chat_id,
            [],
        )

        now = current_song.get(
            chat_id
        )

        lines = []

        if now:
            lines.append(
                f"▶️ الآن: {now['title']}"
            )

        if queue:
            for i, song in enumerate(
                queue,
                start=1,
            ):
                lines.append(
                    f"{i}. {song['title']}"
                )

        if not lines:
            await message.reply_text(
                "📭 القائمة فاضية."
            )
        else:
            await message.reply_text(
                "🎵 **قائمة التشغيل**\n\n"
                + "\n".join(lines)
            )

        return

    # --------------------------------------------------------
    # WAITING FOR SONG
    # --------------------------------------------------------

    if chat_id in waiting_song:

        if normalized not in {
            "تفعيل البوت",
            "تعطيل البوت",
            "الأوامر",
            "الاوامر",
        }:

            waiting_song.pop(
                chat_id,
                None,
            )

            await add_song(
                chat_id,
                text,
                user_name(user),
            )

            return

    # --------------------------------------------------------
    # GAMES LIST
    # --------------------------------------------------------

    if normalized in {
        "العاب",
        "الألعاب",
        "لعب",
    }:

        lines = [
            "🎮 **قائمة الألعاب**",
            "",
            f"📌 عدد الألعاب: {len(GAME_NAMES)}",
            "",
        ]

        for i, game in enumerate(
            GAME_NAMES,
            start=1,
        ):

            icon = (
                "👥"
                if game in TWO_PLAYER_GAMES
                else "👤"
            )

            lines.append(
                f"{i}. {icon} {game}"
            )

        # Telegram message limit protection
        chunks = []

        current = ""

        for line in lines:

            if len(current) + len(line) + 1 > 3800:

                chunks.append(current)
                current = ""

            current += line + "\n"

        if current:
            chunks.append(current)

        for chunk in chunks:
            await message.reply_text(
                chunk
            )

        return

    # --------------------------------------------------------
    # START GAME BY NAME
    # --------------------------------------------------------

    selected_game = game_exists(text)

    if selected_game:

        if chat_id in game_sessions:
            await message.reply_text(
                "🎮 في لعبة شغالة بالفعل.\n"
                "اقفل اللعبة الحالية الأول."
            )
            return

        await create_game(
            chat_id,
            selected_game,
            user,
        )

        session = game_sessions[chat_id]

        if selected_game in TWO_PLAYER_GAMES:

            await message.reply_text(
                f"🎮 **{selected_game}**\n\n"
                f"👤 اللاعب الأول: "
                f"{user_name(user)}\n\n"
                "👥 محتاجين لاعب تاني.\n"
                "اضغط انضم للعبة، وبعدها ابدأ اللعبة.",
                reply_markup=game_buttons(
                    chat_id
                ),
            )

        else:

            text_result = await start_game(
                chat_id,
                session,
            )

            markup = None

            if selected_game in {
                "حجر ورق مقص",
            }:

                markup = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "✊ حجر",
                                callback_data=f"rps:{chat_id}:rock",
                            ),
                            InlineKeyboardButton(
                                "✋ ورق",
                                callback_data=f"rps:{chat_id}:paper",
                            ),
                            InlineKeyboardButton(
                                "✌️ مقص",
                                callback_data=f"rps:{chat_id}:scissors",
                            ),
                        ]
                    ]
                )

            await message.reply_text(
                text_result,
                reply_markup=markup,
            )

        return

    # --------------------------------------------------------
    # CUSTOM REPLIES
    # --------------------------------------------------------

    replies = get_group_replies(
        chat_id
    )

    if normalized in replies:

        await message.reply_text(
            replies[normalized]
        )

        return

    # --------------------------------------------------------
    # ADD REPLY
    # --------------------------------------------------------

    if normalized.startswith(
        "اضف رد "
    ) or normalized.startswith(
        "أضف رد "
    ):

        if not await require_admin(message):
            return

        content = text.split(
            " ",
            2,
        )

        if len(content) < 3:
            await message.reply_text(
                "❌ استخدم:\n"
                "`أضف رد الكلمة = الرد`"
            )
            return

        data = content[2]

        if "=" not in data:
            await message.reply_text(
                "❌ لازم تستخدم =\n"
                "`أضف رد السلام = وعليكم السلام`"
            )
            return

        trigger, reply = data.split(
            "=",
            1,
        )

        trigger = normalize(trigger)
        reply = reply.strip()

        if not trigger or not reply:
            await message.reply_text(
                "❌ البيانات ناقصة."
            )
            return

        replies = get_group_replies(
            chat_id
        )

        if len(replies) >= 500:
            await message.reply_text(
                "❌ وصلت للحد الأقصى: 500 رد."
            )
            return

        replies[trigger] = reply

        save_json(
            CUSTOM_FILE,
            custom_replies,
        )

        await message.reply_text(
            "✅ تم إضافة الرد."
        )

        return

    # --------------------------------------------------------
    # DELETE REPLY
    # --------------------------------------------------------

    if normalized.startswith(
        "مسح رد "
    ):

        if not await require_admin(message):
            return

        trigger = normalize(
            text[8:]
        )

        replies = get_group_replies(
            chat_id
        )

        if trigger not in replies:
            await message.reply_text(
                "❌ الرد مش موجود."
            )
            return

        del replies[trigger]

        save_json(
            CUSTOM_FILE,
            custom_replies,
        )

        await message.reply_text(
            "✅ تم حذف الرد."
        )

        return

    # --------------------------------------------------------
    # RANK
    # --------------------------------------------------------

    if normalized == "رتبتي":

        member = await bot.get_chat_member(
            chat_id,
            user.id,
        )

        status = str(
            member.status
        ).lower()

        if (
            "owner" in status
            or "creator" in status
        ):
            rank = "👑 مالك المجموعة"

        elif (
            "administrator" in status
            or status == "admin"
        ):
            rank = "🛡 مشرف"

        else:
            rank = "👤 عضو"

        await message.reply_text(
            f"📊 رتبتك: {rank}"
        )

        return

    # --------------------------------------------------------
    # OWNER
    # --------------------------------------------------------

    if normalized == "المالك":

        owners = []

        try:
            async for member in bot.get_chat_members(
                chat_id,
                filter=__import__(
                    "pyrogram"
                ).enums.ChatMembersFilter.ADMINISTRATORS,
            ):

                status = str(
                    member.status
                ).lower()

                if (
                    "owner" in status
                    or "creator" in status
                ):

                    owners.append(
                        member.user
                    )

        except Exception:
            pass

        if not owners:
            await message.reply_text(
                "❌ لم أقدر أجيب المالك."
            )
            return

        text_owner = "👑 **مالك المجموعة:**\n\n"

        for owner in owners:
            text_owner += (
                f"• {user_name(owner)}\n"
            )

        await message.reply_text(
            text_owner
        )

        return

    # --------------------------------------------------------
    # ADMINS
    # --------------------------------------------------------

    if normalized == "المشرفين":

        admins = []

        try:
            async for member in bot.get_chat_members(
                chat_id,
                filter=__import__(
                    "pyrogram"
                ).enums.ChatMembersFilter.ADMINISTRATORS,
            ):

                status = str(
                    member.status
                ).lower()

                if (
                    "administrator" in status
                    or status == "admin"
                    or "owner" in status
                    or "creator" in status
                ):

                    admins.append(
                        member.user
                    )

        except Exception:
            pass

        if not admins:
            await message.reply_text(
                "❌ لم أقدر أجيب المشرفين."
            )
            return

        text_admins = "🛡 **مشرفين المجموعة:**\n\n"

        for admin in admins:
            text_admins += (
                f"• {user_name(admin)}\n"
            )

        await message.reply_text(
            text_admins
        )

        return

    # --------------------------------------------------------
    # TARGET USER
    # --------------------------------------------------------

    async def get_target():

        if message.reply_to_message:
            return (
                message.reply_to_message.from_user
            )

        parts = text.split()

        if len(parts) >= 2:
            try:
                return await bot.get_users(
                    parts[1]
                )
            except Exception:
                pass

        return None

    # --------------------------------------------------------
    # PROMOTE
    # --------------------------------------------------------

    if normalized == "ترقية":

        if not await require_admin(message):
            return

        target = await get_target()

        if not target:
            await message.reply_text(
                "❌ اعمل Reply على الشخص واكتب ترقية."
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
                chat_id,
                target.id,
                privileges=privileges,
            )

            await message.reply_text(
                f"✅ تمت ترقية {user_name(target)}."
            )

        except Exception as e:
            await message.reply_text(
                f"❌ فشل الترقية:\n`{e}`"
            )

        return

    # --------------------------------------------------------
    # DEMOTE
    # --------------------------------------------------------

    if normalized == "تنزيل":

        if not await require_admin(message):
            return

        target = await get_target()

        if not target:
            await message.reply_text(
                "❌ اعمل Reply على الشخص واكتب تنزيل."
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
                chat_id,
                target.id,
                privileges=privileges,
            )

            await message.reply_text(
                f"✅ تم تنزيل {user_name(target)}."
            )

        except Exception as e:
            await message.reply_text(
                f"❌ فشل التنزيل:\n`{e}`"
            )

        return

    # --------------------------------------------------------
    # KICK
    # --------------------------------------------------------

    if normalized == "طرد":

        if not await require_admin(message):
            return

        target = await get_target()

        if not target:
            await message.reply_text(
                "❌ اعمل Reply على الشخص واكتب طرد."
            )
            return

        try:
            await bot.ban_chat_member(
                chat_id,
                target.id,
            )

            await bot.unban_chat_member(
                chat_id,
                target.id,
            )

            await message.reply_text(
                f"🚪 تم طرد {user_name(target)}."
            )

        except Exception as e:
            await message.reply_text(
                f"❌ فشل الطرد:\n`{e}`"
            )

        return

    # --------------------------------------------------------
    # BAN
    # --------------------------------------------------------

    if normalized == "حظر":

        if not await require_admin(message):
            return

        target = await get_target()

        if not target:
            await message.reply_text(
                "❌ اعمل Reply على الشخص واكتب حظر."
            )
            return

        try:
            await bot.ban_chat_member(
                chat_id,
                target.id,
            )

            await message.reply_text(
                f"🚫 تم حظر {user_name(target)}."
            )

        except Exception as e:
            await message.reply_text(
                f"❌ فشل الحظر:\n`{e}`"
            )

        return

    # --------------------------------------------------------
    # UNBAN
    # --------------------------------------------------------

    if normalized == "فك حظر":

        if not await require_admin(message):
            return

        target = await get_target()

        if not target:
            await message.reply_text(
                "❌ اعمل Reply على الشخص واكتب فك حظر."
            )
            return

        try:
            await bot.unban_chat_member(
                chat_id,
                target.id,
            )

            await message.reply_text(
                f"✅ تم فك الحظر عن {user_name(target)}."
            )

        except Exception as e:
            await message.reply_text(
                f"❌ فشل فك الحظر:\n`{e}`"
            )

        return

    # --------------------------------------------------------
    # MUTE
    # --------------------------------------------------------

    if normalized == "كتم":

        if not await require_admin(message):
            return

        target = await get_target()

        if not target:
            await message.reply_text(
                "❌ اعمل Reply على الشخص واكتب كتم."
            )
            return

        try:
            await bot.restrict_chat_member(
                chat_id,
                target.id,
                permissions=ChatPermissions(
                    can_send_messages=False
                ),
            )

            await message.reply_text(
                f"🔇 تم كتم {user_name(target)}."
            )

        except Exception as e:
            await message.reply_text(
                f"❌ فشل الكتم:\n`{e}`"
            )

        return

    # --------------------------------------------------------
    # UNMUTE
    # --------------------------------------------------------

    if normalized == "فك كتم":

        if not await require_admin(message):
            return

        target = await get_target()

        if not target:
            await message.reply_text(
                "❌ اعمل Reply على الشخص واكتب فك كتم."
            )
            return

        try:
            await bot.restrict_chat_member(
                chat_id,
                target.id,
                permissions=ChatPermissions(
                    can_send_messages=True
                ),
            )

            await message.reply_text(
                f"🔊 تم فك الكتم عن {user_name(target)}."
            )

        except Exception as e:
            await message.reply_text(
                f"❌ فشل فك الكتم:\n`{e}`"
            )

        return

    # --------------------------------------------------------
    # WARNING
    # --------------------------------------------------------

    if normalized == "تحذير":

        if not await require_admin(message):
            return

        target = await get_target()

        if not target:
            await message.reply_text(
                "❌ اعمل Reply على الشخص واكتب تحذير."
            )
            return

        count = add_warning(
            chat_id,
            target.id,
        )

        await message.reply_text(
            f"⚠️ تم تحذير {user_name(target)}.\n"
            f"عدد التحذيرات: {count}"
        )

        if count >= 3:

            try:
                await bot.ban_chat_member(
                    chat_id,
                    target.id,
                )

                await message.reply_text(
                    "🚫 وصل لـ3 تحذيرات وتم حظره."
                )

            except Exception:
                pass

        return

    # --------------------------------------------------------
    # WARNINGS
    # --------------------------------------------------------

    if normalized == "تحذيرات":

        target = await get_target()

        if not target:
            target = user

        count = get_warning_count(
            chat_id,
            target.id,
        )

        await message.reply_text(
            f"⚠️ تحذيرات {user_name(target)}: "
            f"{count}"
        )

        return

    # --------------------------------------------------------
    # CLEAR WARNINGS
    # --------------------------------------------------------

    if normalized == "مسح تحذيرات":

        if not await require_admin(message):
            return

        target = await get_target()

        if not target:
            await message.reply_text(
                "❌ اعمل Reply على الشخص واكتب مسح تحذيرات."
            )
            return

        clear_warnings(
            chat_id,
            target.id,
        )

        await message.reply_text(
            "✅ تم مسح التحذيرات."
        )

        return

    # --------------------------------------------------------
    # PIN
    # --------------------------------------------------------

    if normalized == "تثبيت":

        if not await require_admin(message):
            return

        if not message.reply_to_message:
            await message.reply_text(
                "❌ اعمل Reply على الرسالة التي تريد تثبيتها."
            )
            return

        try:
            await bot.pin_chat_message(
                chat_id,
                message.reply_to_message.id,
                disable_notification=True,
            )

            await message.reply_text(
                "📌 تم تثبيت الرسالة."
            )

        except Exception as e:
            await message.reply_text(
                f"❌ فشل التثبيت:\n`{e}`"
            )

        return

    # --------------------------------------------------------
    # UNPIN
    # --------------------------------------------------------

    if normalized == "إلغاء تثبيت":

        if not await require_admin(message):
            return

        try:
            await bot.unpin_chat_message(
                chat_id
            )

            await message.reply_text(
                "📌 تم إلغاء التثبيت."
            )

        except Exception as e:
            await message.reply_text(
                f"❌ فشل إلغاء التثبيت:\n`{e}`"
            )

        return


# ============================================================
# PROTECTION
# ============================================================

@bot.on_message(
    filters.group
    & (
        filters.text
        | filters.photo
        | filters.video
        | filters.sticker
        | filters.audio
    ),
    group=-1,
)
async def protection_handler(_, message):

    chat_id = message.chat.id

    if not group_enabled(chat_id):
        return

    if not message.from_user:
        return

    if await is_admin(
        bot,
        chat_id,
        message.from_user.id,
    ):
        return

    settings = get_settings(
        chat_id
    )

    # --------------------------------------------------------
    # LINKS
    # --------------------------------------------------------

    if settings.get("links"):

        text = message.text or ""

        if (
            "http://" in text
            or "https://" in text
            or "t.me/" in text
            or "www." in text
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

        text = (
            message.text or ""
        ).lower()

        for word in BAD_WORDS:

            if word.lower() in text:

                try:
                    await message.delete()
                except Exception:
                    pass

                return

    # --------------------------------------------------------
    # PHOTOS
    # --------------------------------------------------------

    if (
        settings.get("photos")
        and message.photo
    ):

        try:
            await message.delete()
        except Exception:
            pass

        return

    # --------------------------------------------------------
    # VIDEOS
    # --------------------------------------------------------

    if (
        settings.get("videos")
        and message.video
    ):

        try:
            await message.delete()
        except Exception:
            pass

        return

    # --------------------------------------------------------
    # STICKERS
    # --------------------------------------------------------

    if (
        settings.get("stickers")
        and message.sticker
    ):

        try:
            await message.delete()
        except Exception:
            pass

        return

    # --------------------------------------------------------
    # AUDIO
    # --------------------------------------------------------

    if (
        settings.get("audio")
        and message.audio
    ):

        try:
            await message.delete()
        except Exception:
            pass

        return


# ============================================================
# PROTECTION COMMANDS
# ============================================================

@bot.on_message(
    filters.group & filters.text
)
async def protection_commands(_, message):

    text = normalize(
        message.text or ""
    )

    if text not in {
        "قفل الروابط",
        "فتح الروابط",
        "قفل الصور",
        "فتح الصور",
        "قفل الفيديو",
        "فتح الفيديو",
        "قفل الملصقات",
        "فتح الملصقات",
        "قفل الصوت",
        "فتح الصوت",
        "قفل السب",
        "فتح السب",
    }:
        return

    if not await require_admin(message):
        return

    settings = get_settings(
        message.chat.id
    )

    if text == "قفل الروابط":
        settings["links"] = True

    elif text == "فتح الروابط":
        settings["links"] = False

    elif text == "قفل الصور":
        settings["photos"] = True

    elif text == "فتح الصور":
        settings["photos"] = False

    elif text == "قفل الفيديو":
        settings["videos"] = True

    elif text == "فتح الفيديو":
        settings["videos"] = False

    elif text == "قفل الملصقات":
        settings["stickers"] = True

    elif text == "فتح الملصقات":
        settings["stickers"] = False

    elif text == "قفل الصوت":
        settings["audio"] = True

    elif text == "فتح الصوت":
        settings["audio"] = False

    elif text == "قفل السب":
        settings["bad_words"] = True

    elif text == "فتح السب":
        settings["bad_words"] = False

    save_json(
        SETTINGS_FILE,
        group_settings,
    )

    await message.reply_text(
        "✅ تم تحديث إعداد الحماية."
    )


# ============================================================
# GAME CALLBACKS
# ============================================================

@bot.on_callback_query(
    filters.regex(r"^game_join:")
)
async def game_join_callback(_, query):

    try:
        chat_id = int(
            query.data.split(":")[1]
        )
    except Exception:
        await query.answer(
            "❌ خطأ",
            show_alert=True,
        )
        return

    session = game_sessions.get(
        chat_id
    )

    if not session:
        await query.answer(
            "❌ اللعبة انتهت.",
            show_alert=True,
        )
        return

    user_id = query.from_user.id

    if user_id in session["players"]:

        await query.answer(
            "أنت داخل اللعبة بالفعل.",
            show_alert=True,
        )
        return

    if len(session["players"]) >= 2:

        await query.answer(
            "❌ اللعبة مكتملة.",
            show_alert=True,
        )
        return

    session["players"].append(
        user_id
    )

    names = []

    for uid in session["players"]:

        try:
            member = await bot.get_users(uid)
            names.append(
                user_name(member)
            )
        except Exception:
            names.append("لاعب")

    await query.message.edit_text(
        f"🎮 **{session['name']}**\n\n"
        f"👤 اللاعب الأول: {names[0]}\n"
        f"👤 اللاعب الثاني: {names[1]}\n\n"
        "✅ اللاعبان جاهزان.\n"
        "اضغطوا بدء اللعبة.",
        reply_markup=game_buttons(
            chat_id
        ),
    )

    await query.answer(
        "✅ انضممت للعبة!"
    )


@bot.on_callback_query(
    filters.regex(r"^game_start:")
)
async def game_start_callback(_, query):

    try:
        chat_id = int(
            query.data.split(":")[1]
        )
    except Exception:
        await query.answer(
            "❌ خطأ",
            show_alert=True,
        )
        return

    session = game_sessions.get(
        chat_id
    )

    if not session:
        await query.answer(
            "❌ اللعبة انتهت.",
            show_alert=True,
        )
        return

    if query.from_user.id not in session["players"]:

        await query.answer(
            "❌ أنت مش لاعب.",
            show_alert=True,
        )
        return

    if len(session["players"]) < 2:

        await query.answer(
            "❌ لازم لاعبين.",
            show_alert=True,
        )
        return

    if session["started"]:

        await query.answer(
            "اللعبة بدأت بالفعل.",
            show_alert=True,
        )
        return

    result = await start_game(
        chat_id,
        session,
    )

    markup = None

    if session["name"] == "حجر ورق مقص":

        markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✊ حجر",
                        callback_data=f"rps:{chat_id}:rock",
                    ),
                    InlineKeyboardButton(
                        "✋ ورق",
                        callback_data=f"rps:{chat_id}:paper",
                    ),
                    InlineKeyboardButton(
                        "✌️ مقص",
                        callback_data=f"rps:{chat_id}:scissors",
                    ),
                ]
            ]
        )

    await query.message.edit_text(
        result,
        reply_markup=markup,
    )

    await query.answer(
        "▶️ بدأت اللعبة!"
    )


@bot.on_callback_query(
    filters.regex(r"^game_cancel:")
)
async def game_cancel_callback(_, query):

    try:
        chat_id = int(
            query.data.split(":")[1]
        )
    except Exception:
        return

    session = game_sessions.get(
        chat_id
    )

    if not session:
        await query.answer(
            "اللعبة انتهت."
        )
        return

    if query.from_user.id not in session["players"]:

        await query.answer(
            "❌ أنت مش لاعب.",
            show_alert=True,
        )
        return

    game_sessions.pop(
        chat_id,
        None,
    )

    await query.message.edit_text(
        "❌ تم إلغاء اللعبة."
    )

    await query.answer(
        "تم الإلغاء."
    )


# ============================================================
# RPS
# ============================================================

@bot.on_callback_query(
    filters.regex(r"^rps:")
)
async def rps_callback(_, query):

    parts = query.data.split(":")

    if len(parts) != 3:
        return

    chat_id = int(parts[1])
    choice = parts[2]

    session = game_sessions.get(
        chat_id
    )

    if not session or not session["started"]:
        await query.answer(
            "❌ اللعبة غير شغالة.",
            show_alert=True,
        )
        return

    if query.from_user.id not in session["players"]:

        await query.answer(
            "❌ أنت مش لاعب.",
            show_alert=True,
        )
        return

    session.setdefault(
        "choices",
        {}
    )

    session["choices"][
        query.from_user.id
    ] = choice

    await query.answer(
        "✅ اختيارك اتسجل."
    )

    if len(session["choices"]) < 2:
        await query.message.edit_text(
            "✊✋✌️ اختيار أول لاعب تم.\n"
            "مستني اختيار اللاعب الثاني..."
        )
        return

    players = session["players"]

    first = session["choices"][
        players[0]
    ]

    second = session["choices"][
        players[1]
    ]

    wins = {
        "rock": "scissors",
        "scissors": "paper",
        "paper": "rock",
    }

    if first == second:
        result = "🤝 تعادل!"

    elif wins[first] == second:
        result = "🏆 اللاعب الأول كسب!"

    else:
        result = "🏆 اللاعب الثاني كسب!"

    await query.message.edit_text(
        "✊✋✌️ **حجر ورق مقص**\n\n"
        f"اللاعب الأول: {first}\n"
        f"اللاعب الثاني: {second}\n\n"
        f"{result}"
    )

    game_sessions.pop(
        chat_id,
        None,
    )


# ============================================================
# GAME ANSWERS
# ============================================================

@bot.on_message(
    filters.group & filters.text
)
async def game_answer_handler(_, message):

    chat_id = message.chat.id

    session = game_sessions.get(
        chat_id
    )

    if not session:
        return

    if not session["started"]:
        return

    user = message.from_user

    if not user:
        return

    if user.id not in session["players"]:
        return

    text = message.text.strip()

    # --------------------------------------------------------
    # GUESS NUMBER
    # --------------------------------------------------------

    if (
        session["name"]
        == "تخمين الرقم"
    ):

        try:
            guess = int(text)
        except Exception:
            return

        number = session["number"]

        if guess == number:

            await message.reply_text(
                f"🎉 صح!\n"
                f"الرقم كان {number}."
            )

            game_sessions.pop(
                chat_id,
                None,
            )

        elif guess < number:

            await message.reply_text(
                "⬆️ الرقم أكبر."
            )

        else:

            await message.reply_text(
                "⬇️ الرقم أصغر."
            )

        return

    # --------------------------------------------------------
    # MATH
    # --------------------------------------------------------

    if session.get("answer"):

        if text == str(
            session["answer"]
        ):

            await message.reply_text(
                "🎉 إجابة صحيحة!"
            )

            game_sessions.pop(
                chat_id,
                None,
            )

        else:

            await message.reply_text(
                "❌ إجابة غلط، حاول تاني."
            )

        return

    # --------------------------------------------------------
    # GENERIC
    # --------------------------------------------------------

    await message.reply_text(
        f"🎮 {user_name(user)} "
        "شارك في اللعبة! 🔥"
    )


# ============================================================
# WELCOME
# ============================================================

@bot.on_message(
    filters.group & filters.new_chat_members
)
async def welcome_handler(_, message):

    if not group_enabled(
        message.chat.id
    ):
        return

    for member in message.new_chat_members:

        await message.reply_text(
            f"🎀 أهلاً وسهلاً "
            f"{user_name(member)} ❤️\n\n"
            "نورت المجموعة يا جميل 🌷"
        )


# ============================================================
# MUSIC CALLBACKS
# ============================================================

@bot.on_callback_query(
    filters.regex(r"^music_skip:")
)
async def music_skip_callback(_, query):

    if not query.message:
        return

    chat_id = int(
        query.data.split(":")[1]
    )

    if not await is_admin(
        bot,
        chat_id,
        query.from_user.id,
    ):

        await query.answer(
            "❌ للمشرفين فقط.",
            show_alert=True,
        )
        return

    await skip_song(
        chat_id
    )

    await query.answer(
        "⏭ تم التخطي."
    )


@bot.on_callback_query(
    filters.regex(r"^music_stop:")
)
async def music_stop_callback(_, query):

    chat_id = int(
        query.data.split(":")[1]
    )

    if not await is_admin(
        bot,
        chat_id,
        query.from_user.id,
    ):

        await query.answer(
            "❌ للمشرفين فقط.",
            show_alert=True,
        )
        return

    await stop_music(
        chat_id
    )

    await query.answer(
        "⏹ تم الإيقاف."
    )


@bot.on_callback_query(
    filters.regex(r"^music_queue:")
)
async def music_queue_callback(_, query):

    chat_id = int(
        query.data.split(":")[1]
    )

    queue = music_queue.get(
        chat_id,
        []
    )

    now = current_song.get(
        chat_id
    )

    lines = []

    if now:
        lines.append(
            f"▶️ الآن: {now['title']}"
        )

    for i, song in enumerate(
        queue,
        start=1,
    ):
        lines.append(
            f"{i}. {song['title']}"
        )

    if not lines:
        text = "📭 القائمة فاضية."
    else:
        text = (
            "🎵 **قائمة التشغيل**\n\n"
            + "\n".join(lines)
        )

    await query.answer()

    try:
        await query.message.reply_text(
            text
        )
    except Exception:
        pass


# ============================================================
# STARTUP
# ============================================================

async def main():

    global calls

    print(
        "========== BOT FILE STARTED =========="
    )

    await bot.start()

    print(
        "========== BOT STARTED =========="
    )

    await assistant.start()

    print(
        "========== ASSISTANT STARTED =========="
    )

    # مهم جدًا:
    # في النسخة الموجودة عندك calls.start() يرجع coroutine
    # لذلك لازم await
    calls = PyTgCalls(
        assistant
    )

    await calls.start()

    print(
        "========== PYTGCALLS STARTED =========="
    )

    me = await bot.get_me()

    print(
        "BOT:",
        me.username,
    )

    assistant_me = await assistant.get_me()

    print(
        "ASSISTANT:",
        assistant_me.username,
    )

    print(
        "========== EVERYTHING STARTED =========="
    )

    # إبقاء البرنامج شغال
    await asyncio.Event().wait()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    try:
        asyncio.run(
            main()
        )

    except KeyboardInterrupt:
        pass

    except Exception as e:
        print(
            "FATAL ERROR:",
            repr(e),
        )
        raise
