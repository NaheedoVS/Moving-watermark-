import asyncio
import shlex
import os
import math

async def run_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    out, err = await proc.communicate()
    return proc.returncode, out, err

def _fontfile():
    # Common DejaVu font path on many Linux systems and buildpacks
    p = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if os.path.exists(p):
        return p
    return None

def _escape_text_for_drawtext(text: str) -> str:
    # Escape single quotes and backslashes for ffmpeg drawtext literal
    return text.replace("\\", "\\\\").replace("'", r"\'")

async def add_watermark_video(input_path: str, output_path: str, text: str, color: str = 'white', fontsize: int = 36, direction: str = 'static', crf: int = 20, resolution: str = 'original'):
    """
    Add centered (and optionally moving) text watermark to video using ffmpeg.
    direction: 'static' | 'left-right' | 'top-bottom'
    resolution: 'original' | '1080' | '720' | '480'
    """
    fontfile = _fontfile()
    fontfile_param = f":fontfile={fontfile}" if fontfile else ""
    safe_text = _escape_text_for_drawtext(text)

    # Movement expressions. Use sine for smooth oscillation. Period = 5 sec.
    # Horizontal movement amplitude is w/3, vertical amplitude is h/6 (smaller).
    if direction == 'left-right':
        x_expr = "(w-text_w)/2 + (w/3)*sin(2*PI*t/5)"
        y_expr = "(h-text_h)/2"
    elif direction == 'top-bottom':
        x_expr = "(w-text_w)/2"
        y_expr = "(h-text_h)/2 + (h/6)*sin(2*PI*t/5)"
    else:
        x_expr = "(w-text_w)/2"
        y_expr = "(h-text_h)/2"

    drawtext = f"drawtext=text='{safe_text}':x={x_expr}:y={y_expr}:fontcolor={color}:fontsize={fontsize}:box=0{fontfile_param}"

    # Build filter chain
    vf = drawtext

    # Resolution handling (scale). Keep aspect ratio, set max height based on choice.
    scale_filter = ""
    if resolution != 'original':
        if resolution == '1080':
            scale_filter = "scale='min(iw,1920)':'min(ih,1080)':force_original_aspect_ratio=decrease"
        elif resolution == '720':
            scale_filter = "scale='min(iw,1280)':'min(ih,720)':force_original_aspect_ratio=decrease"
        elif resolution == '480':
            scale_filter = "scale='min(iw,854)':'min(ih,480)':force_original_aspect_ratio=decrease"

    if scale_filter:
        vf = f"{scale_filter},{vf}"

    # Build final ffmpeg command. Transcode video to h264 (libx264) using CRF settings, copy audio.
    cmd = f"ffmpeg -y -i {shlex.quote(input_path)} -vf \"{vf}\" -c:v libx264 -preset veryfast -crf {crf} -c:a aac -b:a 128k {shlex.quote(output_path)}"
    returncode, out, err = await run_cmd(cmd)
    if returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {err.decode(errors='ignore')}")
    return output_path
