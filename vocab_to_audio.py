import argparse
import json
import sys
import tempfile
import os
from pathlib import Path
from gtts import gTTS
from pydub import AudioSegment


def tts_clip(text, lang):
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.close()
    gTTS(text=text, lang=lang).save(tmp.name)
    audio = AudioSegment.from_mp3(tmp.name)
    os.unlink(tmp.name)
    return audio


def build_track(entries):
    short_pause = AudioSegment.silent(duration=600)
    long_pause = AudioSegment.silent(duration=1400)
    track = AudioSegment.empty()

    for i, entry in enumerate(entries):
        code_and_term = f"{entry['code']}. {entry['term']}"
        track += tts_clip(code_and_term, "en")
        track += short_pause

        if entry.get("english_meaning"):
            track += tts_clip(entry["english_meaning"], "en")
            track += short_pause

        if entry.get("greek_meaning"):
            track += tts_clip(entry["greek_meaning"], "el")
            track += short_pause

        if entry.get("example"):
            track += tts_clip(entry["example"], "en")

        if i < len(entries) - 1:
            track += long_pause

    return track


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to JSON file with parsed entries")
    parser.add_argument("--output", default=None, help="Output .mp4 filename")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)

    page_number = data.get("page_number", "unknown")
    entries = data.get("entries", [])

    if not entries:
        print("No entries found in input file.", file=sys.stderr)
        sys.exit(1)

    output_path = args.output or f"{page_number}.mp4"

    print(f"Processing {len(entries)} entries from page {page_number}...")
    track = build_track(entries)

    track.export(output_path, format="mp4", codec="aac")
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
