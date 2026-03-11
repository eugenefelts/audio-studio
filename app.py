import streamlit as st
import yt_dlp
from pydub import AudioSegment
import librosa
import soundfile as sf
import tempfile
import os
import io

# ==========================================
# PAGE CONFIGURATION & MOBILE UI STYLING
# ==========================================
st.set_page_config(page_title="Audio Studio", page_icon="🎵", layout="centered")

# Custom CSS to make the UI modern, sleek, and optimized for mobile
st.markdown("""
<style>
    /* Maximize container width on mobile */
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    /* Style buttons to be more sleek */
    .stButton>button { 
        border-radius: 10px; 
        font-weight: 600; 
        transition: 0.2s;
    }
    .stButton>button:active { transform: scale(0.95); }
    /* Hide the default Streamlit header/footer for an app-like feel */
    header {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.title("🎵 Audio Studio")
st.write("A mobile-friendly toolkit for your audio needs.")

# ==========================================
# SESSION STATE INITIALIZATION
# ==========================================
# We use this to hold the generated audio in memory so it isn't lost
# when the app refreshes, and to track pitch semitones.
if "dl_data" not in st.session_state:
    st.session_state.dl_data = None
if "dl_name" not in st.session_state:
    st.session_state.dl_name = None
if "dl_mime" not in st.session_state:
    st.session_state.dl_mime = None
if "semitones" not in st.session_state:
    st.session_state.semitones = 0

# Helper function to clear previous output when switching tools
def clear_output():
    st.session_state.dl_data = None

# ==========================================
# HELPER DICTIONARIES
# ==========================================
MIME_TYPES = {
    "MP3": "audio/mpeg", "WAV": "audio/wav", "FLAC": "audio/flac",
    "M4A": "audio/mp4", "OGG": "audio/ogg", "AAC": "audio/aac"
}

# ==========================================
# UI LAYOUT: TABS FOR DIFFERENT TOOLS
# ==========================================
tab1, tab2, tab3 = st.tabs(["⬇️ Downloader", "🔄 Converter", "🎚️ Pitch Shifter"])

# ------------------------------------------
# TOOL 1: YT-DLP DOWNLOADER
# ------------------------------------------
with tab1:
    st.subheader("YouTube Downloader")
    yt_url = st.text_input("Paste YouTube URL here:", placeholder="https://youtube.com/...")
    yt_format = st.selectbox("Select Output Format", ["MP3", "WAV", "M4A", "FLAC"], on_change=clear_output, key="yt_fmt")
    
    if st.button("Download & Extract Audio", use_container_width=True):
        if not yt_url:
            st.error("Please enter a valid URL.")
        else:
            with st.spinner(f"Extracting high-quality {yt_format}..."):
                try:
                    # Use a temporary directory that auto-deletes when finished
                    with tempfile.TemporaryDirectory() as temp_dir:
                        ydl_opts = {
                            'format': 'bestaudio/best',
                            'postprocessors':[{
                                'key': 'FFmpegExtractAudio',
                                'preferredcodec': yt_format.lower(),
                                'preferredquality': '192',
                            }],
                            'outtmpl': os.path.join(temp_dir, 'extracted_audio.%(ext)s'),
                            'quiet': True,
                            'noplaylist': True
                        }
                        
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([yt_url])
                            
                        # Find the output file
                        files = os.listdir(temp_dir)
                        if not files:
                            st.error("Download failed.")
                        else:
                            file_path = os.path.join(temp_dir, files[0])
                            # Read file into server memory (bytes)
                            with open(file_path, "rb") as f:
                                st.session_state.dl_data = f.read()
                            
                            st.session_state.dl_name = f"download.{yt_format.lower()}"
                            st.session_state.dl_mime = MIME_TYPES.get(yt_format, "audio/mpeg")
                            
                            st.success("Extraction complete!")
                            st.toast("✅ Ready to download!", icon="🎉")
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")

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
                    # Safely save uploaded file to temp path to prevent memory issues with Pydub
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as tmp_in:
                        tmp_in.write(conv_file.getvalue())
                        tmp_in_path = tmp_in.name
                    
                    audio = AudioSegment.from_file(tmp_in_path)
                    
                    # Delete the temporary input file immediately to save server space!
                    os.remove(tmp_in_path) 
                    
                    # Set format specifics for ffmpeg/pydub
                    fmt_kwargs = {}
                    if conv_format == "MP3": fmt_kwargs = {"format": "mp3", "bitrate": "192k"}
                    elif conv_format == "WAV": fmt_kwargs = {"format": "wav"}
                    elif conv_format == "OGG": fmt_kwargs = {"format": "ogg", "codec": "libvorbis"}
                    elif conv_format == "FLAC": fmt_kwargs = {"format": "flac"}
                    elif conv_format == "AAC": fmt_kwargs = {"format": "adts", "codec": "aac"}
                    elif conv_format == "M4A": fmt_kwargs = {"format": "ipod", "codec": "aac"}
                    
                    # Process entirely in memory (No disk saving)
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
    
    # Side-by-side buttons instead of a slider for precise mobile tapping
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("⬇️ Down", use_container_width=True): 
            st.session_state.semitones -= 1
            clear_output()
    with col2:
        # Display current shift value cleanly in the center
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
                    # Write to temporary file to ensure safe loading by Librosa
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as tmp_in:
                        tmp_in.write(pitch_file.getvalue())
                        tmp_in_path = tmp_in.name
                        
                    # Load audio (sr=None preserves the original sample rate)
                    y, sr = librosa.load(tmp_in_path, sr=None)
                    
                    # Cleanup immediately
                    os.remove(tmp_in_path)
                    
                    # Apply pitch shifting (preserves tempo)
                    if st.session_state.semitones != 0:
                        y = librosa.effects.pitch_shift(y, sr=sr, n_steps=st.session_state.semitones)
                    
                    # Write modified audio to memory buffer (WAV format for highest quality)
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
