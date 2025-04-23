# src/asset_generator.py (Complete File - Ensure this is correct)
import os
import requests
import time
import math

# Import TTS SDKs
# from cartesia import Cartesia # Temporarily disabled Cartesia client usage
from deepgram import DeepgramClient, SpeakOptions

from .config_manager import manager as config
from .database_manager import DatabaseManager
from .llm_service import LLMService
from .utils import slugify

class AssetGenerator:
    """Handles generating voiceover and visuals (images/videos) for a topic."""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.llm_service = LLMService()
        self.assets_dir = config.get('ASSETS_DIR')

        # TTS Settings
        self.tts_provider_priority = config.get('TTS_PROVIDER_PRIORITY', [])
        self.elevenlabs_api_key = config.get('ELEVENLABS_API_KEY')
        # self.cartesia_api_key = config.get('CARTESIA_API_KEY') # Key still loaded, but client not used
        self.deepgram_api_key = config.get('DEEPGRAM_API_KEY')

        # Specific TTS Configs
        self.default_voice_id_elevenlabs = config.get('DEFAULT_VOICE_ID_ELEVENLABS')
        # self.default_model_id_cartesia = config.get('DEFAULT_MODEL_ID_CARTESIA') # Not used
        # self.default_voice_name_cartesia = config.get('DEFAULT_VOICE_NAME_CARTESIA') # Not used
        self.default_model_id_deepgram = config.get('DEFAULT_MODEL_ID_DEEPGRAM')

        # Pexels/DALL-E Settings
        self.pexels_api_key = config.get('PEXELS_API_KEY')
        self.target_visuals = config.get('IMAGES_PER_SCRIPT', 8)
        self.dalle_image_size = config.get('IMAGE_SIZE', "1024x1024")

        # Initialize TTS Clients if keys exist
        # self.cartesia_client = Cartesia(api_key=self.cartesia_api_key) if self.cartesia_api_key else None # Disabled
        self.deepgram_client = DeepgramClient(self.deepgram_api_key) if self.deepgram_api_key else None

        print("AssetGenerator initialized.")
        print(f"TTS Provider Priority: {self.tts_provider_priority}")


    def _download_file(self, url, save_path):
        """Downloads a file from a URL to a specified path."""
        try:
            print(f"Downloading from {url} to {save_path}...")
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192): f.write(chunk)
            print("Download successful.")
            return True
        except requests.exceptions.RequestException as e:
            print(f"ERROR: Failed to download {url}: {e}")
            if os.path.exists(save_path):
                 try: os.remove(save_path); print(f"Cleaned up partial file: {save_path}")
                 except OSError: pass
            return False


    # --- TTS Generation Methods ---

    def _generate_elevenlabs_vo(self, script_text, output_path):
        """Generates voiceover using ElevenLabs API."""
        if not self.elevenlabs_api_key: print("INFO: ElevenLabs API key not configured."); return False
        if not self.default_voice_id_elevenlabs: print("ERROR: ElevenLabs DEFAULT_VOICE_ID not set in config/.env."); return False

        voice_id = self.default_voice_id_elevenlabs
        api_endpoint = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": self.elevenlabs_api_key}
        data = {"text": script_text, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
        print(f"Requesting voiceover from ElevenLabs (Voice ID: {voice_id})...")
        try:
            response = requests.post(api_endpoint, json=data, headers=headers, timeout=180)
            if response.status_code == 200:
                with open(output_path, 'wb') as f: f.write(response.content)
                print(f"Successfully saved ElevenLabs voiceover to {output_path}")
                return True
            else:
                print(f"ERROR: ElevenLabs API failed. Status: {response.status_code}, Response: {response.text[:200]}")
                return False
        except requests.exceptions.RequestException as e: print(f"ERROR: Failed to call ElevenLabs API: {e}"); return False


    def _generate_cartesia_vo(self, script_text, output_path):
        """Generates voiceover using Cartesia API. (Currently Disabled Stub)"""
        print("INFO: Cartesia TTS generation is temporarily disabled.")
        # This method needs correct SDK implementation based on docs
        # if not self.cartesia_client:
        #     print("INFO: Cartesia client not initialized.")
        #     return False
        # try:
        #     # --- Correct Cartesia Call Would Go Here ---
        #     print(f"Requesting voiceover from Cartesia...")
        #     # audio_chunks = self.cartesia_client.tts(...) # Get audio bytes/stream
        #     # with open(output_path, "wb") as f: ... # Write bytes to file
        #     print("ERROR: Cartesia SDK call not implemented correctly yet.")
        #     return False
        # except Exception as e:
        #     print(f"ERROR: Failed during Cartesia TTS generation stub: {e}")
        return False


    def _generate_deepgram_vo(self, script_text, output_path):
        """Generates voiceover using Deepgram Aura API."""
        if not self.deepgram_client: print("INFO: Deepgram client not initialized."); return False

        DEEPGRAM_CHAR_LIMIT = 2000
        if len(script_text) > DEEPGRAM_CHAR_LIMIT:
            print(f"WARNING: Script text ({len(script_text)} chars) exceeds Deepgram limit ({DEEPGRAM_CHAR_LIMIT}). Truncating.")
            truncated_text = script_text[:DEEPGRAM_CHAR_LIMIT]
            last_period = truncated_text.rfind('.')
            script_text_to_send = truncated_text[:last_period + 1] if last_period != -1 else truncated_text
            print(f"Truncated script length: {len(script_text_to_send)} chars.")
        else:
            script_text_to_send = script_text

        model = self.default_model_id_deepgram
        source = {"text": script_text_to_send}
        options = SpeakOptions(model=model)

        print(f"Requesting voiceover from Deepgram Aura (Model: {model})...")
        try:
            start_time = time.time()
            response = self.deepgram_client.speak.v("1").save(output_path, source, options)
            duration = time.time() - start_time
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                 print(f"Successfully saved Deepgram voiceover to {output_path} in {duration:.2f}s")
                 return True
            else:
                 print(f"ERROR: Deepgram TTS call finished but output file missing/empty ({output_path}). Resp: {response}")
                 if os.path.exists(output_path): os.remove(output_path)
                 return False
        except ImportError: print("ERROR: Deepgram SDK not installed correctly."); return False
        except Exception as e: print(f"ERROR: Failed during Deepgram TTS generation: {e}"); return False


    def _generate_voiceover(self, script_text, output_path):
        """Generates voiceover using configured TTS providers based on priority."""
        print("\n--- Generating Voiceover (Attempting Providers by Priority) ---")
        for provider in self.tts_provider_priority:
            print(f"--- Attempting TTS Provider: {provider} ---")
            success = False
            temp_output_path = os.path.splitext(output_path)[0] + f".{provider}.tmp" # Use temp file

            if provider == 'cartesia':
                success = self._generate_cartesia_vo(script_text, temp_output_path)
            elif provider == 'deepgram':
                 success = self._generate_deepgram_vo(script_text, temp_output_path)
            elif provider == 'elevenlabs':
                 success = self._generate_elevenlabs_vo(script_text, temp_output_path)
            else:
                 print(f"Warning: Unknown TTS provider in priority list: {provider}")

            if success:
                 print(f"--- Successfully generated voiceover using: {provider} ---")
                 # Rename temp file to final output path
                 try:
                     os.rename(temp_output_path, output_path)
                     print(f"Final voiceover file: {output_path}")
                     return True
                 except OSError as e:
                      print(f"ERROR: Failed to rename temp TTS file {temp_output_path} to {output_path}: {e}")
                      # Try to clean up temp file
                      if os.path.exists(temp_output_path): os.remove(temp_output_path)
                      return False # Treat rename failure as overall failure

            print(f"--- Failed or skipped TTS provider: {provider}. Trying next... ---")
            # Clean up failed temp file
            if os.path.exists(temp_output_path):
                 try: os.remove(temp_output_path)
                 except OSError: pass
            time.sleep(1)

        print("--- ERROR: All configured TTS providers failed. ---")
        return False # All providers failed
    
    def _search_pexels_videos(self, query, per_page=1):
        """Searches Pexels API for videos."""
        if not self.pexels_api_key:
            print("Info: Pexels API key not configured. Skipping Pexels search.")
            return []

        api_endpoint = "https://api.pexels.com/videos/search"
        headers = {"Authorization": self.pexels_api_key}
        params = {
            "query": query,
            "per_page": per_page,
            "orientation": "landscape"
        }
        print(f"Searching Pexels for videos matching query: '{query}'...")
        try:
            response = requests.get(api_endpoint, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            videos = data.get('videos', [])
            print(f"Pexels search found {len(videos)} videos.")

            video_links = []
            for video in videos:
                link = None
                for vf in video.get('video_files', []):
                    if vf.get('quality') == 'hd' and vf.get('link'):
                        link = vf['link']; break
                if not link and video.get('video_files'):
                    link = video['video_files'][0].get('link')
                if link: video_links.append(link)

            return video_links

        except requests.exceptions.RequestException as e:
            print(f"ERROR: Failed to call Pexels API: {e}")
            return []
        except Exception as e:
            print(f"ERROR: Unexpected error during Pexels search: {e}")
            return []


    # --- Visual Generation Method ---
    # <<< ENSURE THIS METHOD IS CORRECTLY DEFINED >>>
    def _generate_visuals(self, script_text, visuals_dir, image_style):
        """Generates images (DALL-E) and tries to find videos (Pexels)."""
        print("Generating visuals...")
        os.makedirs(visuals_dir, exist_ok=True)
        generated_visual_paths = []

        script_segments = [s.strip() for s in script_text.split('.') if len(s.strip()) > 10]
        if not script_segments: script_segments = [s.strip() for s in script_text.splitlines() if len(s.strip()) > 10]
        if not script_segments: script_segments = [script_text]

        num_segments = len(script_segments)
        visuals_needed = self.target_visuals
        print(f"Targeting {visuals_needed} visuals based on {num_segments} script segments.")

        segment_index = 0
        visual_count = 0
        max_retries_per_visual = 2

        while visual_count < visuals_needed and segment_index < num_segments * max_retries_per_visual :
            current_segment = script_segments[segment_index % num_segments]
            visual_filename_base = f"visual_{visual_count + 1:02d}"
            print(f"\n--- Attempting visual {visual_count + 1}/{visuals_needed} for segment: '{current_segment[:50]}...' ---")

            found_visual = False
            retry_count = 0 # Reset retry count for each visual attempt

            # Try Pexels first if key exists (only on first try for a segment number)
            if self.pexels_api_key and (segment_index < num_segments): # Try Pexels only on the first pass
                query = current_segment[:50]
                pexels_videos = self._search_pexels_videos(query, per_page=1)
                if pexels_videos:
                    video_url = pexels_videos[0]
                    file_extension = os.path.splitext(video_url.split('?')[0])[-1] or ".mp4"
                    save_path = os.path.join(visuals_dir, visual_filename_base + file_extension)
                    if self._download_file(video_url, save_path):
                        generated_visual_paths.append(save_path)
                        visual_count += 1
                        found_visual = True
                    else: print("Warning: Failed to download Pexels video.")
                else: print("Info: No suitable Pexels video found for this segment.")

            # Fallback/Alternative: DALL-E Image
            if not found_visual:
                 print("Attempting DALL-E image generation...")
                 try:
                     dalle_prompt = f"{image_style} scene illustrating: {current_segment[:150]}"
                     image_urls = self.llm_service.generate_images(prompt=dalle_prompt, n=1, size=self.dalle_image_size)
                     if image_urls:
                         image_url = image_urls[0]
                         save_path = os.path.join(visuals_dir, visual_filename_base + ".jpg")
                         if self._download_file(image_url, save_path):
                             generated_visual_paths.append(save_path)
                             visual_count += 1
                             found_visual = True
                         else: print("Warning: Failed to download DALL-E image.")
                     else: print("Warning: DALL-E did not return image URLs.")
                 except Exception as e:
                     print(f"ERROR: Failed during DALL-E generation/download: {e}")


            segment_index += 1 # Always advance segment index
            if not found_visual:
                retry_count = (segment_index // num_segments) # Calculate retries based on cycles
                if retry_count < max_retries_per_visual:
                     print(f"Retrying visual generation (Cycle {retry_count + 1})...")
                     time.sleep(2)
                else:
                     # Stop trying for this specific visual number if max retries hit
                     print(f"Warning: Max retries reached for visual {visual_count + 1}. Moving on to request next visual.")
                     # How to advance? We need to ensure visual_count loop terminates.
                     # If we are stuck, let's just break the loop or increment segment enough to stop soon.
                     # This logic needs careful thought to avoid infinite loops AND get enough visuals.
                     # For now, let's just let the outer loop condition handle termination.
                     pass


        print(f"\nVisual generation finished. Acquired {len(generated_visual_paths)} visuals.")
        # Return None if generation failed badly, or the list otherwise
        if not generated_visual_paths and visuals_needed > 0:
             return None
        return generated_visual_paths


    # --- Main Processing Method ---
    def process_topic(self, topic_name):
        """Generates assets (voiceover, visuals) for a topic, updates DB status."""
        print(f"\n===== Starting Asset Generation for: '{topic_name}' =====")
        details = self.db_manager.get_topic_details(topic_name)

        if not details: print(f"ERROR: Topic '{topic_name}' not found."); return False
        if details.get('pipeline_status') != 'PENDING_ASSETS': print(f"Warning: Topic '{topic_name}' not PENDING_ASSETS. Skipping."); return False
        script_path = details.get('generated_script_path')
        if not script_path or not os.path.exists(script_path):
            print(f"ERROR: Script path '{script_path}' invalid for topic '{topic_name}'.")
            self.db_manager.update_status(topic_name, 'FAILED', last_error="Script file missing/invalid"); return False

        topic_slug = slugify(topic_name)
        topic_assets_dir = os.path.join(self.assets_dir, topic_slug)
        visuals_dir = os.path.join(topic_assets_dir, 'visuals')
        voiceover_path = os.path.join(topic_assets_dir, 'voiceover.mp3')
        os.makedirs(topic_assets_dir, exist_ok=True); os.makedirs(visuals_dir, exist_ok=True)

        try:
            with open(script_path, 'r', encoding='utf-8') as f: script_content = f.read()
        except Exception as e:
            print(f"ERROR: Failed to read script {script_path}: {e}")
            self.db_manager.update_status(topic_name, 'FAILED', last_error=f"Failed read script: {e}"); return False

        # Generate Voiceover
        vo_success = self._generate_voiceover(script_content, voiceover_path)
        if not vo_success:
            print("ERROR: Voiceover generation failed."); self.db_manager.update_status(topic_name, 'FAILED', last_error="Voiceover gen failed"); return False

        # Generate Visuals
        # <<< ENSURE THIS CALL IS CORRECT >>>
        image_style = config.get('DEFAULT_IMAGE_STYLE')
        visual_paths = self._generate_visuals(script_content, visuals_dir, image_style) # <<< CHECK THIS LINE CAREFULLY

        # Check Visuals
        if visual_paths is None: # Indicates internal failure in _generate_visuals
            print(f"ERROR: Visual generation failed internally.")
            self.db_manager.update_status(topic_name, 'FAILED', last_error="Visual generation failed"); return False
        elif len(visual_paths) < math.ceil(self.target_visuals * 0.75): # Check if enough were generated
             print(f"ERROR: Insufficient visuals ({len(visual_paths)}/{self.target_visuals}).")
             self.db_manager.update_status(topic_name, 'FAILED', last_error=f"Insufficient visuals ({len(visual_paths)}/{self.target_visuals})"); return False
        else:
            print(f"Successfully generated {len(visual_paths)} visuals.")


        # Update Database
        print("\n--- Finalizing Asset Generation ---")
        final_status = 'PENDING_EDIT'
        success = self.db_manager.update_status(topic=topic_name, status=final_status, last_error='')
        if success:
            print(f"===== Asset Generation SUCCESS for '{topic_name}'. Status set to {final_status}. ====="); return True
        else:
             print(f"ERROR: Failed to update DB status after asset gen.")
             self.db_manager.update_status(topic_name, 'FAILED', last_error="DB update fail after asset gen"); return False # Set final status to FAILED