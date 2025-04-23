# src/input_processor.py
import os
import subprocess
import time
from .config_manager import manager as config
from .transcription_service import TranscriptionService
from .llm_service import LLMService # Needed for analyzing sample scripts

class InputProcessor:
    """Handles processing different user inputs to get text content."""

    def __init__(self):
        self.transcription_service = TranscriptionService()
        self.llm_service = LLMService() # Needed for script analysis
        self.download_dir = os.path.join(config.get('ASSETS_DIR'), '_downloads')
        os.makedirs(self.download_dir, exist_ok=True)
        print(f"InputProcessor initialized. Download dir: {self.download_dir}")

    def _download_youtube_audio(self, url):
        """Downloads audio from YouTube URL using yt-dlp."""
        timestamp = int(time.time())
        output_template = os.path.join(self.download_dir, f"youtube_{timestamp}.%(ext)s")
        # Use 'bestaudio/best' and specify audio format like mp3
        command = [
            'yt-dlp',
            '-x', # Extract audio
            '--audio-format', 'mp3',
            '--audio-quality', '0', # Best quality
            '-f', 'bestaudio/best', # Select best audio stream
            '-o', output_template,
            '--no-playlist', # Download only single video if URL is part of playlist
            '--socket-timeout', '30', # Timeout for connection
            url
        ]
        print(f"Executing yt-dlp command: {' '.join(command)}")
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=300) # 5 min timeout
            print("yt-dlp stdout:", result.stdout)
            print("yt-dlp stderr:", result.stderr)

            # Find the actual downloaded file name (yt-dlp replaces %(ext)s)
            # Assuming only one file is downloaded per run here
            downloaded_files = [f for f in os.listdir(self.download_dir) if f.startswith(f"youtube_{timestamp}")]
            if downloaded_files:
                filepath = os.path.join(self.download_dir, downloaded_files[0])
                print(f"Successfully downloaded audio to: {filepath}")
                return filepath
            else:
                 print("ERROR: yt-dlp ran but could not find downloaded file.")
                 return None

        except FileNotFoundError:
            print("ERROR: 'yt-dlp' command not found. Is it installed and in PATH?")
            return None
        except subprocess.CalledProcessError as e:
            print(f"ERROR: yt-dlp failed with exit code {e.returncode}")
            print("yt-dlp stderr:", e.stderr)
            return None
        except subprocess.TimeoutExpired:
             print("ERROR: yt-dlp download timed out.")
             return None
        except Exception as e:
            print(f"ERROR: An unexpected error occurred during download: {e}")
            return None

    def process_input(self, input_data, input_type):
        """
        Processes the input based on its type.
        Returns the extracted text content or None on failure.
        Input types: 'script', 'samples', 'url', 'audio_path'
        """
        print(f"Processing input type: {input_type}")
        text_content = None

        if input_type == 'script':
            if isinstance(input_data, str) and len(input_data) > 10: # Basic check
                 print("Processing direct script input.")
                 text_content = input_data
            else:
                 print("ERROR: Invalid script input provided.")
                 return None

        elif input_type == 'samples':
            if isinstance(input_data, list) and all(isinstance(s, str) for s in input_data):
                print(f"Processing {len(input_data)} sample scripts.")
                # Combine samples or analyze theme - For topic generation, just combining is often enough
                combined_samples = "\n---\n".join(input_data)
                # Optional: Use LLM to summarize themes first
                # theme_prompt = f"Summarize the main themes and style of these script samples:\n\n{combined_samples[:4000]}"
                # themes = self.llm_service._call_gpt([{"role":"user", "content": theme_prompt}], max_tokens=300)
                # text_content = themes if themes else combined_samples # Use themes if successful
                text_content = combined_samples # Keep it simple for now
            else:
                print("ERROR: Invalid sample scripts input. Expected list of strings.")
                return None

        elif input_type == 'url':
            if isinstance(input_data, str) and input_data.startswith(('http://', 'https://')):
                print(f"Processing URL input: {input_data}")
                audio_path = self._download_youtube_audio(input_data)
                if audio_path:
                    text_content = self.transcription_service.transcribe_audio(audio_path)
                    # Optional: Clean up downloaded file after transcription
                    # try:
                    #     os.remove(audio_path)
                    #     print(f"Cleaned up downloaded file: {audio_path}")
                    # except OSError as e:
                    #     print(f"Warning: Could not delete downloaded file {audio_path}: {e}")
                else:
                    print("ERROR: Failed to download or find audio from URL.")
                    return None
            else:
                 print("ERROR: Invalid URL input provided.")
                 return None

        elif input_type == 'audio_path':
             if isinstance(input_data, str) and os.path.exists(input_data):
                 print(f"Processing audio file input: {input_data}")
                 text_content = self.transcription_service.transcribe_audio(input_data)
             else:
                  print(f"ERROR: Audio file not found or invalid path: {input_data}")
                  return None
        else:
            print(f"ERROR: Unknown input type: {input_type}")
            return None

        if text_content:
            print(f"Successfully processed input. Extracted text length: {len(text_content)} chars.")
            return text_content
        else:
            print("ERROR: Failed to extract text content from input.")
            return None