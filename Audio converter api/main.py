# main.py
import os
import uuid
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pytube import YouTube
from pathlib import Path
import asyncio
import subprocess

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000"),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Temporary storage (Render has ephemeral storage)
TMP_DIR = Path("tmp")
TMP_DIR.mkdir(exist_ok=True)

class ConversionRequest(BaseModel):
    youtube_url: str
    format: str  # 'mp3' or 'wav'

# In-memory task store (consider Redis for production)
tasks = {}

async def convert_audio(task_id: str, url: str, format: str):
    try:
        yt = YouTube(url)
        audio = yt.streams.filter(only_audio=True).first()
        
        # Download
        download_path = audio.download(output_path=TMP_DIR)
        
        # Convert
        output_path = TMP_DIR / f"{task_id}.{format}"
        subprocess.call([
            'ffmpeg', '-i', download_path,
            '-acodec', 'libmp3lame' if format == 'mp3' else 'pcm_s16le',
            output_path
        ])
        
        # Cleanup
        os.remove(download_path)
        tasks[task_id] = {"status": "completed", "path": output_path}
        
    except Exception as e:
        tasks[task_id] = {"status": "failed", "error": str(e)}

@app.post("/convert")
async def create_conversion(request: ConversionRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    tasks[task_id] = {"status": "processing"}
    
    background_tasks.add_task(convert_audio, task_id, request.youtube_url, request.format)
    
    return {"task_id": task_id}

@app.get("/status/{task_id}")
def get_status(task_id: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": task["status"]}

@app.get("/download/{task_id}")
def download_file(task_id: str):
    task = tasks.get(task_id)
    if not task or task["status"] != "completed":
        raise HTTPException(status_code=404, detail="File not ready")
    
    return FileResponse(
        task["path"],
        media_type='application/octet-stream',
        filename=f"converted_{task_id}.{task['path'].split('.')[-1]}"
    )