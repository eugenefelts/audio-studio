import streamlit as st
import yt_dlp
from pydub import AudioSegment
import librosa
import soundfile as sf
import tempfile
import os
import io
import warnings

# Suppress harmless Python 3.12 regex warnings from pydub
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pydub")

# ==========================================
# PAGE CONFIGURATION & MOBILE UI STYLING
# ==========================================
st.set_page_config(page_title="Audio Studio", page_icon="🎵", layout="centered")

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    .stButton>button { 
        border-radius: 10px; 
        font-weight: 600; 
        transition: 0.2s;
    }
    .stButton>button:active { transform: scale(0.95); }
    header {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.title("🎵 Audio Studio")
st.write("A mobile-friendly toolkit for your audio needs.")

if "dl_data" not in st.session_state:
    st.session_state.dl_data = None
if "dl_name" not in st.session_state:
    st.session_state.dl_name = None
if "dl_mime" not in st.session_state:
    st.session_state.dl_mime = None
if "semitones" not in st.session_state:
    st.session_state.semitones = 0

def clear_output():
    st.session_state.dl_data = None

MIME_TYPES = {
    "MP3": "audio/mpeg", "WAV": "audio/wav", "FLAC": "audio/flac",
    "M4A": "audio/mp4", "OGG": "audio/ogg", "AAC": "audio/aac"
}

tab1, tab2, tab3 = st.tabs(["⬇️ Downloader", "🔄 Converter", "🎚️ Pitch Shifter"])

# ------------------------------------------
# TOOL 1: YT-DLP DOWNLOADER (SUPERCHARGED)
# ------------------------------------------
with tab1:
    st.subheader("YouTube Downloader")
    st.info("💡 Note: YouTube frequently blocks cloud servers. If it fails, try a different video.")
    yt_url = st.text_input("Paste YouTube URL here:", placeholder="https://youtube.com/...")
    yt_format = st.selectbox("Select Output Format", ["MP3", "WAV", "M4A", "FLAC"], on_change=clear_output, key="yt_fmt")
    
    if st.button("Download & Extract Audio", use_container_width=True):
        if not yt_url:
            st.error("Please enter a valid URL.")
        else:
            with st.spinner(f"Bypassing checks & extracting {yt_format}..."):
                try:
                    with tempfile.TemporaryDirectory() as temp_dir:
                        # SUPERCHARGED OPTIONS: Added Android Client spoofing & SSL bypass
                        ydl_opts = {
                            'format': 'bestaudio/best',
                            'postprocessors':[{
                                'key': 'FFmpegExtractAudio',
                                'preferredcodec': yt_format.lower(),
                                'preferredquality': '192',
                            }],
                            'outtmpl': os.path.join(temp_dir, 'extracted_audio.%(ext)s'),
                            'quiet': True,
                            'nocheckcertificate': True, # Bypasses SSL issues on Linux
                            'ignoreerrors': False,
                            'no_warnings': True,
                            # This is the magic bullet for Streamlit 403 Forbidden errors:
                            'extractor_args': {'youtube': {'player_client':['android', 'web']}} 
                        }
                        
                        # Catch the exact yt-dlp internal error if it crashes
                        try:
                            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                                ydl.download([yt_url])
                        except Exception as inner_e:
                            st.error(f"YouTube Blocked the Request: {str(inner_e)}")
                            st.stop()
                            
                        files = os.listdir(temp_dir)
                        if not files:
                            st.error("Download failed: No file was generated. YouTube may have blocked this IP.")
                        else:
                            file_path = os.path.join(temp_dir, files[0])
                            with open(file_path, "rb") as f:
                                st.session_state.dl_data = f.read()
                            
                            st.session_state.dl_name = f"download.{yt_format.lower()}"
                            st.session_state.dl_mime = MIME_TYPES.get(yt_format, "audio/mpeg")
                            
                            st.success("Extraction complete!")
                            st.toast("✅ Ready to download!", icon="🎉")
                except Exception as e:
                    st.error(f"An unexpected error occurred: {str(e)}")

# ------------------------------------------
# TOOL 2: UNIVERSAL AUDIO CONVERTER
# ------------------------------------------
with tab2:
    st.subheader("Audio Converter")
    conv_file = st.file_uploader("Upload any audio file", type=["mp3", "wav", "m4a", "flac", "ogg", "aac", "wma"], key="conv_up")
    conv_format = st.selectbox("Convert To",["MP3", "WAV", "OGG", "FLAC", "AAC", "M4A"], on_change=clear_output, key="conv_fmt")
    
    if st.button("Convert Audio", use_container_width=True):
        if not conv_file:
            st.error("Please upload a file first.")
        else:
            with st.spinner(f"Converting to {conv_format}..."):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as tmp_in:
                        tmp_in.write(conv_file.getvalue())
                        tmp_in_path = tmp_in.name
                    
                    audio = AudioSegment.from_file(tmp_in_path)
                    os.remove(tmp_in_path) 
                    
                    fmt_kwargs = {}
                    if conv_format == "MP3": fmt_kwargs = {"format": "mp3", "bitrate": "192k"}
                    elif conv_format == "WAV": fmt_kwargs = {"format": "wav"}
                    elif conv_format == "OGG": fmt_kwargs = {"format": "ogg", "codec": "libvorbis"}
                    elif conv_format == "FLAC": fmt_kwargs = {"format": "flac"}
                    elif conv_format == "AAC": fmt_kwargs = {"format": "adts", "codec": "aac"}
                    elif conv_format == "M4A": fmt_kwargs = {"format": "ipod", "codec": "aac"}
                    
                    buffer = io.BytesIO()
                    audio.export(buffer, **fmt_kwargs)
                    
                    st.session_state.dl_data = buffer.getvalue()
                    st.session_state.dl_name = f"converted.{conv_format.lower()}"
                    st.session_state.dl_mime = MIME_TYPES.get(conv_format, "audio/mpeg")
                    
                    st.success("Conversion complete!")
                    st.toast("✅ Audio converted!", icon="🎉")
                except Exception as e:
                    st.error(f"Conversion failed: {str(e)}")

# ------------------------------------------
# TOOL 3: PRECISION PITCH SHIFTER
# ------------------------------------------
with tab3:
    st.subheader("Pitch Shifter")
    pitch_file = st.file_uploader("Upload audio to pitch shift", type=["mp3", "wav", "flac", "ogg", "m4a"], key="pitch_up")
    
    st.write("Adjust Pitch (Semitones):")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("⬇️ Down", use_container_width=True): 
            st.session_state.semitones -= 1
            clear_output()
    with col2:
        st.markdown(f"<h3 style='text-align: center; margin-top: 0px;'>{st.session_state.semitones}</h3>", unsafe_allow_html=True)
    with col3:
        if st.button("⬆️ Up", use_container_width=True): 
            st.session_state.semitones += 1
            clear_output()
            
    if st.button("Apply Pitch Shift", use_container_width=True):
        if not pitch_file:
            st.error("Please upload a file first.")
        else:
            with st.spinner("Processing pitch shift (this may take a moment)..."):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as tmp_in:
                        tmp_in.write(pitch_file.getvalue())
                        tmp_in_path = tmp_in.name
                        
                    y, sr = librosa.load(tmp_in_path, sr=None)
                    os.remove(tmp_in_path)
                    
                    if st.session_state.semitones != 0:
                        y = librosa.effects.pitch_shift(y, sr=sr, n_steps=st.session_state.semitones)
                    
                    buffer = io.BytesIO()
                    sf.write(buffer, y, sr, format='WAV')
                    
                    st.session_state.dl_data = buffer.getvalue()
                    st.session_state.dl_name = "pitch_shifted.wav"
                    st.session_state.dl_mime = "audio/wav"
                    
                    st.success("Pitch shift applied!")
                    st.toast("✅ Pitch shifted successfully!", icon="🎉")
                except Exception as e:
                    st.error(f"Failed to process pitch shift: {str(e)}")

# ==========================================
# UNIVERSAL DOWNLOAD BUTTON
# ==========================================
st.divider()
if st.session_state.dl_data is not None:
    st.markdown("### 📥 Your file is ready:")
    st.download_button(
        label=f"Download {st.session_state.dl_name}",
        data=st.session_state.dl_data,
        file_name=st.session_state.dl_name,
        mime=st.session_state.dl_mime,
        use_container_width=True,
        type="primary"
    )
