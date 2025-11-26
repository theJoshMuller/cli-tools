#!/usr/bin/env python3

import subprocess
import whisper
from whisper.utils import WriteSRT
from pathlib import Path

print("""
 _  __               _ _       _____                              _ _               
| |/ /__ _ _ __ ___ (_| )___  |_   _| __ __ _ _ __  ___  ___ _ __(_) |__   ___ _ __ 
 | ' // _` | '_ ` _ \| |// __|   | || '__/ _` | '_ \/ __|/ __| '__| | '_ \ / _ \ '__|
 | . \ (_| | | | | | | | \__ \   | || | | (_| | | | \__ \ (__| |  | | |_) |  __/ |   
 |_|\_\__,_|_| |_| |_|_| |___/   |_||_|  \__,_|_| |_|___/\___|_|  |_|_.__/ \___|_|   
                                                                                      
""")
print("Welcome to Kami's Transcriber!")
print("This tool will download the audio from a YouTube video and create subtitles.")
print()

# Define and create the output directory
output_dir = Path.home() / "Desktop"
output_dir.mkdir(parents=True, exist_ok=True)


# Prompt for URL
url = input("Step 1: Paste the YouTube URL here: ")

# Get video title
print()
print("Getting video title...")
title = subprocess.run(
    ["yt-dlp", "--print", "%(title)s", url], capture_output=True, text=True
).stdout.strip()
# Sanitize title for filename
safe_title = (
    title.replace("/", "_")
    .replace("\\", "_")
    .replace(":", "_")
    .replace("*", "_")
    .replace("?", "_")
    .replace('"', "_")
    .replace("<", "_")
    .replace(">", "_")
    .replace("|", "_")
)
audio_file = output_dir / (safe_title + ".mp3")
srt_file = output_dir / (safe_title + ".srt")
print(f"Video title: {title}")

# Download audio
print()
print("Step 2: Downloading audio from the video... (this may take a minute)")
subprocess.run(
    ["yt-dlp", "-x", "--audio-format", "mp3", "-o", str(audio_file), url], check=True
)
print("Audio downloaded successfully!")

# Transcribe with Whisper
print()
print("Step 3: Loading the Whisper AI model...")
model = whisper.load_model("small")
print("Model loaded. Now transcribing the audio... (this may take several minutes)")
print("You will see progress below as words and timestamps appear:")
result = model.transcribe(str(audio_file), verbose=True)
print("Transcription finished!")

# Save SRT
print()
print("Step 4: Saving the subtitles file...")
writer = WriteSRT(str(output_dir))
with open(srt_file, "w", encoding="utf-8") as f:
    writer.write_result(result, f)
print(f"Subtitles saved to your Desktop as {srt_file.name}")

# Inform user
print()
print("🎉 All done! Your SRT file is ready.")
print(f'You can find it as "{srt_file.name}" on your Desktop.')
input("Press Enter to close the program.")
