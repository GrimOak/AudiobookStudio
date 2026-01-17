# EPUB to Audiobook Converter (Neural TTS)

I wrote this script because I wanted to listen to my `.epub` collection without suffering through the standard robotic system voices, and I didn't want to pay for expensive API subscriptions.

This tool uses the **Microsoft Edge TTS** engine (via `edge-tts`) to generate high-quality, human-sounding audio (Neural voices) completely for free. It processes the book in chunks to prevent server timeouts and gives you a nice progress bar so you aren't staring at a blank screen.

## Why this exists?

Most free scripts try to send the whole book to the TTS server at once, which usually crashes or times out for anything larger than a pamphlet. 

**This script:**
1.  **Parses** the EPUB to strip HTML tags.
2.  **Chunks** the text into manageable pieces (smart-splitting by sentences).
3.  **Streams** the audio directly to a file
4.  **Shows** a real-time progress bar.

## Prerequisites

You just need Python 3.x and a few dependencies.

```bash
pip install edge-tts ebooklib beautifulsoup4
```

How to run it
```bash
Clone this repo or download epub_to_mp3_with_bar.py.
```

Run the script:

```bash

python app.py
```

# USAGE

Enter the path to your file when prompted (you can just drag and drop the file into the terminal).

Pick a voice.

Recommendation: en-US-AvaNeural (Female) and en-US-ChristopherNeural (Male) are the best ones for long-form reading.

A few notes
Online Only: This hits the Microsoft servers to generate audio, so you need an active internet connection.

Speed: A standard novel takes about 25-30 minutes to convert. given the fact that you are converting over 10s to 100s of thousands of words into audio.

REAL WORLD TEST - 700k words took 9 hours to generate 68 hours of audiobook

Don't open the file while it's running: The script appends binary data to the MP3 in real-time. If you try to play it while it's converting, it might lock the file and crash the script.

# License

be free. if you create new features or build off of this program, just credit me or smt. thanks!

