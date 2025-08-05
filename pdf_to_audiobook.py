

#!/usr/bin/env python3


import os
import sys
import subprocess
import json
import requests
import argparse

# --- Configuration ---
PRIMARY_SERVER = "192.168.20.9:8880"
FALLBACK_SERVER = "localhost:8880"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def select_language():
    """Prompts the user to select a language until a valid choice is made."""
    while True:
        lang_input = input("Please specify the language for the audiobook (en/es): ").lower()
        if lang_input in ["en", "es"]:
            return lang_input

def get_voice(language):
    """Returns the voice based on the selected language."""
    return "ef_dora" if language == "es" else "af_heart"

def convert_pdf_to_text(pdf_path, txt_path):
    """Converts a PDF file to a text file using pdftotext."""
    print("Converting PDF to text...")
    try:
        subprocess.run(["pdftotext", pdf_path, txt_path], check=True)
        print(f"Raw text saved to '{txt_path}'")
        return True
    except FileNotFoundError:
        print("Error: 'pdftotext' could not be found. Please install poppler-utils.")
        return False
    except subprocess.CalledProcessError:
        print(f"Error: pdftotext failed to convert '{pdf_path}'.")
        return False

def format_text_with_gemini(raw_text_path):
    """Formats text using the Gemini API."""
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        return None

    print("Formatting text with Gemini 2.5 Flash...")
    try:
        with open(raw_text_path, 'r', encoding='utf-8') as f:
            raw_text_content = f.read()
    except FileNotFoundError:
        print(f"Error: Raw text file not found at '{raw_text_path}'")
        return None

    prompt = (
        "Please take the following OCR from a pdf, and format it to be like a script for an audiobook. "
        "Do not keep in any content that would not be spoken in an audiobook, but keep ALL the narration. "
        "Do not output anything except for the script. Only output the words that should be said. "
        "No speaker differences (\"Narrator:\", etc.). Only the words that should be read. "
        "Include the title and headings, but don't include the publishing info at the beggining. "
        "You may put publishing information in a readable format at the end of the script. "
        f"\n\n---\n{raw_text_content}"
    )

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}
    url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=300)
        response.raise_for_status()
        data = response.json()
        processed_script = data['candidates'][0]['content']['parts'][0]['text']
        if not processed_script:
            print("Error: Received empty script from Gemini API.")
            return None
        return processed_script
    except requests.exceptions.RequestException as e:
        print(f"Error calling Gemini API: {e}")
        return None
    except (KeyError, IndexError):
        print("Error: Failed to parse a valid response from the Gemini API.")
        print("Response:", response.text)
        return None


def generate_audiobook(script_content, voice, output_path):
    """Generates the audiobook using the TTS engine."""
    print(f"Generating audiobook (voice: {voice})...")
    payload = {
        "input": script_content,
        "model": "kokoro",
        "voice": voice,
        "response_format": "mp3"
    }
    headers = {"Content-Type": "application/json"}

    # Attempt primary server
    print(f"--> Attempting primary server: {PRIMARY_SERVER}")
    try:
        response = requests.post(
            f"http://{PRIMARY_SERVER}/v1/audio/speech",
            headers=headers,
            json=payload,
            stream=True,
            timeout=600
        )
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Successfully generated audiobook: {output_path}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"--> Primary server failed: {e}")

    # Attempt fallback server
    print(f"--> Attempting fallback server: {FALLBACK_SERVER}")
    try:
        response = requests.post(
            f"http://{FALLBACK_SERVER}/v1/audio/speech",
            headers=headers,
            json=payload,
            stream=True,
            timeout=600
        )
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Successfully generated audiobook: {output_path}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"--> Fallback server failed: {e}")
        print("Error: Audiobook generation failed on both primary and fallback servers.")
        return False

def main():
    """Main function to orchestrate the audiobook generation process."""
    parser = argparse.ArgumentParser(
        description="Generate an audiobook from a PDF or TXT file.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("input_file", help="Path to the input .pdf or .txt file.")
    parser.add_argument("language", nargs='?', choices=['en', 'es'], help="Language for the audiobook (en/es).")
    args = parser.parse_args()

    input_file = args.input_file
    language = args.language

    if not os.path.exists(input_file):
        print(f"Error: Input file not found at '{input_file}'")
        sys.exit(1)

    file_extension = os.path.splitext(input_file)[1].lower()
    if file_extension not in ['.pdf', '.txt']:
        print(f"Error: Unsupported file type '{file_extension}'. Please provide a .pdf or .txt file.")
        sys.exit(1)

    if not language:
        language = select_language()

    voice = get_voice(language)
    basename = os.path.splitext(os.path.basename(input_file))[0]
    output_file = f"{basename}.mp3"
    script_for_tts = ""

    if file_extension == '.pdf':
        print(f"Processing PDF file: {input_file}")
        raw_txt_file = f"{basename}.raw.txt"
        processed_txt_file = f"{basename}.processed.txt"

        if not convert_pdf_to_text(input_file, raw_txt_file):
            sys.exit(1)

        processed_script = format_text_with_gemini(raw_txt_file)
        if not processed_script:
            sys.exit(1)

        with open(processed_txt_file, 'w', encoding='utf-8') as f:
            f.write(processed_script)
        print(f"Processed script saved to '{processed_txt_file}'")
        script_for_tts = processed_script

    elif file_extension == '.txt':
        print(f"Processing text file directly: {input_file}")
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                script_for_tts = f.read()
        except FileNotFoundError:
            print(f"Error: Could not read text file at '{input_file}'")
            sys.exit(1)

    if script_for_tts:
        generate_audiobook(script_for_tts, voice, output_file)
    else:
        print("Error: No script content available for TTS.")
        sys.exit(1)

if __name__ == "__main__":
    main()
