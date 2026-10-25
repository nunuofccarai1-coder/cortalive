import os, re, shutil, subprocess, tempfile, uuid import os, re, shutil, subprocess, tempfile, uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl, Field
import yt_dlp

app = FastAPI(title="CortaLive API", version="0.1.0")
# In production, replace '*' with your deployed frontend domain.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["*"])
ROOT = Path(os.getenv("CORTALIVE_WORKDIR", "/tmp/cortalive"))
ROOT.mkdir(parents=True, exist_ok=True)

class ClipRequest(BaseModel):
    url: HttpUrl
    count: int = Field(default=3, ge=1, le=8)
    seconds: int = Field(default=30, ge=10, le=90)


def safe_remove(path: Path):
    try:
        if path.is_dir(): shutil.rmtree(path, ignore_errors=True)
        elif path.exists(): path.unlink()
    except Exception:
        pass

@app.get("/health")
def health():
    return {"ok": True, "service": "CortaLive API"}

@app.post("/api/clips")
def make_clips(req: ClipRequest, background_tasks: BackgroundTasks):
    raw_url = str(req.url)
    host = re.sub(r"^www\.", "", __import__('urllib.parse').parse.urlparse(raw_url).hostname or "").lower()
    if host not in {"youtube.com", "m.youtube.com", "youtu.be", "youtube-nocookie.com", "www.youtube.com"}:
        raise HTTPException(400, "Envie um link válido do YouTube.")
    if not shutil.which("ffmpeg"):
        raise HTTPException(503, "O servidor está sem FFmpeg instalado.")

    job = ROOT / str(uuid.uuid4())
    job.mkdir(parents=True, exist_ok=True)
    source = job / "source.%(ext)s"
    try:
        opts = {
            "format": "best[ext=mp4]/best",
            "outtmpl": str(source),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 25,
            "retries": 1,
            "max_filesize": 800 * 1024 * 1024,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(raw_url, download=True)
            downloaded = Path(ydl.prepare_filename(info))
        if not downloaded.exists():
            candidates = list(job.glob("source.*"))
            if not candidates: raise RuntimeError("O download não produziu um arquivo de vídeo.")
            downloaded = candidates[0]
        duration = float(info.get("duration") or 0)
        if duration < 3:
            raise ValueError("O vídeo é curto demais ou não tem duração disponível.")
        clip_len = min(req.seconds, max(3, int(duration) - 1))
        max_start = max(0, duration - clip_len)
        starts = [max_start / 2] if req.count == 1 else [max_start * i / (req.count - 1) for i in range(req.count)]
        results = []
        for i, start in enumerate(starts, 1):
            output = job / f"clip-{i}.mp4"
            command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(start), "-i", str(downloaded), "-t", str(clip_len), "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", "-movflags", "+faststart", str(output)]
            proc = subprocess.run(command, capture_output=True, text=True, timeout=180)
            if proc.returncode != 0 or not output.exists() or output.stat().st_size == 0:
                raise RuntimeError("FFmpeg não conseguiu gerar um dos clipes.")
            results.append({"name": output.name, "start": round(start, 1), "end": round(min(duration, start + clip_len), 1), "download_url": f"/api/jobs/{job.name}/{output.name}"})
        # Clean up source after cuts; clip files remain available temporarily.
        safe_remove(downloaded)
        background_tasks.add_task(cleanup_job_later, job, 3600)
        return {"title": info.get("title", "Vídeo"), "duration": duration, "ai_analysis": False, "note": "Estes são cortes distribuídos ao longo do vídeo, não escolhidos por IA.", "clips": results}
    except HTTPException:
        safe_remove(job); raise
    except Exception as exc:
        safe_remove(job)
        message = str(exc)
        if "Private video" in message or "private" in message.lower():
            message = "O vídeo é privado ou exige autenticação. Este servidor não acessa conteúdo privado."
        elif "Sign in" in message or "bot" in message.lower():
            message = "O YouTube bloqueou a consulta neste momento. Tente outro vídeo público mais tarde."
        elif "Unsupported URL" in message:
            message = "Esse link não é compatível. Use um vídeo público do YouTube."
        raise HTTPException(502, message[:350])

async def cleanup_job_later(path: Path, seconds: int):
    # Best-effort cleanup; a production deployment should use a proper task queue.
    import asyncio
    await asyncio.sleep(seconds)
    safe_remove(path)

@app.get("/api/jobs/{job_id}/{filename}")
def download_clip(job_id: str, filename: str):
    if not re.fullmatch(r"[a-f0-9-]{36}", job_id) or not re.fullmatch(r"clip-[1-8]\.mp4", filename):
        raise HTTPException(404, "Arquivo não encontrado.")
    path = ROOT / job_id / filename
    if not path.is_file(): raise HTTPException(404, "O clipe expirou ou não foi encontrado.")
    return FileResponse(path, media_type="video/mp4", filename=filename)
