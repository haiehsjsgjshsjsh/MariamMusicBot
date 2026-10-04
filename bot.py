import os
import re
import random
import asyncio
import logging
from pathlib import Path

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus

from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, GroupCallConfig
from pytgcalls import filters as tgcall_filters
from pytgcalls.types import StreamEnded


# =========================================================
# إعدادات Railway
# =========================================================

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")

if not API_ID or not API_HASH:
    raise RuntimeError("ضع API_ID و API_HASH في Railway Variables")

if not BOT_TOKEN:
    raise RuntimeError("ضع BOT_TOKEN في Railway Variables")

if not SESSION_STRING:
    raise RuntimeError("ضع SESSION_STRING في Railway Variables")


# =========================================================
# Logging
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

log = logging.getLogger("MariamMusicBot")


# =========================================================
# Bot
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
# بيانات التشغيل
# =========================================================

active_bots = set()

playing = {}
queues = {}
game_state = {}

custom_replies = {}

bad_words = {
    "كس",
    "شرموط",
    "شرموطة",
    "خول",
    "متناك",
    "نيك",
    "زانية",
    "قحبة",
}


# =========================================================
# الألعاب
# =========================================================

games = [
    "جمع",
    "طرح",
    "ضرب",
    "تخمين",
    "حظ",
    "صح او غلط",
    "XO",
]


# =========================================================
# أدوات مساعدة
# =========================================================

async def is_admin(message: Message):
    try:
        member = await bot.get_chat_member(
            message.chat.id,
            message.from_user.id
        )

        return member.status in (
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR,
        )

    except Exception:
        return False


async def bot_is_active(message: Message):
    return message.chat.id in active_bots


async def send_safe(message: Message, text: str):
    try:
        await message.reply_text(text)
    except Exception as e:
        log.error("send error: %s", e)


# =========================================================
# الأوامر
# =========================================================

@bot.on_message(filters.command("start") | filters.regex(r"^/الأوامر$"))
async def start_command(client, message: Message):

    text = """
🌹 مريومه الدلوعه 🌹

🎵 قسم الموسيقى:

تشغيل
تشغيل اسم الأغنية
إيقاف
تخطي

🎮 قسم الألعاب:

العاب
إيقاف اللعبة

⚙️ قسم الإدارة:

تفعيل البوت
تعطيل البوت
منع السب

💬 الردود:

اضف رد الكلمة الرد
مسح الرد الكلمة

📋 الأوامر
"""

    await message.reply_text(text)


@bot.on_message(filters.regex(r"^الأوامر$"))
async def commands_ar(client, message: Message):

    await message.reply_text(
        """
📋 أوامر مريومه الدلوعه

🎵 الموسيقى:
• تشغيل
• تشغيل اسم الأغنية
• تخطي
• إيقاف

🎮 الألعاب:
• العاب
• اسم اللعبة
• إيقاف اللعبة

⚙️ البوت:
• تفعيل البوت
• تعطيل البوت

💬 الردود:
• اضف رد الكلمة الرد
• مسح الرد الكلمة

🛡️ الحماية:
• منع السب
"""
    )


# =========================================================
# تفعيل البوت
# =========================================================

@bot.on_message(filters.regex(r"^تفعيل البوت$"))
async def activate_bot(client, message: Message):

    if not await is_admin(message):
        await message.reply_text("❌ الأمر ده للمشرفين فقط.")
        return

    active_bots.add(message.chat.id)

    await message.reply_text(
        "✅ تم تفعيل البوت في الجروب.\n\n"
        "🎵 تقدر تستخدم: تشغيل اسم الأغنية\n"
        "🎮 وتقدر تستخدم: العاب"
    )


@bot.on_message(filters.regex(r"^تعطيل البوت$"))
async def deactivate_bot(client, message: Message):

    if not await is_admin(message):
        await message.reply_text("❌ الأمر ده للمشرفين فقط.")
        return

    active_bots.discard(message.chat.id)

    try:
        await voice.leave_call(message.chat.id)
    except Exception:
        pass

    playing.pop(message.chat.id, None)
    queues.pop(message.chat.id, None)
    game_state.pop(message.chat.id, None)

    await message.reply_text("🛑 تم تعطيل البوت.")


# =========================================================
# تشغيل الموسيقى
# =========================================================

async def play_song(chat_id: int, song: str):

    log.info("Searching for: %s", song)

    # yt-dlp search
    import yt_dlp

    options = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "default_search": "ytsearch1",
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:

            result = await asyncio.to_thread(
                ydl.extract_info,
                f"ytsearch1:{song}",
                False
            )

        if not result or not result.get("entries"):
            return None

        info = result["entries"][0]

        return {
            "title": info.get("title", song),
            "url": info.get("webpage_url"),
        }

    except Exception as e:
        log.exception("yt-dlp search error: %s", e)
        return None


async def start_song(chat_id: int, song: str):

    result = await play_song(chat_id, song)

    if not result:
        await bot.send_message(
            chat_id,
            "❌ مش قادر ألاقي الأغنية."
        )
        return

    title = result["title"]
    url = result["url"]

    try:

        # API الحالية لـ PyTgCalls
        stream = MediaStream(
            url,
            video_flags=MediaStream.Flags.IGNORE,
        )

        await voice.play(
            chat_id,
            stream,
            config=GroupCallConfig(
                auto_start=True
            )
        )

        playing[chat_id] = {
            "title": title,
            "url": url,
        }

        await bot.send_message(
            chat_id,
            f"🎵 الآن يتم تشغيل:\n\n"
            f"🎶 {title}\n\n"
            f"⏭️ تخطي\n"
            f"⏹️ إيقاف"
        )

        log.info(
            "Playing in %s: %s",
            chat_id,
            title
        )

    except Exception as e:

        log.exception("voice.play error")

        await bot.send_message(
            chat_id,
            "❌ مقدرتش أشغل الموسيقى.\n\n"
            "تأكد أن حساب SESSION_STRING موجود في الجروب "
            "ومسموح له بإدارة المحادثة الصوتية."
        )


# =========================================================
# أمر تشغيل
# =========================================================

@bot.on_message(
    filters.regex(
        r"^تشغيل(?:\s+(.+))?$"
    )
)
async def music_command(client, message: Message):

    if not await bot_is_active(message):
        await message.reply_text(
            "❌ البوت غير مفعل.\n"
            "اكتب: تفعيل البوت"
        )
        return

    match = re.match(
        r"^تشغيل(?:\s+(.+))?$",
        message.text.strip()
    )

    song = match.group(1) if match else None

    if not song:
        await message.reply_text(
            "🎵 قول اسم الأغنية بعد تشغيل.\n\n"
            "مثال:\n"
            "تشغيل مانو"
        )
        return

    await message.reply_text(
        f"🔎 بدور على الأغنية...\n\n🎵 {song}"
    )

    await start_song(
        message.chat.id,
        song
    )


# =========================================================
# تخطي
# =========================================================

@bot.on_message(filters.regex(r"^تخطي$"))
async def skip_song(client, message: Message):

    if not await bot_is_active(message):
        return

    chat_id = message.chat.id

    if chat_id not in playing:
        await message.reply_text(
            "❌ مفيش أغنية شغالة."
        )
        return

    await message.reply_text(
        "⏭️ تم تخطي الأغنية."
    )

    queues.setdefault(chat_id, [])

    try:
        await voice.leave_call(chat_id)
    except Exception:
        pass

    playing.pop(chat_id, None)

    if queues[chat_id]:

        next_song = queues[chat_id].pop(0)

        await start_song(
            chat_id,
            next_song
        )


# =========================================================
# إيقاف الموسيقى
# =========================================================

@bot.on_message(filters.regex(r"^إيقاف$"))
async def stop_music(client, message: Message):

    chat_id = message.chat.id

    try:
        await voice.leave_call(chat_id)
    except Exception as e:
        log.warning(
            "leave_call: %s",
            e
        )

    playing.pop(chat_id, None)
    queues.pop(chat_id, None)

    await message.reply_text(
        "⏹️ تم إيقاف الموسيقى."
    )


# =========================================================
# انتهاء الأغنية
# =========================================================

@voice.on_update(tgcall_filters.stream_end())
async def stream_finished(_, update: StreamEnded):

    chat_id = update.chat_id

    log.info(
        "Stream ended: %s",
        chat_id
    )

    playing.pop(chat_id, None)

    if queues.get(chat_id):

        next_song = queues[chat_id].pop(0)

        await start_song(
            chat_id,
            next_song
        )


# =========================================================
# الألعاب
# =========================================================

@bot.on_message(filters.regex(r"^العاب$"))
async def games_list(client, message: Message):

    text = """
🎮 ألعاب مريومه الدلوعه 🎮

1️⃣ جمع
2️⃣ طرح
3️⃣ ضرب
4️⃣ تخمين
5️⃣ حظ
6️⃣ صح او غلط
7️⃣ XO

💡 اكتب اسم اللعبة عشان تبدأ.

مثال:
جمع

🛑 لإيقاف اللعبة:
إيقاف اللعبة
"""

    await message.reply_text(text)


# =========================================================
# بدء لعبة جمع
# =========================================================

def create_math_game():

    a = random.randint(1, 50)
    b = random.randint(1, 50)

    return a, b, a + b


@bot.on_message(filters.regex(r"^جمع$"))
async def game_add(client, message: Message):

    chat_id = message.chat.id

    a, b, answer = create_math_game()

    game_state[chat_id] = {
        "type": "math",
        "answer": answer,
    }

    await message.reply_text(
        f"🧮 لعبة الجمع بدأت!\n\n"
        f"❓ {a} + {b} = ؟\n\n"
        f"اكتب الإجابة."
    )


# =========================================================
# لعبة الطرح
# =========================================================

@bot.on_message(filters.regex(r"^طرح$"))
async def game_sub(client, message: Message):

    chat_id = message.chat.id

    a = random.randint(20, 100)
    b = random.randint(1, 20)

    answer = a - b

    game_state[chat_id] = {
        "type": "math",
        "answer": answer,
    }

    await message.reply_text(
        f"➖ لعبة الطرح بدأت!\n\n"
        f"❓ {a} - {b} = ؟"
    )


# =========================================================
# لعبة الضرب
# =========================================================

@bot.on_message(filters.regex(r"^ضرب$"))
async def game_mul(client, message: Message):

    chat_id = message.chat.id

    a = random.randint(2, 12)
    b = random.randint(2, 12)

    answer = a * b

    game_state[chat_id] = {
        "type": "math",
        "answer": answer,
    }

    await message.reply_text(
        f"✖️ لعبة الضرب بدأت!\n\n"
        f"❓ {a} × {b} = ؟"
    )


# =========================================================
# لعبة الحظ
# =========================================================

@bot.on_message(filters.regex(r"^حظ$"))
async def luck_game(client, message: Message):

    result = random.choice(
        [
            "🍀 حظك حلو جدًا!",
            "😎 النهارده يومك!",
            "😂 حظك محتاج شوية شغل!",
            "🔥 حظك جامد!",
            "💔 المرة الجاية أحسن!",
        ]
    )

    await message.reply_text(result)


# =========================================================
# لعبة التخمين
# =========================================================

@bot.on_message(filters.regex(r"^تخمين$"))
async def guessing_game(client, message: Message):

    number = random.randint(1, 10)

    game_state[message.chat.id] = {
        "type": "guess",
        "answer": number,
    }

    await message.reply_text(
        "🎯 لعبة التخمين بدأت!\n\n"
        "أنا اخترت رقم من 1 إلى 10.\n"
        "خمن الرقم!"
    )


# =========================================================
# صح أو غلط
# =========================================================

@bot.on_message(filters.regex(r"^صح او غلط$"))
async def true_false_game(client, message: Message):

    questions = [
        (
            "🌍 القاهرة عاصمة مصر.",
            "صح"
        ),
        (
            "🌙 الشمس تظهر في الليل.",
            "غلط"
        ),
        (
            "🐘 الفيل من أكبر الحيوانات البرية.",
            "صح"
        ),
    ]

    question, answer = random.choice(
        questions
    )

    game_state[message.chat.id] = {
        "type": "tf",
        "answer": answer,
    }

    await message.reply_text(
        f"❓ {question}\n\n"
        "اكتب: صح أو غلط"
    )


# =========================================================
# إيقاف اللعبة
# =========================================================

@bot.on_message(filters.regex(r"^إيقاف اللعبة$"))
async def stop_game(client, message: Message):

    chat_id = message.chat.id

    if chat_id not in game_state:
        await message.reply_text(
            "❌ مفيش لعبة شغالة."
        )
        return

    game_state.pop(chat_id, None)

    await message.reply_text(
        "🛑 تم إيقاف اللعبة.\n"
        "تقدر تبدأ لعبة جديدة دلوقتي 🎮"
    )


# =========================================================
# فحص إجابات الألعاب
# =========================================================

@bot.on_message(
    filters.text
    & ~filters.regex(r"^تشغيل")
    & ~filters.regex(r"^إيقاف$")
    & ~filters.regex(r"^إيقاف اللعبة$")
)
async def game_answer_and_replies(
    client,
    message: Message
):

    chat_id = message.chat.id
    text = message.text.strip()

    # -----------------------------------------
    # إجابة لعبة
    # -----------------------------------------

    if chat_id in game_state:

        state = game_state[chat_id]

        game_type = state["type"]

        if game_type == "math":

            try:
                answer = int(text)
            except ValueError:
                return

            if answer == state["answer"]:

                await message.reply_text(
                    "✅ إجابة صحيحة! 🎉"
                )

                game_state.pop(
                    chat_id,
                    None
                )

            else:

                await message.reply_text(
                    "❌ إجابة غلط 😄"
                )

            return

        if game_type == "guess":

            try:
                answer = int(text)
            except ValueError:
                return

            correct = state["answer"]

            if answer == correct:

                await message.reply_text(
                    "🎉 صح! خمنت الرقم صح!"
                )

                game_state.pop(
                    chat_id,
                    None
                )

            elif answer < correct:

                await message.reply_text(
                    "⬆️ الرقم أكبر."
                )

            else:

                await message.reply_text(
                    "⬇️ الرقم أصغر."
                )

            return

        if game_type == "tf":

            normalized = text.lower()

            if normalized not in (
                "صح",
                "غلط",
                "خطأ"
            ):
                return

            correct = state["answer"]

            if (
                normalized == correct
                or (
                    normalized == "خطأ"
                    and correct == "غلط"
                )
            ):

                await message.reply_text(
                    "✅ إجابة صحيحة! 🎉"
                )

            else:

                await message.reply_text(
                    "❌ إجابة غلط."
                )

            game_state.pop(
                chat_id,
                None
            )

            return

    # -----------------------------------------
    # الردود المخصصة
    # -----------------------------------------

    key = text.lower()

    if chat_id in custom_replies:

        if key in custom_replies[chat_id]:

            await message.reply_text(
                custom_replies[chat_id][key]
            )

            return


# =========================================================
# إضافة رد
# =========================================================

@bot.on_message(
    filters.regex(
        r"^اضف رد\s+(.+?)\s+(.+)$"
    )
)
async def add_reply(client, message: Message):

    if not await is_admin(message):
        await message.reply_text(
            "❌ الأمر ده للمشرفين فقط."
        )
        return

    match = re.match(
        r"^اضف رد\s+(.+?)\s+(.+)$",
        message.text.strip()
    )

    key = match.group(1).lower()
    reply = match.group(2)

    custom_replies.setdefault(
        message.chat.id,
        {}
    )

    custom_replies[
        message.chat.id
    ][key] = reply

    await message.reply_text(
        f"✅ تم إضافة الرد للكلمة:\n"
        f"«{key}»"
    )


# =========================================================
# مسح رد
# =========================================================

@bot.on_message(
    filters.regex(
        r"^مسح الرد\s+(.+)$"
    )
)
async def delete_reply(client, message: Message):

    if not await is_admin(message):
        await message.reply_text(
            "❌ الأمر ده للمشرفين فقط."
        )
        return

    key = message.text.split(
        " ",
        2
    )[2].lower()

    replies = custom_replies.get(
        message.chat.id,
        {}
    )

    if key not in replies:

        await message.reply_text(
            "❌ الرد ده مش موجود."
        )

        return

    del replies[key]

    await message.reply_text(
        f"🗑️ تم مسح الرد: {key}"
    )


# =========================================================
# منع السب
# =========================================================

@bot.on_message(
    filters.group
    & filters.text
)
async def anti_bad_words(client, message: Message):

    text = message.text.lower()

    found = any(
        word in text
        for word in bad_words
    )

    if not found:
        return

    try:

        await message.delete()

        await bot.send_message(
            message.chat.id,
            "🚫 ممنوع السب في الجروب."
        )

    except Exception as e:

        log.warning(
            "anti bad words error: %s",
            e
        )


# =========================================================
# تشغيل البوت
# =========================================================

async def main():

    await bot.start()

    await assistant.start()

    await voice.start()

    me = await bot.get_me()
    assistant_me = await assistant.get_me()

    log.info(
        "Bot started: @%s",
        me.username
    )

    log.info(
        "Assistant started: %s | %s",
        assistant_me.first_name,
        assistant_me.id
    )

    print(
        "================================="
    )

    print(
        "MariamMusicBot is running"
    )

    print(
        "Bot: @%s",
        me.username
    )

    print(
        "Assistant: %s",
        assistant_me.first_name
    )

    print(
        "================================="
    )

    await asyncio.Event().wait()


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:

        log.info(
            "Bot stopped."
        )

    except Exception as e:

        log.exception(
            "Fatal error: %s",
            e
        )
