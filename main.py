import os

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play

# Initialize env variables from .env
load_dotenv()
ELEVEN_LABS_API_KEY = os.getenv("ELEVEN_LABS_API_KEY")

# TTS Options
MODEL_ID = "eleven_v3"
VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
OUTPUT_FORMAT = "mp3_44100_128"


def init_elevenlabs_instance():
    """
    Initialize ElevenLabs instance with API Key
    """
    return ElevenLabs(api_key=ELEVEN_LABS_API_KEY)


def print_voice_info(instance: ElevenLabs):
    """
    Retrieve voice info from API, and print it
    """
    # Get voice info
    voice_info = instance.voices.get(voice_id=VOICE_ID)

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


def main():
    """
    Main function
    """
    # Init elevenlabs instance
    instance = init_elevenlabs_instance()

    # Print voice info
    print_voice_info(instance)

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
                voice_id=VOICE_ID,
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