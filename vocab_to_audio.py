import argparse
import asyncio
import json
import sys
import tempfile
import os
import shutil
import subprocess
import edge_tts

EN_VOICE = "en-GB-SoniaNeural"
EL_VOICE = "el-GR-AthinaNeural"


async def tts_clip(text, voice, outpath):
    await edge_tts.Communicate(text, voice).save(outpath)


def silence_clip(duration_ms, outpath):
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"aevalsrc=0:channel_layout=mono:sample_rate=24000:d={duration_ms/1000:.3f}",
        "-codec:a", "libmp3lame", "-b:a", "32k",
        outpath
    ], check=True, capture_output=True)


async def build_track(pages, output_path):
    tmpdir = tempfile.mkdtemp(prefix="vocab_audio_")
    clips = []

    short_silence = os.path.join(tmpdir, "pause_short.mp3")
    long_silence = os.path.join(tmpdir, "pause_long.mp3")
    page_pause = os.path.join(tmpdir, "pause_page.mp3")
    silence_clip(600, short_silence)
    silence_clip(1400, long_silence)
    silence_clip(2500, page_pause)

    clip_idx = 0

    for page_idx, (page_number, entries) in enumerate(pages):
        # Page announcement
        p = os.path.join(tmpdir, f"clip_{clip_idx:04d}.mp3")
        await tts_clip(f"Move to page {page_number}.", EN_VOICE, p)
        clips.append(p)
        clips.append(page_pause)
        clip_idx += 1

        for i, entry in enumerate(entries):
            p = os.path.join(tmpdir, f"clip_{clip_idx:04d}.mp3")
            await tts_clip(entry["term"], EN_VOICE, p)
            clips += [p, short_silence]
            clip_idx += 1

            if entry.get("english_meaning"):
                p = os.path.join(tmpdir, f"clip_{clip_idx:04d}.mp3")
                await tts_clip(entry["english_meaning"], EN_VOICE, p)
                clips += [p, short_silence]
                clip_idx += 1

            if entry.get("greek_meaning"):
                p = os.path.join(tmpdir, f"clip_{clip_idx:04d}.mp3")
                await tts_clip(entry["greek_meaning"], EL_VOICE, p)
                clips += [p, short_silence]
                clip_idx += 1

            if entry.get("example"):
                p = os.path.join(tmpdir, f"clip_{clip_idx:04d}.mp3")
                await tts_clip(entry["example"], EN_VOICE, p)
                clips.append(p)
                clip_idx += 1

            if i < len(entries) - 1:
                clips.append(long_silence)

        if page_idx < len(pages) - 1:
            clips.append(page_pause)

        print(f"  Page {page_number}: {len(entries)} entries done")

    concat_file = os.path.join(tmpdir, "concat.txt")
    with open(concat_file, "w", encoding="utf-8") as f:
        for clip in clips:
            f.write(f"file '{clip}'\n")

    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c:a", "aac", "-b:a", "128k",
        output_path
    ], check=True)

    shutil.rmtree(tmpdir)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, nargs="+", help="One or more JSON files (one per page)")
    parser.add_argument("--output", default=None, help="Output .mp4 filename")
    args = parser.parse_args()

    pages = []
    total_entries = 0
    for path in args.input:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        page_number = data.get("page_number", "unknown")
        entries = data.get("entries", [])
        if not entries:
            print(f"Warning: no entries in {path}", file=sys.stderr)
            continue
        pages.append((page_number, entries))
        total_entries += len(entries)

    if not pages:
        print("No entries found in any input file.", file=sys.stderr)
        sys.exit(1)

    if args.output:
        output_path = args.output
    elif len(pages) == 1:
        output_path = f"{pages[0][0]}.mp4"
    else:
        output_path = f"{pages[0][0]}-{pages[-1][0]}.mp4"

    print(f"Processing {total_entries} entries across {len(pages)} page(s)...")
    asyncio.run(build_track(pages, output_path))
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
