import os

import yt_dlp
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse

app = FastAPI()


# Get the default system Downloads folder
DOWNLOAD_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


def download_audio(url: str, output_format: str):
    """Download audio using yt-dlp and convert it."""
    output_path = os.path.join(DOWNLOAD_FOLDER, "audio.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": output_format,
                "preferredquality": "192",
            }
        ],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return os.path.join(DOWNLOAD_FOLDER, f"audio.{output_format}")


@app.get("/download_audio/")
async def download_youtube_audio(
    url: str = Query(..., title="YouTube URL"),
    format: str = Query("mp3", regex="^(mp3|wav)$"),
):
    file_path = download_audio(url, format)
    return FileResponse(
        file_path,
        filename=os.path.basename(file_path),
        media_type="audio/" + format,
    )
