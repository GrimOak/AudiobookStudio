import asyncio
import os
import sys
import warnings
import edge_tts
from ebooklib import epub, ITEM_DOCUMENT
from bs4 import BeautifulSoup

# --- Configuration ---
CHUNK_SIZE = 1500  # Characters per chunk. Lower = smoother progress bar updates.

# Suppress ebooklib warnings
warnings.filterwarnings('ignore', category=UserWarning, module='ebooklib')
warnings.filterwarnings('ignore', category=FutureWarning, module='ebooklib')

def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=50, fill='█'):
    """
    Call in a loop to create terminal progress bar
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    sys.stdout.write(f'\r{prefix} |{bar}| {percent}% {suffix}')
    sys.stdout.flush()
    if iteration == total:
        print()

def extract_text_from_epub(epub_path):
    if not os.path.exists(epub_path):
        print(f"Error: File not found at {epub_path}")
        return None

    print(f"Reading EPUB file: {epub_path}...")
    try:
        book = epub.read_epub(epub_path)
    except Exception as e:
        print(f"Error reading EPUB file: {e}")
        return None

    full_text = []
    items = list(book.get_items())
    
    # Pre-scan to count items for a quick load bar
    print("Extracting text from chapters...")
    
    for item in items:
        if item.get_type() == ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            text = soup.get_text(separator=' ').strip()
            if text:
                full_text.append(text)
    
    joined_text = "\n\n".join(full_text)
    print(f"Extraction complete. Total length: {len(joined_text)} characters.")
    return joined_text

def chunk_text(text, chunk_size=CHUNK_SIZE):
    """
    Splits text into chunks to enable the progress bar and prevent timeouts.
    """
    chunks = []
    while len(text) > chunk_size:
        # Find the nearest period or newline to split cleanly
        split_index = text.rfind('.', 0, chunk_size)
        if split_index == -1:
            split_index = text.rfind('\n', 0, chunk_size)
        if split_index == -1:
            split_index = chunk_size
        
        # Include the punctuation in the current chunk
        chunks.append(text[:split_index+1])
        text = text[split_index+1:].strip()
    
    if text:
        chunks.append(text)
    return chunks

async def get_voice_selection():
    print("\nConnecting to Microsoft Edge servers to fetch voices...")
    try:
        voices = await edge_tts.list_voices()
    except Exception as e:
        print(f"Error: Could not fetch voices. {e}")
        return None

    # Filter for English voices and sort
    english_voices = [v for v in voices if "en-" in v['ShortName']]
    english_voices.sort(key=lambda x: x['ShortName'])

    print("\n--- Available Voices ---")
    options = []
    for idx, voice in enumerate(english_voices):
        # Clean up the name for display (e.g., "en-US-GuyNeural" -> "Guy")
        friendly_name = voice['ShortName'].split('-')[-1].replace("Neural", "")
        print(f"{idx + 1}. {friendly_name} ({voice['Gender']}) - {voice['Locale']}")
        options.append(voice['ShortName'])

    while True:
        try:
            choice = input("\nEnter the number of the voice: ")
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except ValueError:
            pass
        print("Invalid selection. Please enter a number from the list.")

async def convert_text_to_mp3(chunks, voice, output_filename):
    total_chunks = len(chunks)
    print(f"\nStarting conversion (Total parts: {total_chunks})")
    print(f"Saving to: {output_filename}")
    
    # Initialize the progress bar
    print_progress_bar(0, total_chunks, prefix='Progress:', suffix='Complete', length=40)

    # Delete existing file to start fresh
    if os.path.exists(output_filename):
        try:
            os.remove(output_filename)
        except PermissionError:
            print(f"\nError: Close the file '{output_filename}' before running this script!")
            return

    # Open file once and append binary data
    with open(output_filename, "wb") as f:
        for i, chunk in enumerate(chunks):
            communicate = edge_tts.Communicate(chunk, voice)
            
            # Stream data to file
            try:
                async for chunk_data in communicate.stream():
                    if chunk_data["type"] == "audio":
                        f.write(chunk_data["data"])
            except Exception as e:
                print(f"\n\nError processing part {i+1}: {e}")
                print("Your internet connection may have been interrupted.")
                return

            # Update progress bar
            print_progress_bar(i + 1, total_chunks, prefix='Progress:', suffix='Complete', length=40)
            
            # Tiny buffer to prevent server rate-limiting
            await asyncio.sleep(0.1)
    
    print(f"\n\nSUCCESS! Book saved as: {os.path.abspath(output_filename)}")

async def main():
    print("--- EPUB to MP3 with Progress Bar ---")
    
    # 1. Input File
    file_path = input("Enter path to .epub file: ").strip().strip('"').strip("'")
    
    # 2. Extract
    full_text = extract_text_from_epub(file_path)
    if not full_text: return

    # 3. Chunk
    chunks = chunk_text(full_text)
    
    # 4. Voice Selection
    selected_voice = await get_voice_selection()
    if not selected_voice: return
    
    # 5. Output Filename
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_file = f"{base_name}.mp3"
    
    # 6. Convert with Bar
    await convert_text_to_mp3(chunks, selected_voice, output_file)

if __name__ == "__main__":
    # Windows fix for asyncio
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nProcess cancelled by user.")