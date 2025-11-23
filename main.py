import os
import asyncio
import uuid
import tempfile
from pyrogram import Client, filters
from pyrogram.types import Message
from dotenv import load_dotenv

from utils import get_user_settings, set_user_settings
from ffmpeg_helper import add_watermark_video
from pdf_helper import add_watermark_to_pdf

load_dotenv()

# === ENV VARIABLES ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH")

if not BOT_TOKEN or not API_ID or not API_HASH:
    raise RuntimeError("BOT_TOKEN, API_ID aur API_HASH Heroku config vars mein set kar bhosdike!")

app = Client("movable-watermark-bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

def safe_tmpfile(suffix=""):
    return os.path.join(tempfile.gettempdir(), f"{uuid.uuid4().hex}{suffix}")

# =================== COMMANDS ===================

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
    if not m.from_user: return
    args = m.text.split(" ", 1)
    if len(args) < 2 or not args[1].strip():
        return await m.reply_text("Usage: /settext Your watermark text")
    s = get_user_settings(m.from_user.id)
    s["text"] = args[1].strip()
    set_user_settings(m.from_user.id, s)
    await m.reply_text(f"Watermark text set → {s['text']}")

@app.on_message(filters.command("setcolor") & filters.private)
async def set_color(c: Client, m: Message):
    if not m.from_user: return
    args = m.text.split(" ", 1)
    if len(args) < 2 or args[1].strip().lower() not in ("white", "black"):
        return await m.reply_text("Usage: /setcolor white OR black")
    s = get_user_settings(m.from_user.id)
    s["color"] = args[1].strip().lower()
    set_user_settings(m.from_user.id, s)
    await m.reply_text(f"Color → {s['color']}")

@app.on_message(filters.command("setsize") & filters.private)
async def set_size(c: Client, m: Message):
    if not m.from_user: return
    try:
        size = int(m.text.split()[1])
        if not 10 <= size <= 200: raise ValueError
    except Exception:
        return await m.reply_text("Size 10-200 ke beech mein daal")
    s = get_user_settings(m.from_user.id)
    s["size"] = size
    set_user_settings(m.from_user.id, s)
    await m.reply_text(f"Font size → {size}")

@app.on_message(filters.command("setdirection") & filters.private)
async def set_direction(c: Client, m: Message):
    if not m.from_user: return
    val = m.text.split(maxsplit=1)[1].lower() if len(m.text.split()) > 1 else ""
    if val not in ("static", "left-right", "top-bottom"):
        return await m.reply_text("Valid: static | left-right | top-bottom")
    s = get_user_settings(m.from_user.id)
    s["direction"] = val
    set_user_settings(m.from_user.id, s)
    await m.reply_text(f"Direction → {val}")

@app.on_message(filters.command("setcrf") & filters.private)
async def set_crf(c: Client, m: Message):
    if not m.from_user: return
    try:
        crf = int(m.text.split()[1])
        if not 0 <= crf <= 51: raise ValueError
    except Exception:
        return await m.reply_text("CRF 0-51 ke beech mein daal")
    s = get_user_settings(m.from_user.id)
    s["crf"] = crf
    set_user_settings(m.from_user.id, s)
    await m.reply_text(f"CRF → {crf}")

@app.on_message(filters.command("setres") & filters.private)
async def set_res(c: Client, m: Message):
    if not m.from_user: return
    val = m.text.split(maxsplit=1)[1].lower() if len(m.text.split()) > 1 else ""
    if val not in ("original", "1080", "720", "480"):
        return await m.reply_text("Valid: original | 1080 | 720 | 480")
    s = get_user_settings(m.from_user.id)
    s["resolution"] = val
    set_user_settings(m.from_user.id, s)
    await m.reply_text(f"Resolution → {val}")

@app.on_message(filters.command("togglecompress") & filters.private)
async def toggle_compress(c: Client, m: Message):
    if not m.from_user: return
    val = m.text.split(maxsplit=1)[1].lower() if len(m.text.split()) > 1 else ""
    if val not in ("on", "off"):
        return await m.reply_text("Usage: /togglecompress on OR off")
    s = get_user_settings(m.from_user.id)
    s["compress"] = (val == "on")
    set_user_settings(m.from_user.id, s)
    await m.reply_text(f"Compression → {'ON' if s['compress'] else 'OFF'}")

@app.on_message(filters.command("showsettings") & filters.private)
async def show_settings(c: Client, m: Message):
    if not m.from_user: return
    s = get_user_settings(m.from_user.id)
    txt = "Your Settings:\n\n" + "\n".join(f"• {k}: {v}" for k, v in s.items())
    await m.reply_text(txt)

# =================== HANDLERS ===================

@app.on_message(filters.document & filters.private)
async def handle_document(c: Client, m: Message):
    if not m.document or m.document.mime_type != "application/pdf":
        return await m.reply_text("Sirf PDF bhejo bhai")
    s = get_user_settings(m.from_user.id)
    msg = await m.reply_text("PDF download ho raha...")
    in_path = safe_tmpfile(".pdf")
    out_path = safe_tmpfile(".pdf")
    try:
        await m.download(file_name=in_path)
        await msg.edit("Watermark laga raha hu...")
        add_watermark_to_pdf(in_path, out_path, s["text"], fontsize=s["size"], color=s["color"])
        await msg.edit("Upload kar raha hu...")
        await c.send_document(m.chat.id, out_path, caption="Watermarked PDF")
        await msg.delete()
    except Exception as e:
        await msg.edit(f"Error: {e}")
    finally:
        for p in (in_path, out_path):
            try: os.remove(p)
            except: pass

@app.on_message(filters.video & filters.private)
async def handle_video(c: Client, m: Message):
    if not m.from_user: return
    s = get_user_settings(m.from_user.id)
    msg = await m.reply_text("Video download kar raha hu...")
    in_path = safe_tmpfile(".mp4")
    out_path = safe_tmpfile(".mp4")
    try:
        await m.download(file_name=in_path)
        await msg.edit("Moving watermark laga raha hu + compress kar raha hu...")
        await add_watermark_video(
            in_path, out_path,
            text=s["text"],
            color=s.get("color", "white"),
            fontsize=s.get("size", 36),
            direction=s.get("direction", "static"),
            crf=s.get("crf", 23),
            resolution=s.get("resolution", "original")
        )
        await msg.edit("Final video upload ho raha...")
        await c.send_video(m.chat.id, out_path, caption="Done! Moving watermark laga diya")
        await msg.delete()
    except Exception as e:
        await msg.edit(f"Error: {e}")
    finally:
        for p in (in_path, out_path):
            try: os.remove(p)
            except: pass

# =================== MAIN (NO IDLE, NO CRASH) ===================

async def main():
    print("Bot shuru ho raha hai...")
    await app.start()
    print("Bot ONLINE ho gaya! Ab video/PDF daal ke maze le")
    await asyncio.Event().wait()   # Ye bot ko forever zinda rakhega

if __name__ == "__main__":
    asyncio.run(main())
