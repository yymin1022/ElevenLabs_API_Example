import os

from dotenv import load_dotenv

# Initialize env variables from .env
load_dotenv()
ELEVEN_LABS_API_KEY = os.getenv("ELEVEN_LABS_API_KEY")


def main():
    """
    Main function
    """
    print("Hello, World!")


if __name__ == "__main__":
    main()