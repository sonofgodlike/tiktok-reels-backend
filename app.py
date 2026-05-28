from flask import Flask, request, jsonify
import yt_dlp
import os
import uuid
import threading

app = Flask(__name__)
DOWNLOAD_DIR = "/tmp/videos"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def download_tiktok(url, output_path):
    ydl_opts = {
        'outtmpl': output_path,
        'format': 'best[ext=mp4]/best',
        'quiet': True,
        'http_headers': {'User-Agent': 'Mozilla/5.0'}
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return info.get('title', 'TikTok video')

def post_reel(video_path, caption, username, password):
    import shutil
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_path
        os.environ["FFMPEG_BINARY"] = ffmpeg_path
    from instagrapi import Client
    cl = Client()
    cl.delay_range = [1, 3]
    cl.login(username, password)
    cl.clip_upload(video_path, caption)

@app.route("/post", methods=["POST"])
def post():
    data = request.json
    link     = data.get("link")
    username = data.get("username")
    password = data.get("password")
    caption  = data.get("caption", "")

    if not link or not username or not password:
        return jsonify({"error": "missing fields"}), 400

    video_id   = str(uuid.uuid4())
    video_base = os.path.join(DOWNLOAD_DIR, video_id)

    try:
        title = download_tiktok(link, video_base)
    except Exception as e:
        return jsonify({"error": f"download failed: {e}"}), 500

    video_path = None
    for f in os.listdir(DOWNLOAD_DIR):
        if f.startswith(video_id):
            video_path = os.path.join(DOWNLOAD_DIR, f)
            break

    if not video_path:
        return jsonify({"error": "video file not found after download"}), 500

    try:
        post_reel(video_path, caption or title, username, password)
    except Exception as e:
        return jsonify({"error": f"upload failed: {e}"}), 500
    finally:
        if video_path and os.path.exists(video_path):
            os.remove(video_path)

    return jsonify({"success": True, "message": "posted to reels!"})

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "running"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
