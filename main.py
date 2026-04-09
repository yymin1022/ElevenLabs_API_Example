import os

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

# Initialize env variables from .env
load_dotenv()
ELEVEN_LABS_API_KEY = os.getenv("ELEVEN_LABS_API_KEY")


def init_elevenlabs_instance():
    """
    Initialize ElevenLabs instance with API Key
    """
    return ElevenLabs(api_key=ELEVEN_LABS_API_KEY)


def main():
    """
    Main function
    """
    # Init elevenlabs instance
    instance = init_elevenlabs_instance()


if __name__ == "__main__":
    main()