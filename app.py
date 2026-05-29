from flask import Flask, request, jsonify
import os
import uuid
import subprocess
import sys

app = Flask(__name__)
DOWNLOAD_DIR = "/tmp/videos"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def download_tiktok(url, output_path):
    # Use yt-dlp with cookies and no impersonation
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--no-warnings",
        "--format", "best[ext=mp4]/best",
        "--output", output_path,
        "--add-header", "User-Agent:Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "--add-header", "Referer:https://www.tiktok.com/",
        "--no-check-certificate",
        url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(result.stderr or result.stdout)
    return "TikTok video"

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

    video_path = os.path.join(DOWNLOAD_DIR, f"{uuid.uuid4()}.mp4")

    try:
        download_tiktok(link, video_path)
    except Exception as e:
        return jsonify({"error": f"download failed: {str(e)}"}), 500

    # find actual downloaded file
    actual = None
    for f in os.listdir(DOWNLOAD_DIR):
        full = os.path.join(DOWNLOAD_DIR, f)
        if os.path.isfile(full) and f.endswith((".mp4", ".webm", ".mkv")):
            actual = full
            break

    if not actual:
        return jsonify({"error": "video file not found after download"}), 500

    try:
        post_reel(actual, caption or "via TikTok", username, password)
    except Exception as e:
        return jsonify({"error": f"upload failed: {str(e)}"}), 500
    finally:
        if actual and os.path.exists(actual):
            os.remove(actual)

    return jsonify({"success": True, "message": "posted to reels!"})

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "running"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
