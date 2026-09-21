import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())

import os
import yt_dlp

from pyrogram import Client, filters
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream


API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
SESSION_STRING = os.environ["SESSION_STRING"]


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

queues = {}
playing = {}
waiting_for_song = {}


async def search_song(name):
    options = {
        "quiet": True,
        "no_warnings": True,
        "default_search": "ytsearch1",
        "format": "bestaudio/best",
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        info = await asyncio.to_thread(
            ydl.extract_info,
            name,
            False
        )

    if "entries" in info:
        info = info["entries"][0]

    return {
        "title": info.get("title", "أغنية"),
        "url": info["webpage_url"],
    }


async def get_audio(url):
    options = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
    }

    with yt_dlp
