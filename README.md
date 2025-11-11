# Telegram Movable Watermark Bot

A Telegram bot (Pyrogram) that applies a movable centered text watermark to videos (left-right or top-bottom), supports color and font-size controls, PDF watermarking (applies to every page), and optional pre-upload video compression (resolution & CRF). Designed to be easily deployable on Heroku.

## Features
- Per-user settings: watermark text, color (black/white), font size, movement direction.
- Movement modes: `static`, `left-right`, `top-bottom`.
- Video compression before upload: choose resolution (`original`, `1080`, `720`, `480`) and CRF.
- PDF watermarking: watermark applied to every page, centered.
- Simple JSON persistence (`user_settings.json`).
- Deployable to Heroku (Procfile and notes included).

## Deploy to Heroku (quick)
1. Create a Heroku app.
2. Add config vars: BOT_TOKEN, API_ID, API_HASH, OWNER_ID (optional).
3. If ffmpeg isn't present on your dyno, add this buildpack before the Python buildpack:
   `https://github.com/jonathanong/heroku-buildpack-ffmpeg-latest`
4. Push this repo to Heroku or connect via GitHub.
5. Ensure Procfile contains: `worker: python main.py`

## Commands
- `/start` - show help
- `/settext <text>` - set watermark text
- `/setcolor <black|white>` - choose text color
- `/setsize <number>` - font size (10–200)
- `/setdirection <static|left-right|top-bottom>` - movement mode
- `/setcrf <number>` - set CRF for video transcoding (0-51)
- `/setres <original|1080|720|480>` - set output resolution
- `/togglecompress <on|off>` - enable/disable compression before upload
- `/showsettings` - display current settings
- Send a video or a PDF - bot replies with processed file

