import os

# --- 1. The Advanced App Logic (app.py) ---
app_code = """import streamlit as st
import asyncio
import edge_tts
import os
import re
import tempfile
import io
import zipfile
from bs4 import BeautifulSoup

# File Parsers
from ebooklib import epub, ITEM_DOCUMENT
import pypdf
import docx
from striprtf.striprtf import rtf_to_text
from odf import text as odf_text
from odf.opendocument import load as load_odf

# --- Custom CSS ---
st.set_page_config(page_title="TTS Studio Pro", page_icon="🎧", layout="centered")
st.markdown(\"\"\"
    <style>
    .stApp { background-color: #0e1117; color: #fafafa; }
    h1 { text-align: center; background: -webkit-linear-gradient(45deg, #00d2ff, #3a7bd5); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800; }
    .stFileUploader { border: 2px dashed #3a7bd5; border-radius: 10px; padding: 10px; }
    .progress-container { width: 100%; background-color: #2b2b2b; border-radius: 15px; margin: 10px 0; height: 20px; overflow: hidden; }
    .progress-bar-fill { height: 100%; background: linear-gradient(90deg, #00d2ff, #3a7bd5); transition: width 0.3s ease-in-out; }
    
    /* Selection Box Styling */
    .chapter-selector { max-height: 300px; overflow-y: auto; border: 1px solid #333; padding: 10px; border-radius: 5px; background: #161b22; }
    </style>
\"\"\", unsafe_allow_html=True)

# --- Helper Functions ---

def clean_text_logic(text):
    if not text: return ""
    text = re.sub(r'[-/_*]{3,}', ' ', text)
    text = text.replace('/', ' ').replace('\\\\', ' ')
    text = re.sub(r'\\s+', ' ', text).strip()
    return text

def extract_epub_chapters(epub_path):
    \"\"\"Returns list of dicts: [{'title': 'Chapter 1', 'text': '...', 'id': 0}, ...]\"\"\"
    book = epub.read_epub(epub_path)
    chapters = []
    item_count = 1
    
    for item in book.get_items():
        if item.get_type() == ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            title_tag = soup.find(['h1', 'h2', 'h3'])
            title = title_tag.get_text().strip() if title_tag else f"Chapter {item_count}"
            text = soup.get_text(separator=' ').strip()
            
            if len(text) > 50:
                chapters.append({
                    'id': item_count, 
                    'title': title, 
                    'text': clean_text_logic(text)
                })
                item_count += 1
    return chapters

def extract_full_text(uploaded_file, ext):
    text_content = ""
    try:
        if ext == 'epub':
            # This is the fallback if user DOESN'T use chapter splitter
            with tempfile.NamedTemporaryFile(delete=False, suffix=".epub") as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name
            raw_chapters = extract_epub_chapters(tmp_path)
            text_content = "\\n\\n".join([c['text'] for c in raw_chapters])
            os.remove(tmp_path)
        
        elif ext == 'pdf':
            pdf_reader = pypdf.PdfReader(io.BytesIO(uploaded_file.getvalue()))
            text_content = "\\n".join([page.extract_text() for page in pdf_reader.pages])
        elif ext == 'docx':
            doc = docx.Document(io.BytesIO(uploaded_file.getvalue()))
            text_content = "\\n".join([para.text for para in doc.paragraphs])
        elif ext in ['txt', 'md', 'html']:
            raw = uploaded_file.getvalue().decode("utf-8", errors="ignore")
            if ext == 'html':
                soup = BeautifulSoup(raw, 'html.parser')
                text_content = soup.get_text(separator=' ')
            else:
                text_content = raw
        elif ext == 'rtf':
            text_content = rtf_to_text(uploaded_file.getvalue().decode("utf-8", errors="ignore"))
        elif ext == 'odt':
            with tempfile.NamedTemporaryFile(delete=False, suffix=".odt") as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name
            doc = load_odf(tmp_path)
            for element in doc.getElementsByType(odf_text.P):
                text_content += str(element) + "\\n"
            os.remove(tmp_path)
    except Exception:
        return None
    return clean_text_logic(text_content)

def chunk_text(text, chunk_size=2500):
    chunks = []
    while len(text) > chunk_size:
        split_index = text.rfind('.', 0, chunk_size)
        if split_index == -1: split_index = text.rfind('\\n', 0, chunk_size)
        if split_index == -1: split_index = chunk_size
        chunks.append(text[:split_index+1])
        text = text[split_index+1:].strip()
    if text: chunks.append(text)
    return chunks

async def get_voices():
    voices = await edge_tts.list_voices()
    english = [v for v in voices if "en-" in v['ShortName']]
    english.sort(key=lambda x: x['ShortName'])
    return english

async def generate_audio_simple(chunks, voice, rate_str, status_slot, bar_slot):
    combined = b""
    total = len(chunks)
    bar_slot.markdown(f'<div class="progress-container"><div class="progress-bar-fill" style="width: 0%;"></div></div>', unsafe_allow_html=True)
    
    for i, chunk in enumerate(chunks):
        communicate = edge_tts.Communicate(chunk, voice, rate=rate_str)
        async for data in communicate.stream():
            if data["type"] == "audio":
                combined += data["data"]
        
        percent = int(((i + 1) / total) * 100)
        bar_slot.markdown(f'<div class="progress-container"><div class="progress-bar-fill" style="width: {percent}%;"></div></div>', unsafe_allow_html=True)
        if status_slot:
            status_slot.markdown(f"Processing part {i+1}/{total} ({percent}%)")
        await asyncio.sleep(0.1)
    
    return combined

# --- Main UI ---
st.title("🎧 AI Audiobook Studio")

uploaded_file = st.file_uploader("Upload Book", type=['epub', 'pdf', 'docx', 'txt', 'rtf', 'md', 'html', 'odt'])

# Settings Row
c1, c2 = st.columns(2)
with c1:
    if "voices" not in st.session_state:
        st.session_state.voices = asyncio.run(get_voices())
    voice_map = {f"{v['ShortName'].split('-')[-1].replace('Neural','')} ({v['Gender']})" : v['ShortName'] for v in st.session_state.voices}
    selected_voice = st.selectbox("Voice", options=list(voice_map.keys()))

with c2:
    speed = st.slider("Speed", -50, 50, 0, 10, "%d%%")
    rate_str = f"+{speed}%" if speed >= 0 else f"{speed}%"

# Session State for EPUB Chapters
if "chapters_cache" not in st.session_state:
    st.session_state.chapters_cache = []

# --- Logic: EPUB vs Others ---
is_epub = uploaded_file is not None and uploaded_file.name.lower().endswith('.epub')
selected_chapters = []
run_conversion = False

if is_epub:
    st.divider()
    col_scan, col_info = st.columns([1, 3])
    
    with col_scan:
        if st.button("🔍 Scan Chapters"):
            with st.spinner("Scanning EPUB..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".epub") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                
                chapters = extract_epub_chapters(tmp_path)
                st.session_state.chapters_cache = chapters
                os.remove(tmp_path)
                st.rerun()

    # Show Selection Box if chapters are cached
    if st.session_state.chapters_cache:
        with st.expander("📋 Select Chapters to Convert", expanded=True):
            
            # Select All Toggle
            all_selected = st.checkbox("Select All", value=True)
            
            # Scrollable Container for Chapters
            with st.container(height=300):
                chapter_selections = {}
                for chap in st.session_state.chapters_cache:
                    # Default to 'all_selected' value unless manually changed
                    is_checked = st.checkbox(f"{chap['id']}. {chap['title']}", value=all_selected, key=f"ch_{chap['id']}")
                    if is_checked:
                        chapter_selections[chap['id']] = chap

            # Filter the list based on selection
            selected_chapters = list(chapter_selections.values())
            
            st.info(f"Selected {len(selected_chapters)} chapters for conversion.")
            
            if st.button("🚀 Convert Selected Chapters", type="primary"):
                run_conversion = True
                conversion_mode = "EPUB_SPLIT"

elif uploaded_file and not is_epub:
    # Non-EPUB standard start button
    if st.button("🚀 Start Conversion"):
        run_conversion = True
        conversion_mode = "SINGLE_FILE"

# --- Conversion Execution ---
if run_conversion:
    status_slot = st.empty()
    bar_slot = st.empty()
    
    # 1. EPUB Split Mode
    if conversion_mode == "EPUB_SPLIT":
        if not selected_chapters:
            st.error("Please select at least one chapter!")
        else:
            processed_files = []
            main_progress = st.progress(0)
            
            for idx, chap in enumerate(selected_chapters):
                clean_title = re.sub(r'[^a-zA-Z0-9 ]', '', chap['title'])[:30]
                status_slot.text(f"Converting Chapter {idx+1}/{len(selected_chapters)}: {clean_title}")
                
                chunks = chunk_text(chap['text'])
                audio_data = asyncio.run(generate_audio_simple(chunks, voice_map[selected_voice], rate_str, st.empty(), st.empty()))
                
                filename = f"{idx+1:02d} - {clean_title}.mp3"
                processed_files.append((filename, audio_data))
                main_progress.progress((idx + 1) / len(selected_chapters))
            
            bar_slot.empty()
            status_slot.success("✅ Batch Conversion Complete!")
            
            # ZIP Creation
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for fname, data in processed_files:
                    zf.writestr(fname, data)
            
            st.download_button(
                "📥 Download Audiobook (.zip)", 
                data=zip_buffer.getvalue(), 
                file_name=f"{uploaded_file.name.split('.')[0]}_audiobook.zip", 
                mime="application/zip", 
                use_container_width=True
            )

    # 2. Single File Mode
    elif conversion_mode == "SINGLE_FILE":
        ext = uploaded_file.name.split('.')[-1].lower()
        with st.spinner("Extracting text..."):
            text = extract_full_text(uploaded_file, ext)
        
        if text:
            chunks = chunk_text(text)
            try:
                mp3_data = asyncio.run(generate_audio_simple(chunks, voice_map[selected_voice], rate_str, status_slot, bar_slot))
                status_slot.success("Done!")
                st.download_button(
                    "📥 Download MP3", 
                    data=mp3_data, 
                    file_name=f"{uploaded_file.name.split('.')[0]}.mp3", 
                    mime="audio/mpeg", 
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Error: {e}")
"""

# --- 2. Requirements ---
req_code = """streamlit
edge-tts
ebooklib
beautifulsoup4
pypdf
python-docx
striprtf
odfpy
"""

# --- 3. Dockerfile ---
dockerfile_code = """FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
"""

# --- 4. Docker Compose ---
compose_code = """version: '3'
services:
  epub-to-mp3:
    build: .
    ports:
      - "8501:8501"
"""

# --- Write Files ---
print("Writing V1 Project Files (Scan & Select Update)...")

with open("app.py", "w", encoding="utf-8") as f:
    f.write(app_code)

with open("requirements.txt", "w", encoding="utf-8") as f:
    f.write(req_code)

with open("Dockerfile", "w", encoding="utf-8") as f:
    f.write(dockerfile_code)

with open("docker-compose.yml", "w", encoding="utf-8") as f:
    f.write(compose_code)

print("✅ Success! Run: docker-compose build --no-cache && docker-compose up --force-recreate")