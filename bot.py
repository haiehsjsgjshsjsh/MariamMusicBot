import os
import re
import json
import random
import asyncio
import logging
from pathlib import Path

import static_ffmpeg
static_ffmpeg.add_paths()

import pyrogram
from pyrogram import Client, filters, idle
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatPrivileges,
    ChatPermissions,
)

from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, GroupCallConfig


# =========================================================
#                    الإعدادات
# =========================================================

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
SESSION_STRING = os.environ["SESSION_STRING"]

PHOTO_PATH = "IMG_20260922_130735_050.jpg"


# =========================================================
#              توافق Pyrogram / PyrogramMod
# =========================================================

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


# =========================================================
#                     Clients
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

calls = None


# =========================================================
#                     البيانات
# =========================================================

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

MUSIC_DIR = Path("music")
MUSIC_DIR.mkdir(exist_ok=True)

SETTINGS_FILE = DATA_DIR / "group_settings.json"
WARNINGS_FILE = DATA_DIR / "warnings.json"
REPLIES_FILE = DATA_DIR / "custom_replies.json"


def load_json(path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass

    return default


def save_json(path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


group_settings = load_json(SETTINGS_FILE, {})
warnings = load_json(WARNINGS_FILE, {})
custom_replies = load_json(REPLIES_FILE, {})


# =========================================================
#                     حالة البوت
# =========================================================

waiting_song = {}

queues = {}

current_song = {}

game_sessions = {}


# =========================================================
#                     أدوات عامة
# =========================================================

def normalize(text):
    return re.sub(r"\s+", " ", (text or "").strip()).casefold()


def get_setting(chat_id, key, default=False):
    return group_settings.get(str(chat_id), {}).get(key, default)


def set_setting(chat_id, key, value):
    group_settings.setdefault(str(chat_id), {})
    group_settings[str(chat_id)][key] = value
    save_json(SETTINGS_FILE, group_settings)


def queue_for(chat_id):
    return queues.setdefault(chat_id, [])


async def is_admin(message):
    try:
        member = await bot.get_chat_member(
            message.chat.id,
            message.from_user.id,
        )

        status = str(member.status).lower()

        return status in (
            "owner",
            "creator",
            "administrator",
            "admin",
        )

    except Exception:
        return False


async def is_owner(message):
    try:
        member = await bot.get_chat_member(
            message.chat.id,
            message.from_user.id,
        )

        status = str(member.status).lower()

        return status in (
            "owner",
            "creator",
        )

    except Exception:
        return False


async def get_target_user(message):
    if message.reply_to_message:
        if message.reply_to_message.from_user:
            return message.reply_to_message.from_user

    parts = (message.text or "").split(maxsplit=1)

    if len(parts) == 2:
        try:
            return await bot.get_users(parts[1])
        except Exception:
            pass

    return None


# =========================================================
#                    الترقيات
# =========================================================

async def promote_user(chat_id, user_id):

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
        user_id,
        privileges=privileges,
    )


async def demote_user(chat_id, user_id):

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
        user_id,
        privileges=privileges,
    )


# =========================================================
#                     الألعاب
# =========================================================

GAME_NAMES = [
    "إكس أو",
    "حجر ورق مقص",
    "تخمين الرقم",
    "تحدي السرعة",
    "أسئلة عامة",
    "حساب سريع",
    "صح أم خطأ",
    "خمن الشخصية",
    "خمن الفيلم",
    "خمن الأغنية",
    "حروف وكلمات",
    "كلمة السر",
    "ذاكرة الأرقام",
    "ترتيب الأرقام",
    "مين الأسرع",
    "اختبر ذاكرتك",
    "سؤال وجواب",
    "لغز اليوم",
    "من أنا",
    "أكمل الكلمة",
    "أكمل الجملة",
    "الكلمة المفقودة",
    "حرف وكلمة",
    "اسم ولد",
    "اسم بنت",
    "اسم حيوان",
    "اسم بلد",
    "اسم مدينة",
    "اسم أكلة",
    "اسم لاعب",
    "اسم فيلم",
    "اسم مسلسل",
    "اسم لعبة",
    "اسم سيارة",
    "اسم ماركة",
    "اسم لون",
    "اسم فاكهة",
    "اسم خضار",
    "جمع الكلمات",
    "عكس الكلمة",
    "مرادف الكلمة",
    "ترجمة سريعة",
    "إنجليزي سريع",
    "فرنساوي سريع",
    "اختبار معلومات",
    "اختبار كرة",
    "اختبار سيارات",
    "اختبار ألعاب",
    "اختبار أفلام",
    "اختبار مسلسلات",
    "تحدي الحروف",
    "تحدي الأرقام",
    "تحدي الحساب",
    "تحدي الذاكرة",
    "تحدي التركيز",
    "تحدي الملاحظة",
    "تحدي الاختيار",
    "تحدي الحظ",
    "صندوق الحظ",
    "عجلة الحظ",
    "عملة",
    "نرد",
    "أعلى رقم",
    "أقل رقم",
    "زوجي أم فردي",
    "فردي أم زوجي",
    "أقرب رقم",
    "رقم سري",
    "كود سري",
    "سرعة الكتابة",
    "آخر حرف",
    "أول حرف",
    "كلمة من 5 حروف",
    "كلمة من 6 حروف",
    "كلمة من 7 حروف",
    "لغز رياضي",
    "لغز منطقي",
    "لغز بوليسي",
    "لغز غامض",
    "لغز سريع",
    "من الأقوى",
    "من الأسرع",
    "من الأذكى",
    "تحدي 10 ثواني",
    "تحدي 20 ثانية",
    "تحدي 30 ثانية",
    "تحدي بدون تفكير",
    "تحدي نعم أو لا",
    "ممنوع تقول نعم",
    "ممنوع تقول لا",
    "اختار رقم",
    "اختار لون",
    "اختار باب",
    "اختار صندوق",
    "اختبار الحظ",
    "سباق الأرقام",
    "سباق الكلمات",
    "سباق الحروف",
    "سباق الإجابات",
    "سباق النقر",
    "ملك الأسئلة",
    "ملكة الأسئلة",
    "بطل الحساب",
    "بطل الذاكرة",
    "بطل الحروف",
    "بطل السرعة",
    "كأس المعرفة",
    "كأس الحظ",
    "كأس الكلمات",
    "كأس الأرقام",
    "مباراة الأسئلة",
    "مباراة الحظ",
    "مباراة الذاكرة",
    "مباراة السرعة",
    "مباراة الحروف",
    "مباراة الحساب",
    "تحدي الأصدقاء",
    "تحدي شخصين",
    "مسابقة شخصين",
    "معركة الأرقام",
    "معركة الكلمات",
    "معركة الحروف",
    "معركة الحظ",
    "مواجهة سريعة",
    "مواجهة الأذكياء",
    "مواجهة السرعة",
    "مواجهة المعرفة",
    "جولة نهائية",
]


GAME_NAMES = list(dict.fromkeys(GAME_NAMES))


TWO_PLAYER_GAMES = {
    "إكس أو",
    "حجر ورق مقص",
    "مباراة الأسئلة",
    "مباراة الحظ",
    "مباراة الذاكرة",
    "مباراة السرعة",
    "مباراة الحروف",
    "مباراة الحساب",
    "تحدي شخصين",
    "مسابقة شخصين",
    "معركة الأرقام",
    "معركة الكلمات",
    "معركة الحروف",
    "معركة الحظ",
    "مواجهة سريعة",
    "مواجهة الأذكياء",
    "مواجهة السرعة",
    "مواجهة المعرفة",
}


GAME_LOOKUP = {
    normalize(name): name
    for name in GAME_NAMES
}


def find_game(text):

    value = normalize(text)

    if value in GAME_LOOKUP:
        return GAME_LOOKUP[value]

    for key, name in GAME_LOOKUP.items():
        if key in value:
            return name

    return None


def games_list():

    lines = [
        "🎮 **قائمة الألعاب**",
        "",
        f"🎯 عدد الألعاب: **{len(GAME_NAMES)}**",
        "",
    ]

    for index, name in enumerate(GAME_NAMES, 1):

        if name in TWO_PLAYER_GAMES:
            kind = "👥 شخصين"
        else:
            kind = "👤 فردية"

        lines.append(
            f"{index}. {name} — {kind}"
        )

    lines += [
        "",
        "💡 اكتب اسم اللعبة مباشرة لتبدأ.",
    ]

    return "\n".join(lines)


def game_keyboard(chat_id, game):

    if game in TWO_PLAYER_GAMES:

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

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🎮 ابدأ",
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


async def create_game(message, game):

    chat_id = message.chat.id

    if chat_id in game_sessions:

        await message.reply_text(
            "⚠️ فيه لعبة شغالة بالفعل في الجروب."
        )

        return

    game_sessions[chat_id] = {
        "game": game,
        "host": message.from_user.id,
        "players": [message.from_user.id],
        "started": False,
        "moves": {},
        "score": {},
    }

    if game in TWO_PLAYER_GAMES:

        text = (
            f"🎮 **{game}**\n\n"
            "👥 اللعبة دي لشخصين.\n\n"
            "1️⃣ اضغط «انضم للعبة» أنت.\n"
            "2️⃣ الشخص الثاني يضغط «انضم للعبة».\n"
            "3️⃣ بعدها صاحب اللعبة يضغط «بدء اللعبة»."
        )

    else:

        text = (
            f"🎮 **{game}**\n\n"
            "👤 لعبة فردية.\n"
            "اضغط «ابدأ» للبدء."
        )

    await message.reply_text(
        text,
        reply_markup=game_keyboard(chat_id, game),
    )


def rps_keyboard():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✊ حجر",
                    callback_data="rps:rock",
                ),
                InlineKeyboardButton(
                    "✋ ورق",
                    callback_data="rps:paper",
                ),
                InlineKeyboardButton(
                    "✌️ مقص",
                    callback_data="rps:scissors",
                ),
            ]
        ]
    )


# =========================================================
#                    الموسيقى
# =========================================================

async def search_and_download(name):

    import yt_dlp

    safe_name = re.sub(
        r"[^\w\u0600-\u06FF -]",
        "",
        name,
    )[:70].strip()

    if not safe_name:
        safe_name = "song"

    output = MUSIC_DIR / f"{safe_name}.%(ext)s"

    options = {
        "format": "bestaudio/best",
        "outtmpl": str(output),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "default_search": "scsearch1",
    }

    try:

        with yt_dlp.YoutubeDL(options) as ydl:

            info = ydl.extract_info(
                f"scsearch1:{name}",
                download=True,
            )

            entry = (
                info["entries"][0]
                if info.get("entries")
                else info
            )

            path = ydl.prepare_filename(entry)

            if not Path(path).exists():

                files = list(
                    MUSIC_DIR.glob(
                        f"{safe_name}.*"
                    )
                )

                if files:
                    path = str(files[0])

            return {
                "title": entry.get(
                    "title",
                    name,
                ),
                "duration": entry.get(
                    "duration",
                    0,
                ) or 0,
                "path": path,
            }

    except Exception:

        options["default_search"] = "ytsearch1"

        options["extractor_args"] = {
            "youtube": {
                "player_client": [
                    "android"
                ]
            }
        }

        with yt_dlp.YoutubeDL(options) as ydl:

            info = ydl.extract_info(
                f"ytsearch1:{name}",
                download=True,
            )

            entry = (
                info["entries"][0]
                if info.get("entries")
                else info
            )

            path = ydl.prepare_filename(entry)

            return {
                "title": entry.get(
                    "title",
                    name,
                ),
                "duration": entry.get(
                    "duration",
                    0,
                ) or 0,
                "path": path,
            }


async def play_next(chat_id):

    q = queue_for(chat_id)

    if not q:

        current_song.pop(chat_id, None)

        try:
            await calls.leave_call(chat_id)
        except Exception:
            pass

        return

    song = q.pop(0)

    current_song[chat_id] = song

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

    duration = int(
        song.get("duration", 0) or 0
    )

    minutes, seconds = divmod(
        duration,
        60,
    )

    caption = (
        "🎶 **مريومه الدلوعه**\n\n"
        f"🎵 **{song['title']}**\n"
        f"⏱️ `{minutes}:{seconds:02d}`\n"
        f"👤 الطلب: {song.get('requester', 'غير معروف')}"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⏭️ تخطي",
                    callback_data=f"music_skip:{chat_id}",
                ),
                InlineKeyboardButton(
                    "⏹️ إيقاف",
                    callback_data=f"music_stop:{chat_id}",
                ),
            ]
        ]
    )

    try:

        if Path(PHOTO_PATH).exists():

            await bot.send_photo(
                chat_id,
                PHOTO_PATH,
                caption=caption,
                reply_markup=keyboard,
            )

        else:

            await bot.send_message(
                chat_id,
                caption,
                reply_markup=keyboard,
            )

    except Exception:
        pass


async def add_song(
    chat_id,
    name,
    requester,
):

    song = await search_and_download(
        name
    )

    song["requester"] = requester

    q = queue_for(chat_id)

    if current_song.get(chat_id):

        q.append(song)

        return (
            f"➕ اتضافت للقائمة:\n"
            f"🎵 **{song['title']}**"
        )

    await play_next(chat_id)

    return (
        f"▶️ شغلت:\n"
        f"🎵 **{song['title']}**"
    )


# =========================================================
#                       الأوامر
# =========================================================

HELP_TEXT = """
📚 **أوامر مريومه الدلوعه**

🎵 **الميوزك**
• تشغيل
• تشغيل اسم الأغنية
• تخطي
• وقف
• إيقاف
• القائمة

🎮 **الألعاب**
• العاب
• ألعاب
• اكتب اسم اللعبة مباشرة

⚙️ **البوت**
• تفعيل البوت
• تعطيل البوت
• الأوامر
• الاوامر
• مساعدة

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
• تحذير
• تحذيرات
• مسح تحذيرات
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

💬 **الردود**
• اضف رد الكلمة = الرد
• مسح رد الكلمة
"""


# =========================================================
#                 أوامر الجروبات
# =========================================================

@bot.on_message(
    filters.group & filters.text
)
async def group_commands(_, message):

    text = (message.text or "").strip()

    chat_id = message.chat.id

    # -----------------------------------------------------
    # إضافة رد
    # -----------------------------------------------------

    if text.startswith("اضف رد "):

        if not await is_admin(message):

            await message.reply_text(
                "❌ الأمر ده للمشرفين فقط."
            )

            return

        body = text[7:].strip()

        if "=" not in body:

            await message.reply_text(
                "❌ استخدم:\n"
                "اضف رد الكلمة = الرد"
            )

            return

        trigger, reply = body.split(
            "=",
            1,
        )

        trigger = trigger.strip()
        reply = reply.strip()

        bucket = custom_replies.setdefault(
            str(chat_id),
            {},
        )

        key = normalize(trigger)

        if (
            len(bucket) >= 500
            and key not in bucket
        ):

            await message.reply_text(
                "❌ وصلت للحد الأقصى وهو 500 رد."
            )

            return

        bucket[key] = reply

        save_json(
            REPLIES_FILE,
            custom_replies,
        )

        await message.reply_text(
            f"✅ تم إضافة الرد.\n\n"
            f"لو قلت: **{trigger}**\n"
            f"هرد عليك: **{reply}**"
        )

        return

    # -----------------------------------------------------
    # حذف رد
    # -----------------------------------------------------

    if text.startswith("مسح رد "):

        if not await is_admin(message):

            await message.reply_text(
                "❌ الأمر ده للمشرفين فقط."
            )

            return

        trigger = normalize(
            text[7:]
        )

        bucket = custom_replies.setdefault(
            str(chat_id),
            {},
        )

        if trigger not in bucket:

            await message.reply_text(
                "❌ الرد مش موجود."
            )

            return

        del bucket[trigger]

        save_json(
            REPLIES_FILE,
            custom_replies,
        )

        await message.reply_text(
            "✅ تم مسح الرد."
        )

        return

    # -----------------------------------------------------
    # الأوامر
    # -----------------------------------------------------

    if text in (
        "الأوامر",
        "الاوامر",
        "مساعدة",
    ):

        await message.reply_text(
            HELP_TEXT
        )

        return

    # -----------------------------------------------------
    # الألعاب
    # -----------------------------------------------------

    if text in (
        "العاب",
        "ألعاب",
        "الالعاب",
        "الألعاب",
    ):

        await message.reply_text(
            games_list()
        )

        return

    # -----------------------------------------------------
    # تفعيل / تعطيل
    # -----------------------------------------------------

    if text == "تفعيل البوت":

        if not await is_admin(message):

            await message.reply_text(
                "❌ الأمر ده للمشرفين فقط."
            )

            return

        set_setting(
            chat_id,
            "enabled",
            True,
        )

        await message.reply_text(
            "✅ تم تفعيل البوت في الجروب."
        )

        return

    if text == "تعطيل البوت":

        if not await is_admin(message):

            await message.reply_text(
                "❌ الأمر ده للمشرفين فقط."
            )

            return

        set_setting(
            chat_id,
            "enabled",
            False,
        )

        await message.reply_text(
            "⛔ تم تعطيل البوت."
        )

        return

    # -----------------------------------------------------
    # بدء لعبة باسمها
    # -----------------------------------------------------

    game = find_game(text)

    if game:

        await create_game(
            message,
            game,
        )

        return

    # -----------------------------------------------------
    # لو البوت غير مفعل
    # -----------------------------------------------------

    if not get_setting(
        chat_id,
        "enabled",
        False,
    ):

        return

    # -----------------------------------------------------
    # تشغيل
    # -----------------------------------------------------

    if text == "تشغيل":

        waiting_song[
            chat_id
        ] = message.from_user.id

        await message.reply_text(
            "🎵 قول اسم الأغنية."
        )

        return

    # -----------------------------------------------------
    # تشغيل + اسم
    # -----------------------------------------------------

    if text.startswith("تشغيل "):

        waiting_song.pop(
            chat_id,
            None,
        )

        song_name = text[7:].strip()

        if not song_name:

            await message.reply_text(
                "🎵 اكتب اسم الأغنية."
            )

            return

        try:

            result = await add_song(
                chat_id,
                song_name,
                message.from_user.mention,
            )

            await message.reply_text(
                result
            )

        except Exception as e:

            await message.reply_text(
                "❌ حصل خطأ في تشغيل الأغنية:\n"
                f"`{type(e).__name__}`"
            )

        return

    # -----------------------------------------------------
    # تخطي
    # -----------------------------------------------------

    if text == "تخطي":

        if not await is_admin(message):

            await message.reply_text(
                "❌ الأمر ده للمشرفين فقط."
            )

            return

        try:
            await calls.leave_call(
                chat_id
            )
        except Exception:
            pass

        current_song.pop(
            chat_id,
            None,
        )

        try:

            await play_next(
                chat_id
            )

            await message.reply_text(
                "⏭️ تم تخطي الأغنية."
            )

        except Exception as e:

            await message.reply_text(
                "❌ حصل خطأ في التخطي:\n"
                f"`{type(e).__name__}`"
            )

        return

    # -----------------------------------------------------
    # وقف / إيقاف
    # -----------------------------------------------------

    if text in (
        "وقف",
        "إيقاف",
    ):

        if not await is_admin(message):

            await message.reply_text(
                "❌ الأمر ده للمشرفين فقط."
            )

            return

        try:
            await calls.leave_call(
                chat_id
            )
        except Exception:
            pass

        queues.pop(
            chat_id,
            None,
        )

        current_song.pop(
            chat_id,
            None,
        )

        waiting_song.pop(
            chat_id,
            None,
        )

        await message.reply_text(
            "⏹️ تم إيقاف الميوزك ومسح القائمة."
        )

        return

    # -----------------------------------------------------
    # القائمة
    # -----------------------------------------------------

    if text == "القائمة":

        q = queue_for(chat_id)

        if (
            not current_song.get(chat_id)
            and not q
        ):

            await message.reply_text(
                "📭 القائمة فاضية."
            )

            return

        lines = [
            "🎵 **قائمة التشغيل**",
            "",
        ]

        if current_song.get(
            chat_id
        ):

            lines.append(
                "▶️ الآن:\n"
                + current_song[
                    chat_id
                ]["title"]
            )

        for index, song in enumerate(
            q,
            1,
        ):

            lines.append(
                f"{index}. {song['title']}"
            )

        await message.reply_text(
            "\n".join(lines)
        )

        return

    # =====================================================
    #                    الرتب
    # =====================================================

    if text == "رتبتي":

        try:

            member = await bot.get_chat_member(
                chat_id,
                message.from_user.id,
            )

            status = str(
                member.status
            ).lower()

            if status in (
                "owner",
                "creator",
            ):

                rank = "👑 مالك"

            elif status in (
                "administrator",
                "admin",
            ):

                rank = "🛡️ مشرف"

            else:

                rank = "👤 عضو"

        except Exception:

            rank = "👤 عضو"

        await message.reply_text(
            f"📌 رتبتك: {rank}"
        )

        return

    # -----------------------------------------------------
    # المالك
    # -----------------------------------------------------

    if text == "المالك":

        owners = []

        try:

            async for member in bot.get_chat_members(
                chat_id,
                filter=pyrogram.enums.ChatMembersFilter.ADMINISTRATORS,
            ):

                status = str(
                    member.status
                ).lower()

                if status in (
                    "owner",
                    "creator",
                ):

                    owners.append(
                        member.user.mention
                    )

        except Exception:
            pass

        if owners:

            await message.reply_text(
                "👑 **المالك:**\n\n"
                + "\n".join(owners)
            )

        else:

            await message.reply_text(
                "👑 المالك: غير معروف."
            )

        return

    # -----------------------------------------------------
    # المشرفين
    # -----------------------------------------------------

    if text == "المشرفين":

        admins = []

        try:

            async for member in bot.get_chat_members(
                chat_id,
                filter=pyrogram.enums.ChatMembersFilter.ADMINISTRATORS,
            ):

                status = str(
                    member.status
                ).lower()

                if status in (
                    "owner",
                    "creator",
                    "administrator",
                    "admin",
                ):

                    admins.append(
                        f"• {member.user.mention}"
                    )

        except Exception:
            pass

        await message.reply_text(
            "🛡️ **المشرفين:**\n\n"
            + (
                "\n".join(admins)
                if admins
                else "لا يوجد"
            )
        )

        return

    # =====================================================
    #                    الإدارة
    # =====================================================

    admin_commands = {
        "ترقية",
        "تنزيل",
        "طرد",
        "حظر",
        "فك حظر",
        "كتم",
        "فك كتم",
        "تحذير",
        "تحذيرات",
        "مسح تحذيرات",
        "تثبيت",
        "إلغاء تثبيت",
    }

    if text in admin_commands:

        if not await is_admin(message):

            await message.reply_text(
                "❌ الأمر ده للمشرفين فقط."
            )

            return

        # -----------------------------
        # تثبيت
        # -----------------------------

        if text == "تثبيت":

            if not message.reply_to_message:

                await message.reply_text(
                    "↩️ اعمل ريبلاي على الرسالة واكتب تثبيت."
                )

                return

            try:

                await message.reply_to_message.pin()

                await message.reply_text(
                    "📌 تم تثبيت الرسالة."
                )

            except Exception as e:

                await message.reply_text(
                    f"❌ فشل التثبيت: `{type(e).__name__}`"
                )

            return

        # -----------------------------
        # إلغاء التثبيت
        # -----------------------------

        if text == "إلغاء تثبيت":

            try:

                await bot.unpin_chat_message(
                    chat_id
                )

                await message.reply_text(
                    "📌 تم إلغاء التثبيت."
                )

            except Exception as e:

                await message.reply_text(
                    f"❌ `{type(e).__name__}`"
                )

            return

        user = await get_target_user(
            message
        )

        # -----------------------------
        # لازم عضو
        # -----------------------------

        if not user:

            await message.reply_text(
                "↩️ اعمل ريبلاي على العضو "
                "ثم اكتب الأمر."
            )

            return

        # -----------------------------
        # ترقية
        # -----------------------------

        if text == "ترقية":

            try:

                await promote_user(
                    chat_id,
                    user.id,
                )

                await message.reply_text(
                    f"✅ تمت ترقية {user.mention}."
                )

            except Exception as e:

                await message.reply_text(
                    "❌ فشلت الترقية:\n"
                    f"`{type(e).__name__}`"
                )

            return

        # -----------------------------
        # تنزيل
        # -----------------------------

        if text == "تنزيل":

            try:

                await demote_user(
                    chat_id,
                    user.id,
                )

                await message.reply_text(
                    f"✅ تم تنزيل {user.mention}."
                )

            except Exception as e:

                await message.reply_text(
                    "❌ فشل التنزيل:\n"
                    f"`{type(e).__name__}`"
                )

            return

        # -----------------------------
        # طرد
        # -----------------------------

        if text == "طرد":

            try:

                await bot.ban_chat_member(
                    chat_id,
                    user.id,
                )

                await bot.unban_chat_member(
                    chat_id,
                    user.id,
                )

                await message.reply_text(
                    f"👢 تم طرد {user.mention}."
                )

            except Exception as e:

                await message.reply_text(
                    f"❌ `{type(e).__name__}`"
                )

            return

        # -----------------------------
        # حظر
        # -----------------------------

        if text == "حظر":

            try:

                await bot.ban_chat_member(
                    chat_id,
                    user.id,
                )

                await message.reply_text(
                    f"🚫 تم حظر {user.mention}."
                )

            except Exception as e:

                await message.reply_text(
                    f"❌ `{type(e).__name__}`"
                )

            return

        # -----------------------------
        # فك حظر
        # -----------------------------

        if text == "فك حظر":

            try:

                await bot.unban_chat_member(
                    chat_id,
                    user.id,
                )

                await message.reply_text(
                    f"✅ تم فك الحظر عن {user.mention}."
                )

            except Exception as e:

                await message.reply_text(
                    f"❌ `{type(e).__name__}`"
                )

            return

        # -----------------------------
        # كتم / فك كتم
        # -----------------------------

        if text in (
            "كتم",
            "فك كتم",
        ):

            try:

                permissions = ChatPermissions(
                    can_send_messages=(
                        text == "فك كتم"
                    )
                )

                await bot.restrict_chat_member(
                    chat_id,
                    user.id,
                    permissions=permissions,
                )

                if text == "كتم":

                    await message.reply_text(
                        f"🔇 تم كتم {user.mention}."
                    )

                else:

                    await message.reply_text(
                        f"🔊 تم فك كتم {user.mention}."
                    )

            except Exception as e:

                await message.reply_text(
                    f"❌ `{type(e).__name__}`"
                )

            return

        # -----------------------------
        # التحذيرات
        # -----------------------------

        if text in (
            "تحذير",
            "تحذيرات",
            "مسح تحذيرات",
        ):

            bucket = warnings.setdefault(
                str(chat_id),
                {},
            )

            user_id = str(
                user.id
            )

            if text == "تحذير":

                bucket[user_id] = (
                    bucket.get(
                        user_id,
                        0,
                    )
                    + 1
                )

                save_json(
                    WARNINGS_FILE,
                    warnings,
                )

                await message.reply_text(
                    f"⚠️ {user.mention}\n"
                    f"عدد التحذيرات: "
                    f"**{bucket[user_id]}**"
                )

            elif text == "تحذيرات":

                count = bucket.get(
                    user_id,
                    0,
                )

                await message.reply_text(
                    f"⚠️ تحذيرات "
                    f"{user.mention}: "
                    f"**{count}**"
                )

            else:

                bucket[user_id] = 0

                save_json(
                    WARNINGS_FILE,
                    warnings,
                )

                await message.reply_text(
                    f"✅ تم مسح تحذيرات "
                    f"{user.mention}."
                )

            return

    # =====================================================
    #                  الحماية
    # =====================================================

    protection = re.match(
        r"^(قفل|فتح) "
        r"(الروابط|الصور|الفيديو|الملصقات|الصوت|السب)$",
        text,
    )

    if protection:

        if not await is_admin(message):

            await message.reply_text(
                "❌ للمشرفين فقط."
            )

            return

        action, item = protection.groups()

        settings_map = {
            "الروابط": "links",
            "الصور": "photos",
            "الفيديو": "videos",
            "الملصقات": "stickers",
            "الصوت": "audio",
            "السب": "badwords",
        }

        key = settings_map[item]

        set_setting(
            chat_id,
            key,
            action == "قفل",
        )

        if action == "قفل":

            await message.reply_text(
                f"🔒 تم قفل {item}."
            )

        else:

            await message.reply_text(
                f"🔓 تم فتح {item}."
            )

        return

    # =====================================================
    #                  الردود المضافة
    # =====================================================

    reply = custom_replies.get(
        str(chat_id),
        {},
    ).get(
        normalize(text)
    )

    if reply:

        await message.reply_text(
            reply
        )

        return


# =========================================================
#                انتظار اسم الأغنية
# =========================================================

@bot.on_message(
    filters.group & filters.text
)
async def waiting_song_handler(
    _,
    message,
):

    chat_id = message.chat.id

    text = (
        message.text or ""
    ).strip()

    if waiting_song.get(
        chat_id
    ) != message.from_user.id:

        return

    if text in (
        "تشغيل",
        "تخطي",
        "وقف",
        "إيقاف",
    ):

        return

    if text in (
        "الأوامر",
        "الاوامر",
        "مساعدة",
        "العاب",
        "ألعاب",
        "تفعيل البوت",
        "تعطيل البوت",
    ):

        return

    waiting_song.pop(
        chat_id,
        None,
    )

    if not get_setting(
        chat_id,
        "enabled",
        False,
    ):

        return

    try:

        result = await add_song(
            chat_id,
            text,
            message.from_user.mention,
        )

        await message.reply_text(
            result
        )

    except Exception as e:

        await message.reply_text(
            "❌ حصل خطأ في تشغيل الأغنية:\n"
            f"`{type(e).__name__}`"
        )


# =========================================================
#                  أزرار الموسيقى
# =========================================================

@bot.on_callback_query(
    filters.regex(
        r"^music_(skip|stop):"
    )
)
async def music_buttons(
    _,
    query,
):

    parts = query.data.split(":")

    action = parts[0]
    chat_id = int(parts[1])

    try:

        member = await bot.get_chat_member(
            chat_id,
            query.from_user.id,
        )

        status = str(
            member.status
        ).lower()

        if status not in (
            "owner",
            "creator",
            "administrator",
            "admin",
        ):

            await query.answer(
                "❌ للمشرفين فقط.",
                show_alert=True,
            )

            return

    except Exception:

        await query.answer(
            "❌ تعذر التحقق من صلاحيتك.",
            show_alert=True,
        )

        return

    if action == "music_skip":

        try:
            await calls.leave_call(
                chat_id
            )
        except Exception:
            pass

        current_song.pop(
            chat_id,
            None,
        )

        try:

            await play_next(
                chat_id
            )

        except Exception:
            pass

        await query.answer(
            "⏭️ تم التخطي."
        )

    else:

        try:
            await calls.leave_call(
                chat_id
            )
        except Exception:
            pass

        queues.pop(
            chat_id,
            None,
        )

        current_song.pop(
            chat_id,
            None,
        )

        await query.answer(
            "⏹️ تم الإيقاف."
        )


# =========================================================
#                  أزرار الألعاب
# =========================================================

@bot.on_callback_query(
    filters.regex(
        r"^game_(join|start|cancel):"
    )
)
async def game_buttons(
    _,
    query,
):

    action, chat_id_text = (
        query.data.split(":")
    )

    chat_id = int(
        chat_id_text
    )

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

    # -----------------------------------------------------
    # انضمام
    # -----------------------------------------------------

    if action == "join":

        if user_id not in session[
            "players"
        ]:

            if len(
                session["players"]
            ) >= 2:

                await query.answer(
                    "❌ اللعبة مكتملة.",
                    show_alert=True,
                )

                return

            session[
                "players"
            ].append(
                user_id
            )

        await query.answer(
            "✅ تم انضمامك للعبة."
        )

        try:

            players = session[
                "players"
            ]

            await query.message.edit_text(
                f"🎮 **{session['game']}**\n\n"
                f"👤 اللاعب الأول: `{players[0]}`\n"
                f"👤 اللاعب الثاني: `{players[1]}`\n\n"
                "اضغط «بدء اللعبة»."
                ,
                reply_markup=game_keyboard(
                    chat_id,
                    session["game"],
                ),
            )

        except Exception:
            pass

        return

    # -----------------------------------------------------
    # إلغاء
    # -----------------------------------------------------

    if action == "cancel":

        game_sessions.pop(
            chat_id,
            None,
        )

        await query.answer(
            "❌ تم إلغاء اللعبة."
        )

        try:

            await query.message.edit_text(
                "❌ تم إلغاء اللعبة."
            )

        except Exception:
            pass

        return

    # -----------------------------------------------------
    # بدء
    # -----------------------------------------------------

    if action == "start":

        if user_id != session[
            "host"
        ]:

            await query.answer(
                "❌ صاحب اللعبة هو اللي يبدأ.",
                show_alert=True,
            )

            return

        if (
            session["game"]
            in TWO_PLAYER_GAMES
            and len(
                session["players"]
            ) < 2
        ):

            await query.answer(
                "⏳ مستني اللاعب الثاني.",
                show_alert=True,
            )

            return

        session[
            "started"
        ] = True

        game = session[
            "game"
        ]

        # -----------------------------------------------
        # إكس أو
        # -----------------------------------------------

        if game == "إكس أو":

            session[
                "board"
            ] = [
                "⬜"
            ] * 9

            session[
                "turn"
            ] = 0

            await query.message.edit_text(
                "❌⭕ **إكس أو بدأت!**\n\n"
                "❌ اللاعب الأول\n"
                "⭕ اللاعب الثاني\n\n"
                "اللعبة هتكون بأزرار.",
                reply_markup=xo_keyboard(
                    chat_id
                ),
            )

            await query.answer(
                "🎮 بدأت!"
            )

            return

        # -----------------------------------------------
        # حجر ورق مقص
        # -----------------------------------------------

        if game == "حجر ورق مقص":

            session[
                "moves"
            ] = {}

            await query.message.edit_text(
                "✊✋✌️ **حجر ورق مقص**\n\n"
                "كل لاعب يختار حركته.",
                reply_markup=rps_keyboard(),
            )

            await query.answer(
                "🎮 بدأت!"
            )

            return

        # -----------------------------------------------
        # باقي الألعاب
        # -----------------------------------------------

        session[
            "target"
        ] = random.randint(
            1,
            10,
        )

        await query.message.edit_text(
            f"🎮 **{game}**\n\n"
            "🔥 بدأت الجولة!\n\n"
            "اكتب رقم من **1 إلى 10** "
            "وأول لاعب يوصل للرقم المطلوب يكسب.\n\n"
            "🎯 الرقم موجود عند البوت ومخفي."
        )

        await query.answer(
            "🎮 بدأت!"
        )


# =========================================================
#                       إكس أو
# =========================================================

def xo_keyboard(chat_id):

    rows = []

    for row in range(3):

        buttons = []

        for col in range(3):

            index = row * 3 + col

            buttons.append(
                InlineKeyboardButton(
                    "⬜",
                    callback_data=f"xo:{chat_id}:{index}",
                )
            )

        rows.append(buttons)

    return InlineKeyboardMarkup(
        rows
    )


def check_xo(board):

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

    for a, b, c in wins:

        if (
            board[a]
            == board[b]
            == board[c]
            != "⬜"
        ):

            return board[a]

    if "⬜" not in board:
        return "draw"

    return None


@bot.on_callback_query(
    filters.regex(
        r"^xo:"
    )
)
async def xo_handler(
    _,
    query,
):

    _, chat_text, index_text = (
        query.data.split(":")
    )

    chat_id = int(
        chat_text
    )

    index = int(
        index_text
    )

    session = game_sessions.get(
        chat_id
    )

    if not session:

        await query.answer(
            "❌ اللعبة انتهت.",
            show_alert=True,
        )

        return

    if not session.get(
        "started"
    ):

        return

    user_id = query.from_user.id

    if user_id not in session[
        "players"
    ]:

        await query.answer(
            "❌ أنت مش لاعب.",
            show_alert=True,
        )

        return

    turn = session[
        "turn"
    ]

    expected_user = session[
        "players"
    ][turn % 2]

    if user_id != expected_user:

        await query.answer(
            "⏳ استنى دورك.",
            show_alert=True,
        )

        return

    board = session[
        "board"
    ]

    if board[index] != "⬜":

        await query.answer(
            "❌ المكان متاخد.",
            show_alert=True,
        )

        return

    symbol = (
        "❌"
        if turn % 2 == 0
        else "⭕"
    )

    board[index] = symbol

    session[
        "turn"
    ] += 1

    result = check_xo(
        board
    )

    rows = []

    for row in range(3):

        buttons = []

        for col in range(3):

            i = row * 3 + col

            buttons.append(
                InlineKeyboardButton(
                    board[i],
                    callback_data=f"xo:{chat_id}:{i}",
                )
            )

        rows.append(buttons)

    if result:

        if result == "draw":

            text = (
                "🤝 **إكس أو**\n\n"
                "تعادل!"
            )

        else:

            winner = (
                session["players"][0]
                if result == "❌"
                else session["players"][1]
            )

            text = (
                "🏆 **إكس أو**\n\n"
                f"الفائز: `{winner}`"
            )

        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                rows
            ),
        )

        game_sessions.pop(
            chat_id,
            None,
        )

    else:

        await query.message.edit_text(
            "❌⭕ **إكس أو**\n\n"
            "دور اللاعب التالي:",
            reply_markup=InlineKeyboardMarkup(
                rows
            ),
        )

    await query.answer()


# =========================================================
#                    حجر ورق مقص
# =========================================================

@bot.on_callback_query(
    filters.regex(
        r"^rps:"
    )
)
async def rps_handler(
    _,
    query,
):

    chat_id = query.message.chat.id

    session = game_sessions.get(
        chat_id
    )

    if not session:

        await query.answer(
            "❌ اللعبة انتهت.",
            show_alert=True,
        )

        return

    if session.get(
        "game"
    ) != "حجر ورق مقص":

        return

    user_id = query.from_user.id

    if user_id not in session[
        "players"
    ]:

        await query.answer(
            "❌ أنت مش لاعب.",
            show_alert=True,
        )

        return

    move = query.data.split(
        ":"
    )[1]

    session.setdefault(
        "moves",
        {}
    )

    session[
        "moves"
    ][user_id] = move

    await query.answer(
        "✅ تم تسجيل اختيارك."
    )

    if len(
        session["moves"]
    ) < 2:

        return

    p1, p2 = session[
        "players"
    ]

    m1 = session[
        "moves"
    ][p1]

    m2 = session[
        "moves"
    ][p2]

    if m1 == m2:

        result = "🤝 تعادل!"

    elif (
        (m1, m2)
        in {
            ("rock", "scissors"),
            ("scissors", "paper"),
            ("paper", "rock"),
        }
    ):

        result = (
            f"🏆 اللاعب الأول فاز!\n"
            f"`{p1}`"
        )

    else:

        result = (
            f"🏆 اللاعب الثاني فاز!\n"
            f"`{p2}`"
        )

    await query.message.reply_text(
        "✊✋✌️ **النتيجة**\n\n"
        + result
    )

    game_sessions.pop(
        chat_id,
        None,
    )


# =========================================================
#                ألعاب الأرقام العامة
# =========================================================

@bot.on_message(
    filters.group & filters.text
)
async def active_game_answer(
    _,
    message,
):

    chat_id = message.chat.id

    session = game_sessions.get(
        chat_id
    )

    if not session:
        return

    if not session.get(
        "started"
    ):
        return

    game = session.get(
        "game"
    )

    if game in (
        "إكس أو",
        "حجر ورق مقص",
    ):
        return

    text = (
        message.text or ""
    ).strip()

    if not text.isdigit():
        return

    number = int(text)

    if not (
        1 <= number <= 10
    ):
        return

    target = session.get(
        "target"
    )

    if number == target:

        await message.reply_text(
            "🏆 **كسبت!**\n\n"
            f"🎮 اللعبة: {game}\n"
            f"🎯 الرقم كان: **{target}**"
        )

        game_sessions.pop(
            chat_id,
            None,
        )

    else:

        await message.reply_text(
            "❌ غلط 😄\n"
            "جرب رقم تاني من 1 إلى 10."
        )


# =========================================================
#                     الترحيب
# =========================================================

@bot.on_message(
    filters.new_chat_members
)
async def welcome_handler(
    _,
    message,
):

    names = ", ".join(
        user.mention
        for user in message.new_chat_members
    )

    await message.reply_text(
        f"👋 أهلاً {names} ❤️\n"
        "نورتوا الجروب!"
    )


# =========================================================
#                  الحماية التلقائية
# =========================================================

BAD_WORDS = {
    "كلمة_ممنوعة_1",
    "كلمة_ممنوعة_2",
}


URL_RE = re.compile(
    r"(https?://\S+|www\.\S+|t\.me/\S+)",
    re.I,
)


@bot.on_message(
    filters.group
)
async def protection_handler(
    _,
    message,
):

    if not message.from_user:
        return

    chat_id = message.chat.id

    try:

        member = await bot.get_chat_member(
            chat_id,
            message.from_user.id,
        )

        status = str(
            member.status
        ).lower()

        if status in (
            "owner",
            "creator",
            "administrator",
            "admin",
        ):

            return

    except Exception:

        return

    text = (
        message.text
        or message.caption
        or ""
    )

    try:

        if (
            get_setting(
                chat_id,
                "links",
            )
            and URL_RE.search(text)
        ):

            await message.delete()

            return

        if (
            get_setting(
                chat_id,
                "badwords",
            )
            and any(
                word in text.casefold()
                for word in BAD_WORDS
            )
        ):

            await message.delete()

            return

        if (
            get_setting(
                chat_id,
                "photos",
            )
            and message.photo
        ):

            await message.delete()

            return

        if (
            get_setting(
                chat_id,
                "videos",
            )
            and message.video
        ):

            await message.delete()

            return

        if (
            get_setting(
                chat_id,
                "stickers",
            )
            and message.sticker
        ):

            await message.delete()

            return

        if (
            get_setting(
                chat_id,
                "audio",
            )
            and (
                message.audio
                or message.voice
            )
        ):

            await message.delete()

            return

    except Exception:
        pass


# =========================================================
#                       MAIN
# =========================================================

async def main():

    global calls

    print(
        "========== BOT FILE STARTED =========="
    )

    # تشغيل البوت
    await bot.start()

    print(
        "========== BOT STARTED =========="
    )

    # تشغيل حساب المساعد
    await assistant.start()

    print(
        "========== ASSISTANT STARTED =========="
    )

    # تشغيل PyTgCalls بعد دخول الـ event loop
    calls = PyTgCalls(
        assistant
    )

    calls.start()

    print(
        "========== PYTGCALLS STARTED =========="
    )

    # إبقاء البوت شغال
    await idle()


if __name__ == "__main__":

    asyncio.run(
        main()
    )
