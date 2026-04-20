import argparse
import csv
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

# Initialize env variables from .env
load_dotenv()
ELEVEN_LABS_API_KEY = os.getenv("ELEVEN_LABS_API_KEY")

# CSV Options
OUTPUT_CSV_PATH = "voice_list.csv"
VOICE_PAGE_SIZE = 100


def init_elevenlabs_instance() -> ElevenLabs:
    """
    Initialize ElevenLabs instance with API Key
    """
    if not ELEVEN_LABS_API_KEY:
        raise RuntimeError("ELEVEN_LABS_API_KEY is not set in environment.")
    return ElevenLabs(api_key=ELEVEN_LABS_API_KEY)


def get_all_shared_voices(instance: ElevenLabs, page_size: int = VOICE_PAGE_SIZE):
    """
    Retrieve all shared voices from ElevenLabs using pagination
    """
    voices = []
    page = 0

    while True:
        response = instance.voices.get_shared(
            page_size=page_size,
            page=page,
        )
        batch = response.voices or []
        voices.extend(batch)

        print(f"Fetched page {page}: {len(batch)} voices (total: {len(voices)})")

        if not batch or not response.has_more:
            break
        page += 1

    return voices


def get_all_default_voices_from_search(instance: ElevenLabs, page_size: int = VOICE_PAGE_SIZE):
    """
    Retrieve all default voices from /v2/voices/search
    """
    voices = []
    next_page_token = None
    expected_total_count = None

    while True:
        response = instance.voices.search(
            page_size=page_size,
            next_page_token=next_page_token,
            voice_type="default",
            include_total_count=True,
        )
        batch = response.voices or []
        voices.extend(batch)

        if expected_total_count is None:
            expected_total_count = getattr(response, "total_count", None)
        print(f"Fetched default voices: {len(batch)} (total: {len(voices)})")

        has_more = bool(getattr(response, "has_more", False))
        next_page_token = getattr(response, "next_page_token", None)
        if not has_more or not next_page_token:
            break

    if expected_total_count is not None:
        unique_count = len({getattr(voice, "voice_id", "") for voice in voices if getattr(voice, "voice_id", "")})
        print(f"Default voice check: expected={expected_total_count}, collected_unique={unique_count}")

    return voices


def get_voice_details(instance: ElevenLabs, voice_id: str):
    """
    Retrieve full voice details by voice ID, with safe fallback
    """
    try:
        return instance.voices.get(voice_id=voice_id)
    except Exception:
        return None


def get_all_default_voice_details(instance: ElevenLabs, page_size: int = VOICE_PAGE_SIZE):
    """
    Retrieve default voices and expand to full metadata when possible
    """
    default_voice_summaries = get_all_default_voices_from_search(instance, page_size=page_size)

    voices = []
    for voice in default_voice_summaries:
        voice_id = getattr(voice, "voice_id", "")
        if not voice_id:
            continue
        detailed_voice = get_voice_details(instance, voice_id)
        voices.append(detailed_voice or voice)

    print(f"Resolved default voice details: {len(voices)}")
    return voices


def get_all_voices(
    instance: ElevenLabs,
    page_size: int = VOICE_PAGE_SIZE,
):
    """
    Retrieve all voices from shared library + default voices
    """
    shared_voices = get_all_shared_voices(instance, page_size=page_size)
    default_voices = get_all_default_voice_details(instance, page_size=page_size)

    voice_entries = []
    seen = set()

    for voice in shared_voices:
        key = (getattr(voice, "voice_id", ""), "shared_library")
        if key in seen:
            continue
        seen.add(key)
        voice_entries.append((voice, "shared_library"))

    for voice in default_voices:
        key = (getattr(voice, "voice_id", ""), "default_voices")
        if key in seen:
            continue
        seen.add(key)
        voice_entries.append((voice, "default_voices"))

    print(f"Total collected voices: {len(voice_entries)}")
    return voice_entries


def convert_voice_to_csv_row(voice, voice_source: str) -> dict:
    """
    Convert voice model to a flat CSV row dict
    """
    row = {"voice_source": voice_source}
    data = voice.model_dump()
    for key, value in data.items():
        if isinstance(value, (dict, list)):
            row[key] = json.dumps(value, ensure_ascii=False)
        elif value is None:
            row[key] = ""
        else:
            row[key] = value
    return row


def save_voice_list_csv(voice_entries, output_path: Path) -> None:
    """
    Save voice metadata to CSV
    """
    rows = []
    fieldnames = []
    seen = set()

    for voice, voice_source in voice_entries:
        row = convert_voice_to_csv_row(voice, voice_source)
        rows.append(row)
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})

    print(f"Saved {len(rows)} voices to {output_path}")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Fetch ElevenLabs shared + default voices and save metadata to CSV.",
    )
    parser.add_argument(
        "--output",
        default=OUTPUT_CSV_PATH,
        help=f"Output CSV path (default: {OUTPUT_CSV_PATH})",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=VOICE_PAGE_SIZE,
        help=f"Voices per API request, max {VOICE_PAGE_SIZE} (default: {VOICE_PAGE_SIZE})",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()

    page_size = args.page_size
    if page_size < 1 or page_size > VOICE_PAGE_SIZE:
        raise ValueError(f"--page-size must be between 1 and {VOICE_PAGE_SIZE}")

    output_path = Path(args.output).expanduser().resolve()
    instance = init_elevenlabs_instance()
    voice_entries = get_all_voices(
        instance,
        page_size=page_size,
    )
    save_voice_list_csv(voice_entries, output_path)


if __name__ == "__main__":
    main()
