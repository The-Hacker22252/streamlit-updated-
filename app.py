import os
import glob
import time
import shutil
import streamlit as strl
import yt_dlp

# 1. Main Page and UI Design Setup
strl.set_page_config(page_title="NexStream Pro | Media Downloader", page_icon="⚡", layout="wide")

# Check if FFmpeg is installed on this system
FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None

strl.markdown("""
    <style>
    .main { background-color: #0B0F19; color: #E2E8F0; }
    .main-title {
        font-size: 3rem !important;
        font-weight: 800 !important;
        background: linear-gradient(135deg, #FF416C 0%, #FF4B2B 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 5px;
    }
    .dashboard-card {
        background-color: #161D30;
        border: 1px solid #24324F;
        border-radius: 12px;
        padding: 25px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
    .stButton>button {
        width: 100% !important;
        background: linear-gradient(90deg, #10B981 0%, #059669 100%) !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 14px 20px !important;
        font-size: 16px !important;
        font-weight: 700 !important;
    }
    </style>
""", unsafe_allow_html=True)

# 2. Tracking System Session Variables
if 'download_progress' not in strl.session_state:
    strl.session_state.download_progress = 0.0
if 'download_speed' not in strl.session_state:
    strl.session_state.download_speed = "0 MB/s"
if 'download_status' not in strl.session_state:
    strl.session_state.download_status = "Idle"

def progress_callback(d):
    if d['status'] == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
        downloaded = d.get('downloaded_bytes', 0)
        speed = d.get('speed', 0)
        if speed:
            strl.session_state.download_speed = f"{speed / (1024 * 1024):.2f} MB/s"
        percent = downloaded / total
        strl.session_state.download_progress = min(percent, 1.0)
        strl.session_state.download_status = "Downloading stream..."
    elif d['status'] == 'finished':
        strl.session_state.download_progress = 1.0
        strl.session_state.download_status = "Finalizing file..."

def clean_old_files():
    for f in glob.glob("downloaded_media.*"):
        try: os.remove(f)
        except: pass

# FIXED: Explicitly returns the first string path from the list, never the list itself
def get_output_file():
    files = glob.glob("downloaded_media.*")
    return files[0] if files else None

# 3. Layout Rendering Interface
strl.markdown("<h1 class='main-title'>NEXSTREAM PRO</h1>", unsafe_allow_html=True)

if FFMPEG_AVAILABLE:
    strl.success("🚀 FFmpeg system engine detected! HD and MP3 conversions unlocked.")
else:
    strl.warning("⚠️ FFmpeg not found on computer. Running in Compatibility Mode (720p Video Max, Audio conversion disabled).")

left_col, right_col = strl.columns(2, gap="large")

with left_col:
    strl.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
    strl.subheader("🎛️ Control Panel")
    url_input = strl.text_input("YouTube Link Input:", placeholder="https://youtube.com...")
    
    format_options = ["Full Video (MP4)", "Audio Only (MP3)"] if FFMPEG_AVAILABLE else ["Full Video (MP4)"]
    media_format = strl.selectbox("Output Format:", format_options)
    
    if media_format == "Full Video (MP4)":
        quality_options = ["Best Available (Requires FFmpeg)", "720p Max (No FFmpeg Needed)"] if FFMPEG_AVAILABLE else ["720p Max (No FFmpeg Needed)"]
        quality = strl.selectbox("Quality Profile:", quality_options)
    else:
        quality = strl.selectbox("Audio Bitrate:", ["320kbps", "192kbps", "128kbps"])
        
    process_btn = strl.button("🚀 EXECUTE DOWNLOADING")
    strl.markdown("</div>", unsafe_allow_html=True)

with right_col:
    strl.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
    strl.subheader("📊 Live Display Monitor")
    m_col1, m_col2 = strl.columns(2)
    with m_col1:
        strl.metric(label="System Status", value=strl.session_state.download_status)
    with m_col2:
        strl.metric(label="Bandwidth Speed", value=strl.session_state.download_speed)
    p_bar = strl.progress(strl.session_state.download_progress)
    strl.markdown("</div>", unsafe_allow_html=True)

# 4. Engine Run Pipeline Logic
if process_btn:
    if not url_input:
        strl.error("Configuration Execution Blocked: Link String Missing.")
    else:
        try:
            strl.session_state.download_status = "Analyzing Target..."
            strl.session_state.download_progress = 0.0
            clean_old_files()
            
            with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                meta = ydl.extract_info(url_input, download=False)
            
            with right_col:
                strl.markdown(f"""
                    <div class='dashboard-card' style='border-color: #3B82F6;'>
                        <b>Title:</b> {meta.get('title', 'Unknown')}<br>
                        <b>Creator:</b> {meta.get('uploader', 'Unknown')}<br>
                        <b>Length:</b> {time.strftime('%H:%M:%S', time.gmtime(meta.get('duration', 0)))}
                    </div>
                """, unsafe_allow_html=True)
            
            ydl_opts = {
                'outtmpl': 'downloaded_media.%(ext)s',
                'progress_hooks': [progress_callback],
                'quiet': True,
                'no_warnings': True
            }

            if media_format == "Audio Only (MP3)":
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': quality.replace("kbps", ""),
                    }]
                })
            else:
                if quality == "Best Available (Requires FFmpeg)" and FFMPEG_AVAILABLE:
                    ydl_opts['format'] = 'bestvideo+bestaudio/best'
                else:
                    ydl_opts['format'] = 'best[ext=mp4]/best'

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url_input])
                
            output_file_path = get_output_file()
            
            if output_file_path and os.path.exists(output_file_path):
                p_bar.progress(1.0)
                strl.session_state.download_status = "Finished Stream Transfer"
                strl.toast("Transcoding Process Completed!", icon="🎉")
                
                with open(output_file_path, "rb") as final_data:
                    binary_payload = final_data.read()
                    
                ext_lbl = "mp3" if media_format == "Audio Only (MP3)" else "mp4"
                
                with left_col:
                    strl.download_button(
                        label=f"📥 RETRIEVE COMPLETED .{ext_lbl.upper()} FILE",
                        data=binary_payload,
                        file_name=f"Download_{int(time.time())}.{ext_lbl}",
                        mime="audio/mpeg" if ext_lbl == "mp3" else "video/mp4"
                    )
        except Exception as system_fault:
            strl.error(f"Error Processing Subsystem Chain: {str(system_fault)}")
            strl.session_state.download_status = "Pipeline Halted"
