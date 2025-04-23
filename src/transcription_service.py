# src/transcription_service.py
import openai
import os
import time
from .config_manager import manager as config

class TranscriptionService:
    """Handles audio transcription using OpenAI Whisper."""

    def __init__(self):
        self.api_key = config.get('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not configured in .env.")
        self.client = openai.OpenAI(api_key=self.api_key)
        self.model = config.get('OPENAI_WHISPER_MODEL', 'whisper-1')
        print(f"TranscriptionService initialized with model: {self.model}")

    def transcribe_audio(self, audio_file_path):
        """
        Transcribes the given audio file.
        Returns the transcription text or None if an error occurs.
        """
        if not os.path.exists(audio_file_path):
            print(f"ERROR: Audio file not found at {audio_file_path}")
            return None

        print(f"Starting transcription for {audio_file_path} using {self.model}...")
        start_time = time.time()
        try:
            with open(audio_file_path, "rb") as audio_file:
                # Ensure the file object is passed correctly
                transcript_response = self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file # Pass the file object directly
                    # language="en" # Optional: Specify language
                    # response_format="text" # Default is json, 'text' is simpler if only text needed
                )

            duration = time.time() - start_time
            # Access the text attribute from the response object
            transcribed_text = transcript_response.text
            print(f"Transcription completed in {duration:.2f} seconds. Length: {len(transcribed_text)} chars.")
            return transcribed_text

        except openai.AuthenticationError as e:
             print(f"ERROR: OpenAI Whisper Authentication Failed. {e}")
             return None
        except openai.RateLimitError as e:
            print(f"ERROR: OpenAI Whisper Rate Limit Exceeded. {e}")
            return None
        except openai.APIConnectionError as e:
            print(f"ERROR: OpenAI Whisper API Connection Error: {e}")
            return None
        except Exception as e:
            print(f"ERROR: An unexpected error occurred during transcription: {e}")
            return None