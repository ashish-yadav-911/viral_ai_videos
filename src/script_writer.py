# src/script_writer.py
import os
from .config_manager import manager as config
from .database_manager import DatabaseManager
from .llm_service import LLMService
from .utils import slugify

class ScriptWriter:
    """Handles generating script, saving it, and updating DB status."""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.llm_service = LLMService()
        self.assets_dir = config.get('ASSETS_DIR')
        print("ScriptWriter initialized.")

    def process_topic(self, topic_name):
        """
        Generates and saves script for a topic, updates DB status to PENDING_ASSETS.
        Returns True on success, False on failure.
        """
        print(f"Processing topic for script generation: '{topic_name}'")

        # 1. Verify Topic Status (optional but good practice)
        details = self.db_manager.get_topic_details(topic_name)
        if not details:
            print(f"ERROR: Topic '{topic_name}' not found in database.")
            return False

        current_status = details.get('pipeline_status')

        # --- MODIFIED STATUS CHECK ---
        # Allow processing if PENDING_SCRIPT or FAILED (for retry)
        allowed_statuses = ['PENDING_SCRIPT', 'FAILED']
        if current_status not in allowed_statuses:
             print(f"Warning: Topic '{topic_name}' status is '{current_status}'. Skipping script generation (requires {allowed_statuses}).")
             return False # Skip if not in an allowed starting state
        elif current_status == 'FAILED':
            print(f"Info: Retrying script generation for FAILED topic '{topic_name}'.")

        # 2. Generate Script using LLM
        try:
            script_content = self.llm_service.generate_script(topic_name)
            if not script_content:
                # LLM Service already printed an error if generation failed structurally
                print(f"ERROR: Failed to generate valid script content for '{topic_name}'.")
                self.db_manager.update_status(topic_name, 'FAILED', last_error="Script generation failed (LLM Error)")
                return False
        except Exception as e:
            print(f"ERROR: Exception during LLM script generation for '{topic_name}': {e}")
            self.db_manager.update_status(topic_name, 'FAILED', last_error=f"Script generation failed: {e}")
            return False

        # 3. Create Slug & Asset Path
        topic_slug = slugify(topic_name)
        script_dir = os.path.join(self.assets_dir, topic_slug)
        script_path = os.path.join(script_dir, 'script.txt')

        # 4. Save the Script File
        try:
            os.makedirs(script_dir, exist_ok=True)
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            print(f"Saved generated script to: {script_path}")
        except OSError as e:
            print(f"ERROR: Failed to save script file to {script_path}: {e}")
            self.db_manager.update_status(topic_name, 'FAILED', last_error=f"Failed to save script file: {e}")
            return False

        # 5. Update Database Status
        success = self.db_manager.update_status(
            topic=topic_name,
            status='PENDING_ASSETS',
            generated_script_path=script_path, # Store the path
            last_error='' # Clear any previous error
        )

        if success:
            print(f"Successfully processed script for '{topic_name}'. Status updated to PENDING_ASSETS.")
            return True
        else:
            print(f"ERROR: Failed to update database status for '{topic_name}' after saving script.")
            # The script is saved, but DB is inconsistent. Maybe mark as FAILED?
            self.db_manager.update_status(topic_name, 'FAILED', last_error="DB status update failed after script save")
            return False