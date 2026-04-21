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

ACCENT_LANGUAGE_MAP = {
    "american": "en",
    "british": "en",
    "australian": "en",
    "canadian": "en",
    "irish": "en",
    "scottish": "en",
    "new zealand": "en",
    "new zealander": "en",
    "south african": "en",
    "mexican": "es",
    "castilian": "es",
    "argentinian": "es",
    "argentine": "es",
    "colombian": "es",
    "chilean": "es",
    "peruvian": "es",
    "venezuelan": "es",
    "brazilian": "pt",
}

ACCENT_LOCALE_MAP = {
    "american": "en-US",
    "british": "en-GB",
    "australian": "en-AU",
    "canadian": "en-CA",
    "irish": "en-IE",
    "scottish": "en-GB",
    "new zealand": "en-NZ",
    "new zealander": "en-NZ",
    "south african": "en-ZA",
    "mexican": "es-MX",
    "castilian": "es-ES",
    "argentinian": "es-AR",
    "argentine": "es-AR",
    "colombian": "es-CO",
    "chilean": "es-CL",
    "peruvian": "es-PE",
    "venezuelan": "es-VE",
    "brazilian": "pt-BR",
}


def _dedupe_keep_order(values):
    deduped = []
    seen = set()
    for value in values:
        if not value:
            continue
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def get_supported_model_info(data: dict):
    """
    Extract supported model IDs from available voice metadata
    """
    model_ids = []
    sources = []

    high_quality_base_model_ids = data.get("high_quality_base_model_ids")
    if isinstance(high_quality_base_model_ids, list):
        model_ids.extend([model_id for model_id in high_quality_base_model_ids if model_id])
        if high_quality_base_model_ids:
            sources.append("high_quality_base_model_ids")

    verified_languages = data.get("verified_languages")
    if isinstance(verified_languages, list):
        verified_model_ids = []
        for item in verified_languages:
            if not isinstance(item, dict):
                continue
            model_id = item.get("model_id")
            if model_id:
                verified_model_ids.append(model_id)
        if verified_model_ids:
            model_ids.extend(verified_model_ids)
            sources.append("verified_languages.model_id")

    model_ids = _dedupe_keep_order(model_ids)
    source = ",".join(_dedupe_keep_order(sources)) if sources else "none"
    return model_ids, source


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
    data = voice.model_dump()
    
    row = {"voice_source": voice_source, **data}

    labels = data.get("labels") if isinstance(data.get("labels"), dict) else {}
    verified_languages = data.get("verified_languages") if isinstance(data.get("verified_languages"), list) else []
    sharing = data.get("sharing") if isinstance(data.get("sharing"), dict) else {}
    supported_model_ids, supported_model_source = get_supported_model_info(data)
    row["supported_model_ids"] = supported_model_ids
    row["supported_model_count"] = len(supported_model_ids)
    row["supported_model_source"] = supported_model_source

    preferred_language = labels.get("language")
    primary_verified_language = None
    for item in verified_languages:
        if not isinstance(item, dict):
            continue
        if preferred_language and item.get("language") == preferred_language:
            primary_verified_language = item
            break
        if primary_verified_language is None:
            primary_verified_language = item

    # Backfill shared-style columns for default voices.
    if not row.get("use_case"):
        row["use_case"] = labels.get("use_case", "")
    if not row.get("gender"):
        row["gender"] = labels.get("gender", "")
    if not row.get("accent"):
        row["accent"] = labels.get("accent", "")
    if not row.get("age"):
        row["age"] = labels.get("age", "")
    if not row.get("language"):
        row["language"] = labels.get("language", "")
    accent_key = str(row.get("accent", "") or labels.get("accent", "")).strip().lower()
    if not row.get("language") and row.get("locale"):
        row["language"] = str(row.get("locale")).split("-")[0]
    if not row.get("language") and accent_key:
        row["language"] = ACCENT_LANGUAGE_MAP.get(accent_key, "")
    if not row.get("locale") and isinstance(primary_verified_language, dict):
        row["locale"] = primary_verified_language.get("locale", "")
    if not row.get("accent") and isinstance(primary_verified_language, dict):
        row["accent"] = primary_verified_language.get("accent", "")
    if not row.get("language") and isinstance(primary_verified_language, dict):
        row["language"] = primary_verified_language.get("language", "")
    if not row.get("date_unix") and row.get("created_at_unix"):
        row["date_unix"] = row.get("created_at_unix")
    if not row.get("public_owner_id"):
        row["public_owner_id"] = sharing.get("public_owner_id", "")
    accent_key = str(row.get("accent", "")).strip().lower()
    if not row.get("locale") and accent_key:
        row["locale"] = ACCENT_LOCALE_MAP.get(accent_key, "")
    if not row.get("locale") and row.get("language"):
        row["locale"] = row.get("language")
    if not row.get("language"):
        row["language"] = "und"
    if not row.get("locale"):
        row["locale"] = "und"
    if not supported_model_ids:
        supported_model_ids = ["unknown"]
        if supported_model_source == "none":
            supported_model_source = "fallback_unknown"
        else:
            supported_model_source = f"{supported_model_source},fallback_unknown"
        row["supported_model_ids"] = supported_model_ids
        row["supported_model_count"] = len(supported_model_ids)
        row["supported_model_source"] = supported_model_source

    normalized_verified_languages = []
    for item in verified_languages:
        if not isinstance(item, dict):
            continue
        normalized_item = dict(item)
        if not normalized_item.get("model_id") and supported_model_ids:
            normalized_item["model_id"] = supported_model_ids[0]
        normalized_verified_languages.append(normalized_item)
    verified_languages = normalized_verified_languages

    if not verified_languages:
        high_quality_base_model_ids = (
            row.get("high_quality_base_model_ids")
            if isinstance(row.get("high_quality_base_model_ids"), list)
            else []
        )
        fallback_model_id = supported_model_ids[0] if supported_model_ids else ""
        fallback_verified_language = {
            "language": row.get("language", ""),
            "locale": row.get("locale", ""),
            "accent": row.get("accent", ""),
            "model_id": fallback_model_id or (high_quality_base_model_ids[0] if high_quality_base_model_ids else ""),
            "preview_url": row.get("preview_url", ""),
        }
        row["verified_languages"] = [fallback_verified_language]
    else:
        row["verified_languages"] = verified_languages

    for key in ("public_owner_id", "date_unix", "accent", "gender", "age", "use_case", "language", "locale"):
        if key not in row:
            row[key] = ""

    for key, value in list(row.items()):
        if isinstance(value, (dict, list)):
            row[key] = json.dumps(value, ensure_ascii=False)
        elif value is None:
            row[key] = ""
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
