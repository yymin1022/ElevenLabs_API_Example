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


def select_voice(instance: ElevenLabs):
    """
    Retrieve available voices and select one by index from CLI input
    """
    voices = instance.voices.get_all().voices
    if not voices:
        print("No voice is available.")
        return None

    print("Available voices:")
    for idx, voice in enumerate(voices, start=1):
        print(f"{idx}. {voice.name} ({voice.voice_id})")

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
