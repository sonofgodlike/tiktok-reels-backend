from flask import Flask, request, jsonify
import os
import uuid
import requests

app = Flask(__name__)
DOWNLOAD_DIR = "/tmp/videos"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def download_tiktok(url, output_path):
    # Use tikwm API to download without watermark
    api_url = "https://api.tikwm.com/api/"
    response = requests.post(api_url, data={"url": url, "hd": 1})
    data = response.json()

    if data.get("code") != 0:
        raise Exception(f"TikTok API error: {data.get('msg', 'unknown error')}")

    video_url = data["data"].get("hdplay") or data["data"].get("play")
    title = data["data"].get("title", "TikTok video")

    if not video_url:
        raise Exception("No video URL found")

    video_response = requests.get(video_url, stream=True, headers={
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'https://www.tiktok.com/'
    })
    video_response.raise_for_status()

    with open(output_path, 'wb') as f:
        for chunk in video_response.iter_content(chunk_size=8192):
            f.write(chunk)

    return title

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
        title = download_tiktok(link, video_path)
    except Exception as e:
        return jsonify({"error": f"download failed: {str(e)}"}), 500

    if not os.path.exists(video_path):
        return jsonify({"error": "video file not found after download"}), 500

    try:
        post_reel(video_path, caption or title, username, password)
    except Exception as e:
        return jsonify({"error": f"upload failed: {str(e)}"}), 500
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)

    return jsonify({"success": True, "message": "posted to reels!"})

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "running"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
