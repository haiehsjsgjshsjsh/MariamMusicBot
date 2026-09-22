import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())

import os
import static_ffmpeg
import yt_dlp
import pyrogram.errors

# تشغيل FFmpeg و FFprobe
static_ffmpeg.add_paths()

# =========================
# توافق PyTgCalls مع Pyrogram
# =========================

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

from pytgcalls import PyTgCalls
from pytgcalls.types import (
    MediaStream,
    GroupCallConfig
)


# =========================================================
# بيانات Railway
# =========================================================

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
SESSION_STRING = os.environ["SESSION_STRING"]


# =========================================================
# المجموعة المطلوبة
# =========================================================

REQUIRED_CHAT = "@mariamqueennuriii"


# اسم الصورة
PHOTO_PATH = "IMG_20260922_130735_050.jpg"


# =========================================================
# البوت
# =========================================================

bot = Client(
    "MariamMusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)


# =========================================================
# الحساب المساعد
# =========================================================

assistant = Client(
    "MariamMusicAssistant",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)


calls = PyTgCalls(assistant)


# =========================================================
# البيانات
# =========================================================

queues = {}
playing = {}
waiting_for_song = {}
paused = {}


# =========================================================
# التحقق من الاشتراك
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

            if getattr(member, "is_member", False):
                return True

        return False

    except Exception as e:

        print(
            "MEMBERSHIP CHECK ERROR:",
            repr(e)
        )

        return False


# =========================================================
# الحصول على اسم البوت تلقائيًا
# =========================================================

async def get_bot_username():

    try:

        me = await bot.get_me()

        return me.username

    except Exception:

        return "MariamMusicBot"


# =========================================================
# رسالة التحقق
# =========================================================

async def send_join_message(message):

    bot_username = await get_bot_username()

    add_bot_link = (
        f"https://t.me/{bot_username}"
        f"?startgroup=musicbot"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "➕ أضفني لمجموعتك",
                    url=add_bot_link
                )
            ],
            [
                InlineKeyboardButton(
                    "📢 انضم للمجموعة",
                    url="https://t.me/mariamqueennuriii"
                )
            ],
            [
                InlineKeyboardButton(
                    "✅ تحقق",
                    callback_data="check_join"
                )
            ]
        ]
    )

    await message.reply_text(
        "🎵 <b>أهلًا بيك في مريومه الدلوعه</b>\n\n"
        "لاستخدام البوت لازم تعمل الخطوات دي:\n\n"
        "1️⃣ أضف البوت لمجموعتك.\n"
        "2️⃣ انضم للمجموعة المطلوبة.\n"
        "3️⃣ اضغط «✅ تحقق».\n\n"
        "بعد التحقق تقدر تستخدم أوامر تشغيل الأغاني.",
        reply_markup=keyboard
    )


# =========================================================
# التحقق من صلاحية المستخدم
# =========================================================

async def require_access(message):

    if not message.from_user:
        return False

    user_id = message.from_user.id

    joined = await is_user_joined(
        user_id
    )

    if not joined:

        await send_join_message(
            message
        )

        return False

    return True


# =========================================================
# البحث عن الأغنية
# =========================================================

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

        if not info:
            return None

        entries = info.get("entries")

        if not entries:
            return None

        song = entries[0]

        return {
            "title": song.get(
                "title",
                "أغنية"
            ),

            "url": (
                song.get("webpage_url")
                or song.get("url")
            ),

            "duration": song.get(
                "duration"
            )
        }

    except Exception as e:

        print(
            "SEARCH ERROR:",
            repr(e)
        )

        return None


# =========================================================
# الحصول على الصوت
# =========================================================

async def get_audio(url):

    options = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
    }

    try:

        with yt_dlp.YoutubeDL(options) as ydl:

            info = await asyncio.to_thread(
                ydl.extract_info,
                url,
                False
            )

        if not info:
            return None

        return info.get("url")

    except Exception as e:

        print(
            "AUDIO ERROR:",
            repr(e)
        )

        return None


# =========================================================
# مدة الأغنية
# =========================================================

def format_duration(seconds):

    if not seconds:
        return "غير معروف"

    try:

        seconds = int(seconds)

        minutes = seconds // 60
        seconds = seconds % 60

        return f"{minutes:02d}:{seconds:02d}"

    except Exception:

        return "غير معروف"


# =========================================================
# رسالة الأغنية
# =========================================================

async def send_play_message(
    chat_id,
    song,
    user_name
):

    duration = format_duration(
        song.get("duration")
    )

    caption = (
        "🎵 <b>مريومه الدلوعه</b>\n\n"
        "❤️ <b>STARTED STREAMING</b>\n\n"
        f"▶️ <b>العنوان:</b> "
        f"{song['title']}\n"
        f"⏱ <b>المدة:</b> "
        f"{duration}\n\n"
        f"👤 <b>Requested by:</b> "
        f"{user_name}"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⏸ إيقاف مؤقت",
                    callback_data="pause"
                ),
                InlineKeyboardButton(
                    "▶️ استكمال",
                    callback_data="resume"
                )
            ],
            [
                InlineKeyboardButton(
                    "⏭ تخطي",
                    callback_data="skip"
                ),
                InlineKeyboardButton(
                    "⏹ إيقاف",
                    callback_data="stop"
                )
            ],
            [
                InlineKeyboardButton(
                    "📋 القائمة",
                    callback_data="queue"
                )
            ]
        ]
    )

    try:

        await bot.send_photo(
            chat_id,
            photo=PHOTO_PATH,
            caption=caption,
            reply_markup=keyboard
        )

    except Exception as e:

        print(
            "PHOTO ERROR:",
            repr(e)
        )

        await bot.send_message(
            chat_id,
            caption,
            reply_markup=keyboard
        )


# =========================================================
# تشغيل الأغنية
# =========================================================

async def play_song(
    chat_id,
    song,
    user_name="مريومه"
):

    try:

        print(
            f"PLAYING: {song['title']}"
        )

        audio_url = await get_audio(
            song["url"]
        )

        if not audio_url:

            await bot.send_message(
                chat_id,
                "❌ مش قادر أوصل للصوت."
            )

            return False

        await calls.play(
            chat_id,
            MediaStream(
                audio_url,
                video_flags=MediaStream.Flags.IGNORE
            ),
            GroupCallConfig(
                auto_start=True
            )
        )

        playing[chat_id] = song
        paused[chat_id] = False

        await send_play_message(
            chat_id,
            song,
            user_name
        )

        print(
            f"PLAY SUCCESS: {song['title']}"
        )

        return True

    except Exception as e:

        print(
            "PLAY ERROR:",
            repr(e)
        )

        await bot.send_message(
            chat_id,
            "❌ حصل خطأ أثناء تشغيل الأغنية.\n"
            "راجع Logs في Railway."
        )

        return False


# =========================================================
# البحث والتشغيل
# =========================================================

async def search_and_play(
    message,
    song_name
):

    chat_id = message.chat.id

    user_name = (
        message.from_user.first_name
        if message.from_user
        else "مستخدم"
    )

    await message.reply_text(
        "🔎 بدور على الأغنية..."
    )

    song = await search_song(
        song_name
    )

    if not song:

        await message.reply_text(
            "❌ ملقتش الأغنية دي."
        )

        return

    # لو فيه أغنية شغالة
    if chat_id in playing:

        if chat_id not in queues:
            queues[chat_id] = []

        queues[chat_id].append(
            song
        )

        await message.reply_text(
            "✅ اتضافت للقائمة:\n"
            f"🎵 {song['title']}"
        )

        return

    await play_song(
        chat_id,
        song,
        user_name
    )


# =========================================================
# /start
# =========================================================

@bot.on_message(
    filters.private &
    filters.command("start")
)
async def start_command(
    client,
    message
):

    if not await require_access(
        message
    ):
        return

    await message.reply_text(
        "🎵 <b>مريومه الدلوعه</b>\n\n"
        "✅ تم التحقق بنجاح.\n\n"
        "استخدم البوت داخل الجروب:\n\n"
        "🎵 تشغيل\n"
        "⏭️ تخطي\n"
        "📋 القائمة\n"
        "⏹️ وقف"
    )


# =========================================================
# أي رسالة خاصة قبل التحقق
# =========================================================

@bot.on_message(
    filters.private &
    filters.text
)
async def private_handler(
    client,
    message
):

    if message.text.startswith("/start"):
        return

    if not await require_access(
        message
    ):
        return

    await message.reply_text(
        "✅ تم التحقق.\n"
        "استخدم البوت داخل الجروب."
    )


# =========================================================
# أوامر الجروبات
# =========================================================

@bot.on_message(
    filters.group &
    filters.text
)
async def music_handler(
    client,
    message
):

    # تحقق قبل استخدام البوت
    if not await require_access(
        message
    ):
        return

    chat_id = message.chat.id

    text = message.text.strip()

    # تشغيل فقط
    if text == "تشغيل":

        waiting_for_song[chat_id] = True

        await message.reply_text(
            "🎵 قول اسم الأغنية"
        )

        return

    # تشغيل + اسم الأغنية
    if text.startswith("تشغيل "):

        song_name = (
            text[len("تشغيل "):]
            .strip()
        )

        if song_name:

            await search_and_play(
                message,
                song_name
            )

        else:

            waiting_for_song[chat_id] = True

            await message.reply_text(
                "🎵 قول اسم الأغنية"
            )

        return

    # انتظار اسم الأغنية
    if waiting_for_song.get(
        chat_id
    ):

        waiting_for_song[chat_id] = False

        await search_and_play(
            message,
            text
        )


# =========================================================
# تخطي
# =========================================================

async def do_skip(chat_id):

    if chat_id not in playing:
        return False

    playing.pop(
        chat_id,
        None
    )

    paused.pop(
        chat_id,
        None
    )

    try:

        await calls.leave_call(
            chat_id
        )

    except Exception as e:

        print(
            "LEAVE ERROR:",
            repr(e)
        )

    if queues.get(chat_id):

        next_song = queues[
            chat_id
        ].pop(0)

        await play_song(
            chat_id,
            next_song,
            "القائمة"
        )

        return True

    return True


@bot.on_message(
    filters.group &
    filters.regex(r"^تخطي$")
)
async def skip_command(
    client,
    message
):

    if not await require_access(
        message
    ):
        return

    chat_id = message.chat.id

    if chat_id not in playing:

        await message.reply_text(
            "❌ مفيش أغنية شغالة."
        )

        return

    await message.reply_text(
        "⏭️ تم التخطي."
    )

    await do_skip(
        chat_id
    )


# =========================================================
# إيقاف
# =========================================================

async def do_stop(chat_id):

    try:

        await calls.leave_call(
            chat_id
        )

    except Exception as e:

        print(
            "STOP ERROR:",
            repr(e)
        )

    playing.pop(
        chat_id,
        None
    )

    queues[chat_id] = []

    waiting_for_song[chat_id] = False

    paused.pop(
        chat_id,
        None
    )


@bot.on_message(
    filters.group &
    filters.regex(r"^(وقف|إيقاف)$")
)
async def stop_command(
    client,
    message
):

    if not await require_access(
        message
    ):
        return

    await do_stop(
        message.chat.id
    )

    await message.reply_text(
        "⏹️ تم إيقاف الأغاني."
    )


# =========================================================
# القائمة
# =========================================================

async def queue_text(chat_id):

    queue = queues.get(
        chat_id,
        []
    )

    if not queue:

        return "📋 القائمة فاضية."

    text = (
        "📋 <b>قائمة الأغاني:</b>\n\n"
    )

    for i, song in enumerate(
        queue,
        1
    ):

        text += (
            f"{i}. 🎵 "
            f"{song['title']}\n"
        )

    return text


@bot.on_message(
    filters.group &
    filters.regex(r"^القائمة$")
)
async def queue_command(
    client,
    message
):

    if not await require_access(
        message
    ):
        return

    await message.reply_text(
        await queue_text(
            message.chat.id
        )
    )


# =========================================================
# الأزرار
# =========================================================

@bot.on_callback_query()
async def button_handler(
    client,
    query
):

    data = query.data

    # -------------------------
    # تحقق
    # -------------------------

    if data == "check_join":

        user_id = query.from_user.id

        joined = await is_user_joined(
            user_id
        )

        if joined:

            await query.answer(
                "✅ تم التحقق بنجاح!"
            )

            try:

                await query.message.edit_text(
                    "✅ <b>تم التحقق بنجاح</b>\n\n"
                    "🎵 دلوقتي تقدر تستخدم البوت "
                    "داخل الجروب."
                )

            except Exception:
                pass

        else:

            await query.answer(
                "❌ لسه مش منضم للمجموعة.",
                show_alert=True
            )

        return


    # -------------------------
    # تحقق قبل أزرار الموسيقى
    # -------------------------

    joined = await is_user_joined(
        query.from_user.id
    )

    if not joined:

        await query.answer(
            "❌ لازم تنضم للمجموعة أولًا.",
            show_alert=True
        )

        return


    chat_id = query.message.chat.id


    # -------------------------
    # Pause
    # -------------------------

    if data == "pause":

        if chat_id not in playing:

            await query.answer(
                "❌ مفيش أغنية شغالة.",
                show_alert=True
            )

            return

        try:

            await calls.pause_stream(
                chat_id
            )

            paused[chat_id] = True

            await query.answer(
                "⏸ تم الإيقاف المؤقت"
            )

        except Exception as e:

            print(
                "PAUSE ERROR:",
                repr(e)
            )

            await query.answer(
                "❌ مقدرتش أوقف الأغنية.",
                show_alert=True
            )

        return


    # -------------------------
    # Resume
    # -------------------------

    if data == "resume":

        if chat_id not in playing:

            await query.answer(
                "❌ مفيش أغنية.",
                show_alert=True
            )

            return

        try:

            await calls.resume_stream(
                chat_id
            )

            paused[chat_id] = False

            await query.answer(
                "▶️ تم استكمال الأغنية"
            )

        except Exception as e:

            print(
                "RESUME ERROR:",
                repr(e)
            )

            await query.answer(
                "❌ مقدرتش أكمل الأغنية.",
                show_alert=True
            )

        return


    # -------------------------
    # Skip
    # -------------------------

    if data == "skip":

        if chat_id not in playing:

            await query.answer(
                "❌ مفيش أغنية شغالة.",
                show_alert=True
            )

            return

        await query.answer(
            "⏭️ تم التخطي"
        )

        await do_skip(
            chat_id
        )

        return


    # -------------------------
    # Stop
    # -------------------------

    if data == "stop":

        await do_stop(
            chat_id
        )

        await query.answer(
            "⏹️ تم الإيقاف"
        )

        return


    # -------------------------
    # Queue
    # -------------------------

    if data == "queue":

        await query.answer()

        await bot.send_message(
            chat_id,
            await queue_text(
                chat_id
            )
        )

        return


# =========================================================
# تشغيل
# =========================================================

print(
    "🎵 Mariam Music Bot Started..."
)

calls.start()

bot.run()

بعد استبدال "bot.py" بهذا الكود، اعمل Commit changes وانتظر Railway يعمل Deploy.

مهم جدًا قبل الاختبار: أضف البوت نفسه إلى "@mariamqueennuriii" ويفضل تعمله Admin؛ لأن التحقق من أعضاء المجموعة يعتمد على "getChatMember".

بعدها جرّب "/start" من الخاص. المفروض تظهر لك أزرار «أضفني لمجموعتك» + «انضم للمجموعة» + «تحقق».
