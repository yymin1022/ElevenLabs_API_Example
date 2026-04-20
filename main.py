import os

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play

# Initialize env variables from .env
load_dotenv()
ELEVEN_LABS_API_KEY = os.getenv("ELEVEN_LABS_API_KEY")

# TTS Options
MODEL_ID = "eleven_v3"
OUTPUT_FORMAT = "mp3_44100_128"
VOICE_LIST_LIMIT = 200
VOICE_PAGE_SIZE = 100


def init_elevenlabs_instance():
    """
    Initialize ElevenLabs instance with API Key
    """
    return ElevenLabs(api_key=ELEVEN_LABS_API_KEY)


def print_voice_info(instance: ElevenLabs, voice_id: str):
    """
    Retrieve voice info from API, and print it
    """
    # Get voice info
    voice_info = instance.voices.get(voice_id=voice_id)

    # Print info as formatted text
    print(
        f"""
Current voice info
Name: {voice_info.name}
Category: {voice_info.category}
Description: {voice_info.description}
Labels: {voice_info.labels}
Verified Languages: {voice_info.verified_languages}
        """
    )


def get_popular_voices(instance: ElevenLabs):
    """
    Retrieve top shared voices sorted by usage in the last 7 days
    """
    voices_by_id = {}
    page = 0

    while len(voices_by_id) < VOICE_LIST_LIMIT:
        remaining = VOICE_LIST_LIMIT - len(voices_by_id)
        page_size = min(VOICE_PAGE_SIZE, remaining)
        response = instance.voices.get_shared(
            page_size=page_size,
            page=page,
        )

        if not response.voices:
            break

        for voice in response.voices:
            voices_by_id.setdefault(voice.voice_id, voice)

        if not response.has_more:
            break
        page += 1

    voices = list(voices_by_id.values())

    voices.sort(
        key=lambda voice: getattr(voice, "usage_character_count_7_d", 0) or 0,
        reverse=True,
    )
    return voices[:VOICE_LIST_LIMIT]


def select_voice(instance: ElevenLabs):
    """
    Retrieve voices sorted by popularity and select one by index from CLI input
    """
    voices = get_popular_voices(instance)
    if not voices:
        print("No voice is available.")
        return None

    print(f"Available voices (Top {len(voices)} by usage in last 7 days):")
    for idx, voice in enumerate(voices, start=1):
        usage_7d = getattr(voice, "usage_character_count_7_d", 0) or 0
        print(f"{idx}. {voice.name} ({voice.voice_id}) - {usage_7d:,} chars/7d")

    while True:
        selected = input("Select voice number (or press Enter to exit): ").strip()
        if not selected:
            return None

        if not selected.isdigit():
            print("Please enter a valid number.")
            continue

        voice_index = int(selected) - 1
        if voice_index < 0 or voice_index >= len(voices):
            print("Selected number is out of range.")
            continue

        return voices[voice_index]


def main():
    """
    Main function
    """
    # Init elevenlabs instance
    instance = init_elevenlabs_instance()

    # Select voice
    selected_voice = select_voice(instance)
    if selected_voice is None:
        print("Exit...")
        return

    # Print voice info
    print_voice_info(instance, selected_voice.voice_id)

    try:
        while True:
            # Get text from input
            text = input("Enter: ").strip()

            # Exit if text is empty
            if not text:
                break

            # Process TTS converting
            audio = instance.text_to_speech.convert(
                text=text,
                voice_id=selected_voice.voice_id,
                model_id=MODEL_ID,
                output_format=OUTPUT_FORMAT,
            )

            # Play converted audio
            play(audio)
    except KeyboardInterrupt:
        # Exit when Ctrl + C
        pass
    finally:
        print("Exit...")


if __name__ == "__main__":
    main()
