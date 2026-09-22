import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())

import os
import json
import random
import re
from pathlib import Path

import static_ffmpeg
import yt_dlp
import pyrogram.errors

static_ffmpeg.add_paths()


# =========================================================
# PyTgCalls compatibility
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


from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from pyrogram.enums import ChatMemberStatus

from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, GroupCallConfig


# =========================================================
# Railway Variables
# =========================================================

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
SESSION_STRING = os.environ["SESSION_STRING"]


# =========================================================
# Settings
# =========================================================

REQUIRED_CHAT = "@mariamqueennuriii"
REQUIRED_CHAT_LINK = "https://t.me/mariamqueennuriii"

PHOTO_PATH = "IMG_20260922_130735_050.jpg"

CUSTOM_REPLIES_FILE = "custom_replies.json"


# =========================================================
# Clients
# =========================================================

bot = Client(
    "MariamMusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

assistant = Client(
    "MariamMusicAssistant",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

calls = PyTgCalls(assistant)


# =========================================================
# Runtime Data
# =========================================================

queues = {}
playing = {}
waiting_for_song = {}
paused = {}


# =========================================================
# Custom Replies Storage
# =========================================================

def load_custom_replies():
    if not os.path.exists(CUSTOM_REPLIES_FILE):
        return {}

    try:
        with open(
            CUSTOM_REPLIES_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)

        if isinstance(data, dict):
            return data

        return {}

    except Exception as e:
        print("CUSTOM REPLIES LOAD ERROR:", repr(e))
        return {}


custom_replies = load_custom_replies()


def save_custom_replies():
    try:
        with open(
            CUSTOM_REPLIES_FILE,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                custom_replies,
                f,
                ensure_ascii=False,
                indent=2
            )

    except Exception as e:
        print("CUSTOM REPLIES SAVE ERROR:", repr(e))


# =========================================================
# Membership - Private Verification Only
# =========================================================

async def is_user_joined(user_id):
    try:
        member = await bot.get_chat_member(
            REQUIRED_CHAT,
            user_id
        )

        status = str(member.status).lower()

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
            "MEMBERSHIP CHECK ERROR:",
            repr(e)
        )

        return False


async def send_join_message(message):

    try:
        me = await bot.get_me()
        username = me.username or "MariamMusicBot"

    except Exception:
        username = "MariamMusicBot"

    add_link = (
        f"https://t.me/{username}"
        "?startgroup=musicbot"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "➕ أضفني لمجموعتك",
                url=add_link
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
    ])

    await message.reply_text(
        "🎵 <b>مريومه الدلوعه</b>\n\n"
        "لاستخدام البوت:\n\n"
        "1️⃣ أضف البوت لمجموعتك.\n"
        "2️⃣ انضم للمجموعة المطلوبة.\n"
        "3️⃣ اضغط «✅ تحقق».\n\n"
        "بعد التحقق تقدر تستخدم البوت.",
        reply_markup=keyboard
    )


async def require_private_access(message):

    if not message.from_user:
        return False

    if await is_user_joined(
        message.from_user.id
    ):
        return True

    await send_join_message(message)

    return False


# =========================================================
# Admin Check
# =========================================================

async def is_admin(chat_id, user_id):

    try:
        member = await bot.get_chat_member(
            chat_id,
            user_id
        )

        return member.status in (
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR
        )

    except Exception:
        return False


# =========================================================
# Welcome System
# =========================================================

WELCOME_MESSAGES = [
    "🎉 أهلاً وسهلاً بيك {name} ❤️\nنورت الجروب وشرفتنا 🌹",

    "🌹 يا أهلاً ويا سهلاً بـ {name} ❤️\nنورتنا يا جميل 😍",

    "❤️ أهلاً بيك يا {name}\nالجروب نور بوجودك 🌷",

    "🎊 نورتنا يا {name} ❤️\nأهلاً بيك بين إخواتك 🌹",

    "✨ أهلاً يا {name} ❤️\nمنور الجروب يا غالي 😎",

    "🌸 أهلاً وسهلاً يا {name}\nنورت المكان كله ❤️",

    "🔥 نورتنا يا {name} ❤️\nأهلاً بيك معانا 🌹",

    "💗 أهلاً يا {name}\nوجودك نور الجروب ❤️",

    "🎀 أهلاً بيك يا {name} ❤️\nنورتنا وشرفتـنا 🌹",

    "🥰 يا أهلاً بـ {name}\nمنور الجروب يا جميل ❤️"
]


@bot.on_message(
    filters.group &
    filters.new_chat_members
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

        welcome = random.choice(
            WELCOME_MESSAGES
        )

        welcome = welcome.replace(
            "{name}",
            name
        )

        try:
            await message.reply_text(
                welcome
            )

        except Exception as e:
            print(
                "WELCOME ERROR:",
                repr(e)
            )


# =========================================================
# Built-in Automatic Replies
# =========================================================

BUILTIN_REPLIES = {

    "السلام عليكم": [
        "وعليكم السلام ورحمة الله وبركاته ❤️",
        "وعليكم السلام يا جميل 🌹",
        "وعليكم السلام ❤️"
    ],

    "السلام عليكم ورحمة الله": [
        "وعليكم السلام ورحمة الله وبركاته ❤️",
        "وعليكم السلام يا غالي 🌹"
    ],

    "ازيك": [
        "الحمد لله تمام ❤️",
        "بخير الحمد لله 😎",
        "تمام يا نجم ❤️"
    ],

    "عامل ايه": [
        "تمام الحمد لله ❤️",
        "بخير يا صاحبي 😎",
        "زي الفل 😂❤️"
    ],

    "عامل إيه": [
        "تمام الحمد لله ❤️",
        "الحمد لله كله تمام 🌹",
        "زي الفل 😎"
    ],

    "صباح الخير": [
        "صباح النور والسرور ☀️❤️",
        "صباح الفل 🌹",
        "صباح الورد 🌷"
    ],

    "مساء الخير": [
        "مساء النور ❤️",
        "مساء الفل 🌹",
        "مساء الورد 🌷"
    ],

    "تصبح على خير": [
        "وإنت من أهله ❤️",
        "أحلام سعيدة 🌙",
        "نوم العوافي 😴"
    ],

    "شكرا": [
        "العفو ❤️",
        "ولا يهمك يا غالي 🌹",
        "تحت أمرك ❤️"
    ],

    "شكراً": [
        "العفو ❤️",
        "ولا يهمك يا غالي 🌹",
        "تحت أمرك ❤️"
    ],

    "بحبك": [
        "وأنا بحب الناس الحلوة ❤️",
        "يا روحي 😂❤️",
        "ده من ذوقك 🌹"
    ],

    "وحشتني": [
        "وإنت كمان وحشتني ❤️",
        "وأنت أكتر 😭❤️",
        "منور الدنيا ❤️"
    ],

    "فينك": [
        "موجود أهو 😎",
        "هنا معاكم ❤️",
        "أنا موجود يا صاحبي"
    ],

    "مين هنا": [
        "أنا هنا 😎",
        "كلنا هنا 😂",
        "أهل الجروب موجودين ❤️"
    ],

    "مريومه": [
        "نعم يا قلبي ❤️",
        "أيوه يا جميل 🌹",
        "قول يا غالي 👀"
    ],

    "مريم": [
        "نعم ❤️",
        "أيوه يا جميل 🌹",
        "قول اللي عندك 😄"
    ],

    "يا بوت": [
        "نعم؟ 👀",
        "أيوه يا باشا 😎",
        "قول طلبك"
    ],

    "بوت": [
        "معاك يا نجم 😎",
        "نعم؟ 👀",
        "أوامرك ❤️"
    ],

    "اهلا": [
        "أهلاً وسهلاً ❤️",
        "يا أهلاً بيك 🌹",
        "منور الجروب ❤️"
    ],

    "أهلا": [
        "أهلاً وسهلاً ❤️",
        "يا أهلاً بيك 🌹",
        "منور الجروب ❤️"
    ],

    "هاي": [
        "هاي يا جميل ❤️",
        "هلا والله 🌹",
        "منور 😎"
    ],

    "hello": [
        "Hello ❤️",
        "أهلاً وسهلاً 😎",
        "Welcome ❤️"
    ],

    "hi": [
        "Hi ❤️",
        "أهلاً بيك 🌹",
        "منور 😎"
    ],

    "تمام": [
        "دايمًا يا رب ❤️",
        "تمام التمام 😎",
        "الحمد لله 🌹"
    ],

    "كويس": [
        "الحمد لله ❤️",
        "دايمًا يا رب 🌹",
        "ربنا يديمها عليك ❤️"
    ],

    "الحمد لله": [
        "دوم الحمد لله ❤️",
        "ربنا يديمها نعمة 🌹",
        "يارب دايمًا 🙏"
    ],

    "مبروك": [
        "الله يبارك فيك ❤️",
        "ألف مبروك 🎉",
        "تستاهل كل خير 🌹"
    ],

    "تسلم": [
        "تسلم يا غالي ❤️",
        "حبيبي 🌹",
        "من ذوقك ❤️"
    ],

    "حبيبي": [
        "حبيب قلبي ❤️",
        "يا روحي 🌹",
        "حبيبي يا نجم 😎"
    ],

    "يا غالي": [
        "يا غالي على قلبي ❤️",
        "تؤمر يا غالي 😎",
        "منور ❤️"
    ],

    "يا نجم": [
        "عيون النجم ❤️",
        "تؤمر يا نجم 😎",
        "حبيب قلبي 🌹"
    ],

    "يا باشا": [
        "أيوه يا باشا 😎",
        "تؤمر ❤️",
        "قول يا كبير 🔥"
    ],

    "يا كبير": [
        "حبيب الكبير ❤️",
        "تؤمر يا كبير 😎",
        "قول بس 🌹"
    ],

    "ربنا يخليك": [
        "ويخليك لينا ❤️",
        "حبيبي يا غالي 🌹",
        "ربنا يسعدك ❤️"
    ],

    "ربنا يسعدك": [
        "ويسعدك يا رب ❤️",
        "آمين يا رب 🙏",
        "ويسعد قلبك 🌹"
    ],

    "ربنا يوفقك": [
        "ويوفقنا كلنا يا رب ❤️",
        "آمين يا رب 🙏",
        "ربنا يكرمك 🌹"
    ],

    "ربنا معاك": [
        "ومعاك يا رب ❤️",
        "آمين يا رب 🙏",
        "ربنا يحفظك 🌹"
    ],

    "هههه": [
        "دوم الضحكة 😂❤️",
        "ضحكتك حلوة 😂",
        "ربنا يديمها 😄"
    ],

    "ههههه": [
        "دوم يا رب 😂❤️",
        "ضحكتك معدية 😂",
        "ربنا يسعدك ❤️"
    ],

    "😂": [
        "دوم الضحكة 😂❤️",
        "إيه اللي بيضحكك؟ 😂",
        "ربنا يسعدك 😄"
    ],

    "زهقان": [
        "تعالى نولع الجروب 😂🔥",
        "متزهقش يا نجم ❤️",
        "شغل أغنية ونروق 😎"
    ],

    "زهقانة": [
        "تعالي نولع الجروب 😂🔥",
        "متزهقيش يا جميلة ❤️",
        "شغلي أغنية ونروق 😎"
    ],

    "ملل": [
        "مفيش ملل مع مريومه 😂🔥",
        "شغل أغنية ونروق 🎵",
        "يلا نكسر الملل ❤️"
    ]
}


# =========================================================
# إضافة عبارات تلقائية حتى يصبح العدد 500
# =========================================================

EXTRA_TRIGGERS = [
    "اخبارك",
    "أخبارك",
    "اخباركم",
    "أخباركم",
    "عاملين ايه",
    "عاملين إيه",
    "جامد",
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
    "حد موجود",
    "فين الناس",
    "الناس فين",
    "تعالى",
    "تعالي",
    "تعالوا",
    "استنى",
    "استني",
    "لحظة",
    "دقيقة",
    "معلش",
    "اسف",
    "آسف",
    "اسفة",
    "آسفة",
    "مبروك عليك",
    "كل سنة وانت طيب",
    "كل سنة وانتي طيبة",
    "رمضان كريم",
    "عيد سعيد",
    "جمعة مباركة",
    "يا نجمة",
    "يا صاحبي",
    "يا صاحبتي",
    "يا قلبي",
    "يا روحي",
    "يا عم",
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
    "جامد اوي",
    "حلو اوي",
    "عاش",
    "برافو",
    "كفو",
    "احسنت",
    "أحسنت",
    "شطورة",
    "شاطر",
