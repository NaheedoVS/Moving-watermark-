import time
import pytz
from datetime import datetime

# Force system time sync workaround
now = datetime.now(pytz.utc)
ts = int(now.timestamp())
time.time = lambda: ts

import os
import asyncio
import uuid
import tempfile
from pyrogram import Client, filters
from pyrogram.types import Message
from dotenv import load_dotenv
import aiofiles
from utils import get_user_settings, set_user_settings
from ffmpeg_helper import add_watermark_video
from pdf_helper import add_watermark_to_pdf

load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH")
OWNER_ID = os.environ.get("OWNER_ID")

if not BOT_TOKEN or not API_ID or not API_HASH:
    raise RuntimeError("BOT_TOKEN, API_ID and API_HASH must be set as environment variables")

app = Client("movable-watermark-bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

def safe_tmpfile(suffix=""):
    return os.path.join(tempfile.gettempdir(), f"{uuid.uuid4().hex}{suffix}")

@app.on_message(filters.command("start") & filters.private)
async def start(c: Client, m: Message):
    await m.reply_text(
        "Hello! I will watermark videos and PDFs.\n\n"
        "Commands:\n"
        "/settext <text>\n"
        "/setcolor <black|white>\n"
        "/setsize <10-200>\n"
        "/setdirection <static|left-right|top-bottom>\n"
        "/setcrf <number> (0-51)\n"
        "/setres <original|1080|720|480>\n"
        "/togglecompress <on|off>\n"
        "/showsettings\n\n"
        "Send a video or PDF and I'll process it with your settings."
    )

@app.on_message(filters.command("settext") & filters.private)
async def set_text(c: Client, m: Message):
    user = m.from_user
    if not user:
        return
    args = m.text.split(" ", 1)
    if len(args) < 2 or not args[1].strip():
        await m.reply_text("Usage: /settext Your watermark text")
        return
    s = get_user_settings(user.id)
    s["text"] = args[1].strip()
    set_user_settings(user.id, s)
    await m.reply_text(f"Watermark text set to: {s['text']}")

@app.on_message(filters.command("setcolor") & filters.private)
async def set_color(c: Client, m: Message):
    user = m.from_user
    if not user:
        return
    args = m.text.split(" ", 1)
    if len(args) < 2 or args[1].strip().lower() not in ("white", "black"):
        await m.reply_text("Usage: /setcolor white OR /setcolor black")
        return
    s = get_user_settings(user.id)
    s["color"] = args[1].strip().lower()
    set_user_settings(user.id, s)
    await m.reply_text(f"Watermark color set to: {s['color']}")

@app.on_message(filters.command("setsize") & filters.private)
async def set_size(c: Client, m: Message):
    user = m.from_user
    if not user:
        return
    args = m.text.split(" ", 1)
    try:
        size = int(args[1].strip())
        if size < 10 or size > 200:
            raise ValueError()
    except Exception:
        await m.reply_text("Size must be a number between 10 and 200")
        return
    s = get_user_settings(user.id)
    s["size"] = size
    set_user_settings(user.id, s)
    await m.reply_text(f"Watermark font size set to: {size}")

@app.on_message(filters.command("setdirection") & filters.private)
async def set_direction(c: Client, m: Message):
    user = m.from_user
    if not user:
        return
    args = m.text.split(" ", 1)
    val = args[1].strip().lower() if len(args) > 1 else ""
    if val not in ("static", "left-right", "top-bottom"):
        await m.reply_text("Usage: /setdirection static|left-right|top-bottom")
        return
    s = get_user_settings(user.id)
    s["direction"] = val
    set_user_settings(user.id, s)
    await m.reply_text(f"Movement direction set to: {val}")

@app.on_message(filters.command("setcrf") & filters.private)
async def set_crf(c: Client, m: Message):
    user = m.from_user
    if not user:
        return
    args = m.text.split(" ", 1)
    try:
        crf = int(args[1].strip())
        if crf < 0 or crf > 51:
            raise ValueError()
    except Exception:
        await m.reply_text("CRF must be a number between 0 and 51 (recommended 18-28)")
        return
    s = get_user_settings(user.id)
    s["crf"] = crf
    set_user_settings(user.id, s)
    await m.reply_text(f"CRF set to: {crf}")

@app.on_message(filters.command("setres") & filters.private)
async def set_res(c: Client, m: Message):
    user = m.from_user
    if not user:
        return
    args = m.text.split(" ", 1)
    val = args[1].strip().lower() if len(args) > 1 else ""
    if val not in ("original", "1080", "720", "480"):
        await m.reply_text("Usage: /setres original|1080|720|480")
        return
    s = get_user_settings(user.id)
    s["resolution"] = val
    set_user_settings(user.id, s)
    await m.reply_text(f"Resolution set to: {val}")

@app.on_message(filters.command("togglecompress") & filters.private)
async def toggle_compress(c: Client, m: Message):
    user = m.from_user
    if not user:
        return
    args = m.text.split(" ", 1)
    val = args[1].strip().lower() if len(args) > 1 else ""
    if val not in ("on", "off"):
        await m.reply_text("Usage: /togglecompress on|off")
        return
    s = get_user_settings(user.id)
    s["compress"] = (val == "on")
    set_user_settings(user.id, s)
    await m.reply_text(f"Compression set to: {s['compress']}")

@app.on_message(filters.command("showsettings") & filters.private)
async def show_settings(c: Client, m: Message):
    user = m.from_user
    if not user:
        return
    s = get_user_settings(user.id)
    await m.reply_text("Your settings:\n" + "\n".join(f"{k}: {v}" for k, v in s.items()))

@app.on_message(filters.document & filters.private)
async def handle_document(c: Client, m: Message):
    # Accept PDFs only
    if not m.document:
        return
    if m.document.mime_type != "application/pdf":
        await m.reply_text("Only PDF files are supported for documents.")
        return
    user = m.from_user
    s = get_user_settings(user.id)
    msg = await m.reply_text("Downloading PDF...")
    in_path = safe_tmpfile(".pdf")
    out_path = safe_tmpfile(".pdf")
    try:
        await m.download(file_name=in_path)
        await msg.edit("Applying watermark to PDF...")
        add_watermark_to_pdf(in_path, out_path, s["text"], fontsize=s["size"], color=s["color"])
        await msg.edit("Uploading watermarked PDF...")
        await c.send_document(chat_id=m.chat.id, document=out_path, caption="Watermarked PDF")
        await msg.delete()
    except Exception as e:
        await msg.edit(f"Error: {e}")
    finally:
        for p in (in_path, out_path):
            try:
                os.remove(p)
            except Exception:
                pass

@app.on_message(filters.video & filters.private)
async def handle_video(c: Client, m: Message):
    user = m.from_user
    if not user:
        return
    s = get_user_settings(user.id)
    msg = await m.reply_text("Downloading video...")
    in_path = safe_tmpfile(".mp4")
    intermediate = safe_tmpfile(".mp4")
    out_path = safe_tmpfile(".mp4")
    try:
        await m.download(file_name=in_path)
        await msg.edit("Processing video (watermark + compression)...")
        # If compression disabled, pass original resolution and crf but we still transcode to apply drawtext.
        crf = s.get("crf", 20)
        res = s.get("resolution", "original")
        await add_watermark_video(in_path, out_path, s["text"], color=s.get("color","white"), fontsize=s.get("size",36), direction=s.get("direction","static"), crf=crf, resolution=res)
        await msg.edit("Uploading processed video...")
        await c.send_video(chat_id=m.chat.id, video=out_path, caption="Watermarked video")
        await msg.delete()
    except Exception as e:
        await msg.edit(f"Error: {e}")
    finally:
        for p in (in_path, intermediate, out_path):
            try:
                os.remove(p)
            except Exception:
                pass

if __name__ == '__main__':
    print("Starting bot...")
    app.run()
