
import os
import datetime
import subprocess
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash

# Import configuration and managers/services
from src.config_manager import manager as config
from src.database_manager import DatabaseManager 
from src.topic_generator import TopicGenerator
from src.script_writer import ScriptWriter
from src.asset_generator import AssetGenerator

# --- Initialize Flask App ---
app = Flask(__name__)
app.secret_key = config.get('FLASK_SECRET_KEY')

# --- Initialize Services ---
db_manager = None # VARIABLE NAME CHANGE
topic_generator = None
topic_generator = None
script_writer = None
# Initialize other managers to None initially
script_writer = None
asset_generator = None
video_editor = None
youtube_uploader = None
notification_manager = None
asset_generator = None

try:
    print("Initializing services...")
    db_manager = DatabaseManager()
    topic_generator = TopicGenerator()
    script_writer = ScriptWriter()
    # Initialize other managers here when their classes are ready
    asset_generator = AssetGenerator()
    # video_editor = VideoEditor()
    # youtube_uploader = YouTubeUploader()
    # notification_manager = NotificationManager()
    print("Services initialized successfully.")
except Exception as e:
    print(f"FATAL ERROR initializing core services: {e}")
    # Consider how the app should behave if core services fail
    # For now, routes will check if managers are available


# --- Helper Function to Pass Globals to Templates ---
@app.context_processor
def inject_global_vars():
    """Make config and other globals available in all templates."""
    return dict(
        config=config, # Pass the entire config manager instance
        now=datetime.datetime.utcnow(), # Pass current UTC time
        db_manager=db_manager # <<< EXPLICITLY ADD db_manager HERE
    )

# --- Routes ---
@app.route('/')
def index():
    video_data = []
    error_message = None

    if not db_manager: # CHECK CHANGE
        error_message = "Database Manager failed to initialize. Cannot load data."
    else:
        try:
            video_data = db_manager.get_all_videos_status() # METHOD CALL on new manager

            #             # -------- ADD THIS DEBUGGING BLOCK --------
            # print("\n" + "="*20 + " DEBUGGING video_data " + "="*20)
            # if isinstance(video_data, list):
            #     print(f"Type: list, Length: {len(video_data)}")
            #     for i, item in enumerate(video_data):
            #         print(f"Item {i}: Type={type(item)}, Value={item}")
            #         # If item is a dict, check keys
            #         if isinstance(item, dict):
            #              print(f"    Keys: {list(item.keys())}")
            #         elif item is None:
            #              print(f"    WARNING: Item {i} is None!")
            # else:
            #     print(f"Type: {type(video_data)}, Value: {video_data}")
            # print("="*58 + "\n")
            # # -------- END DEBUGGING BLOCK --------

        except Exception as e:
            print(f"Error fetching data from Database in index route: {e}")
            flash(f"Error connecting or fetching data from Database: {e}", "warning")

    return render_template('index.html', videos=video_data, error=error_message)

# --- Action Routes ---

@app.route('/trigger/topics', methods=['POST'])
def trigger_topic_generation():
    if not topic_generator or not db_manager: # CHECK CHANGE (db_manager)
        flash("Core services (Topic Generator or Database Manager) are not available.", "danger")
        return redirect(url_for('index'))

    # --- Get input from form ---
    input_type = request.form.get('topic_input_type')
    input_text = request.form.get('topic_input_text')
    try:
        num_topics = int(request.form.get('num_topics', 10))
        if not (1 <= num_topics <= 50): # Add some reasonable limit
            flash("Number of topics must be between 1 and 50.", "warning")
            return redirect(url_for('index'))
    except ValueError:
        flash("Invalid number of topics specified.", "warning")
        return redirect(url_for('index'))


    print(f"Received topic generation request. Type: {input_type}, Num: {num_topics}")
    # print(f"Input Text/URL: {input_text[:100]}...") # Avoid logging potentially large scripts

    input_data = None
    if not input_text or not input_text.strip():
        flash("Input Text/URL cannot be empty.", "warning")
        return redirect(url_for('index'))

    if input_type == 'script' or input_type == 'url':
        input_data = input_text.strip()
    elif input_type == 'samples':
         # Assume samples are provided in the 'topic_input_text' textarea, separated by lines
         input_data = [line.strip() for line in input_text.strip().splitlines() if line.strip()]
         if not input_data:
             flash("No valid sample scripts found in the text area (ensure one sample per line).", "warning")
             return redirect(url_for('index'))
    # Add handling for file uploads ('audio_path') later if needed
    else:
        flash(f"Invalid input type specified: {input_type}", "danger")
        return redirect(url_for('index'))

    if not input_data:
         flash(f"Could not prepare input data for type '{input_type}'.", "warning")
         return redirect(url_for('index'))

    # --- Trigger Generation (Synchronous for V1) ---
    try:
        # This can take time - ideally run in background, but simple sequential for V1
        flash("Starting topic generation... This may take a moment.", "info") # Give user feedback
        # Force redirect and then process? No, let's wait for V1.

        added_topics = topic_generator.generate_and_store_topics(input_data, input_type, num_topics)

        if added_topics:
            flash(f"Successfully generated and added {len(added_topics)} topics!", "success")
        elif added_topics is None: # Indicates an error occurred during the process
             flash("Topic generation failed. Check console logs for details.", "danger")
        else: # Indicates process ran but no *new* topics were added (e.g., all duplicates)
             flash("Topic generation process completed, but no new topics were added (they might exist already).", "info")

    except Exception as e:
        print(f"ERROR during topic generation trigger: {e}")
        flash(f"An unexpected error occurred during topic generation: {e}", "danger")

    return redirect(url_for('index'))


# app.py (Updated trigger_process_next route)

@app.route('/trigger/process', methods=['POST'])
def trigger_process_next():
    """
    Processes the next videos in the pipeline with priority:
    1. Retries FAILED items (attempting script gen again).
    2. Processes PENDING_ASSETS items (generating assets).
    3. Processes PENDING_SCRIPT items (generating scripts).
    """
    num_to_process = config.get('VIDEOS_TO_GENERATE_PER_RUN', 2)
    print(f"\n>>> Triggering processing for next {num_to_process} videos (Priority: FAILED > PENDING_ASSETS > PENDING_SCRIPT) <<<")

    if not db_manager:
        flash("Database Manager service is not available.", "danger")
        print(">>> ERROR: db_manager not available.")
        return redirect(url_for('index'))

    processed_count = 0
    # --- Counters for different stages ---
    failed_retry_success_count = 0
    failed_retry_failure_count = 0
    asset_success_count = 0
    asset_failure_count = 0
    script_success_count = 0
    script_failure_count = 0

    # --- Priority 1: Retry FAILED ---
    print("\n--- [Priority 1] Checking for FAILED topics to retry ---")
    limit = num_to_process - processed_count
    if limit > 0 and script_writer: # Need script_writer to retry
        failed_topics = db_manager.find_topics_by_status('FAILED', limit=limit)
        print(f"--- [Priority 1] Found {len(failed_topics)} FAILED topics to retry: {failed_topics}")
        if failed_topics:
            for topic in failed_topics:
                if processed_count >= num_to_process: break # Check limit before processing
                print(f"\n--- [Priority 1] Retrying (as script gen) for FAILED topic: {topic} ---")
                processed_count += 1
                try:
                    # Treat FAILED retry as a fresh script generation attempt
                    success = script_writer.process_topic(topic)
                    if success:
                        failed_retry_success_count += 1
                        print(f"--- [Priority 1] SUCCESS retry for: {topic}")
                    else:
                        failed_retry_failure_count += 1
                        print(f"--- [Priority 1] FAILED retry for: {topic} (script_writer returned False)")
                except Exception as e:
                    failed_retry_failure_count += 1
                    print(f"--- [Priority 1] FAILED retry for: {topic} (Unhandled Exception: {e})")
                    # Update status back to FAILED if unexpected error
                    if db_manager: db_manager.update_status(topic, 'FAILED', last_error=f"Unhandled retry exception: {e}")
        else:
            print("--- [Priority 1] No FAILED topics found.")
    elif not script_writer:
         print("--- [Priority 1] Script Writer service unavailable, cannot retry FAILED items.")
    else:
         print("--- [Priority 1] Processing limit reached, skipping FAILED check.")


    # --- Priority 2: Process PENDING_ASSETS ---
    print("\n--- [Priority 2] Checking for PENDING_ASSETS topics ---")
    limit = num_to_process - processed_count
    if limit > 0 and asset_generator: # Need asset_generator
        asset_topics = db_manager.find_topics_by_status('PENDING_ASSETS', limit=limit)
        print(f"--- [Priority 2] Found {len(asset_topics)} PENDING_ASSETS topics: {asset_topics}")
        if asset_topics:
            for topic in asset_topics:
                 if processed_count >= num_to_process: break
                 print(f"\n--- [Priority 2] Processing assets for: {topic} ---")
                 processed_count += 1
                 try:
                     success = asset_generator.process_topic(topic)
                     if success:
                         asset_success_count += 1
                         print(f"--- [Priority 2] SUCCESS assets for: {topic}")
                     else:
                         asset_failure_count += 1
                         print(f"--- [Priority 2] FAILED assets for: {topic} (asset_generator returned False)")
                 except Exception as e:
                     asset_failure_count += 1
                     print(f"--- [Priority 2] FAILED assets for: {topic} (Unhandled Exception: {e})")
                     if db_manager: db_manager.update_status(topic, 'FAILED', last_error=f"Unhandled asset exception: {e}")
        else:
            print("--- [Priority 2] No PENDING_ASSETS topics found.")
    elif not asset_generator:
        print("--- [Priority 2] Asset Generator service unavailable, cannot process PENDING_ASSETS items.")
    else:
        print("--- [Priority 2] Processing limit reached, skipping PENDING_ASSETS check.")


    # --- Priority 3: Process PENDING_SCRIPT ---
    print("\n--- [Priority 3] Checking for PENDING_SCRIPT topics ---")
    limit = num_to_process - processed_count
    if limit > 0 and script_writer: # Need script_writer
        script_topics = db_manager.find_topics_by_status('PENDING_SCRIPT', limit=limit)
        print(f"--- [Priority 3] Found {len(script_topics)} PENDING_SCRIPT topics: {script_topics}")
        if script_topics:
            for topic in script_topics:
                if processed_count >= num_to_process: break
                print(f"\n--- [Priority 3] Processing script for: {topic} ---")
                processed_count += 1
                try:
                    success = script_writer.process_topic(topic)
                    if success:
                        script_success_count += 1
                        print(f"--- [Priority 3] SUCCESS script for: {topic}")
                    else:
                        script_failure_count += 1
                        print(f"--- [Priority 3] FAILED script for: {topic} (script_writer returned False)")
                except Exception as e:
                    script_failure_count += 1
                    print(f"--- [Priority 3] FAILED script for: {topic} (Unhandled Exception: {e})")
                    if db_manager: db_manager.update_status(topic, 'FAILED', last_error=f"Unhandled script exception: {e}")
        else:
            print("--- [Priority 3] No PENDING_SCRIPT topics found.")
    elif not script_writer:
        print("--- [Priority 3] Script Writer service unavailable, cannot process PENDING_SCRIPT items.")
    else:
        print("--- [Priority 3] Processing limit reached, skipping PENDING_SCRIPT check.")


    # --- Report Summary ---
    total_failed = failed_retry_failure_count + asset_failure_count + script_failure_count
    total_success = failed_retry_success_count + asset_success_count + script_success_count
    final_summary = (f"Processing run complete (Processed {processed_count}/{num_to_process} max). "
                     f"Retried FAILED: {failed_retry_success_count} success, {failed_retry_failure_count} failed. "
                     f"Assets: {asset_success_count} success, {asset_failure_count} failed. "
                     f"Scripts: {script_success_count} success, {script_failure_count} failed.")

    print(f"\n>>> {final_summary} <<<")
    if total_failed > 0:
        flash(f"{final_summary} Check logs for error details.", "warning")
    elif total_success > 0:
         flash(final_summary, "success")
    else:
         flash("No pending items found to process in this run.", "info")

    return redirect(url_for('index'))


@app.route('/trigger/orchestrator', methods=['POST'])
def trigger_orchestrator():
    if not db_manager: # CHECK CHANGE
         flash("Database service is not available.", "danger")
         return redirect(url_for('index'))
    # TODO: Execute the logic currently planned for orchestrator.py

    print("Placeholder: Trigger Orchestrator called")
    flash("Orchestrator trigger not fully implemented yet. Check console.", "info")
    python_executable = config.get('PYTHON_EXECUTABLE', 'python') # Use configured python or default
    orchestrator_script = 'orchestrator.py'
    try:
        # Be careful with running scripts like this in a web server context

        process = subprocess.Popen([python_executable, orchestrator_script],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # Don't wait for it to finish, just start it
        print(f"Attempted to start {orchestrator_script} with PID: {process.pid}")
        flash(f"Orchestrator script ({orchestrator_script}) started in background (PID: {process.pid}). Check console/logs for progress.", "success")
        # return jsonify({"status": "success", "message": f"Orchestrator script started ({process.pid}). Check console/logs."}), 200
    except FileNotFoundError:
         print(f"Error starting orchestrator.py: '{python_executable}' or '{orchestrator_script}' not found.")
         flash(f"Error: Could not find Python executable ('{python_executable}') or script ('{orchestrator_script}').", "danger")
    except Exception as e:
        print(f"Error starting orchestrator.py: {e}")
        flash(f"Failed to start orchestrator script: {e}", "danger")
        # return jsonify({"status": "error", "message": f"Failed to start orchestrator: {e}"}), 500
    return redirect(url_for('index'))


# @app.route('/trigger/upload/<topic>', methods=['POST'])
# def trigger_upload(topic):
#     # TODO: Find video details (final path, metadata) for the given topic slug/name
#     # TODO: Call youtube_uploader
#     # TODO: Update status in sheet_manager
#     print(f"Placeholder: Trigger Upload called for topic: {topic}")
#     flash(f"Upload trigger for '{topic}' not implemented yet.", "info")
#     # return jsonify({"status": "success", "message": f"Upload triggered for {topic} (Placeholder)"}), 200
#     return redirect(url_for('index'))

# --- Topic Management Routes ---
@app.route('/delete_topic', methods=['POST'])
def delete_topic_route():
    """Handles deletion of a topic from the database."""
    if not db_manager:
        flash("Database service is not available.", "danger")
        return redirect(url_for('index'))

    topic_to_delete = request.form.get('topic_to_delete')

    if not topic_to_delete:
        flash("No topic specified for deletion.", "warning")
        return redirect(url_for('index'))

    print(f"Received request to delete topic: {topic_to_delete}")
    try:
        success = db_manager.delete_topic(topic_to_delete)
        if success:
            flash(f"Successfully deleted topic: '{topic_to_delete}'.", "success")
        else:
            # delete_topic might return False if not found or on error
            flash(f"Could not delete topic: '{topic_to_delete}'. It might not exist or an error occurred.", "warning")
    except Exception as e:
        print(f"ERROR during topic deletion route for '{topic_to_delete}': {e}")
        flash(f"An unexpected error occurred while deleting topic: {e}", "danger")

    return redirect(url_for('index'))


# --- Editor Routes (Placeholders) ---
@app.route('/editor/<topic_slug>')
def editor(topic_slug):
    # TODO: Fetch asset list and script for topic_slug
    # TODO: Render editor.html template with this data
    print(f"Placeholder: Editor page requested for: {topic_slug}")
    flash(f"Editor page for '{topic_slug}' not implemented yet.", "info")
    # return render_template('editor.html', topic_slug=topic_slug) # Pass data later
    return redirect(url_for('index')) # Redirect back until implemented


@app.route('/api/assets/<topic_slug>')
def api_get_assets(topic_slug):
    # TODO: Find assets in ./assets/<topic_slug>/
    print(f"Placeholder: API Get Assets called for: {topic_slug}")
    # Simulate finding assets
    return jsonify({
        "images": ["placeholder1.jpg", "placeholder2.png"],
        "videos": ["stock_footage.mp4"],
        "voiceover": "voiceover.mp3"
    })

@app.route('/api/script/<topic_slug>')
def api_get_script(topic_slug):
    # TODO: Read script text from ./assets/<topic_slug>/script.txt
    print(f"Placeholder: API Get Script called for: {topic_slug}")
    # Simulate reading script
    script_path = os.path.join(config.get('ASSETS_DIR'), topic_slug, 'script.txt') # Example path
    script_content = "Placeholder script content."
    try:
        # Simulating reading actual script if path logic were implemented
        # if os.path.exists(script_path):
        #     with open(script_path, 'r', encoding='utf-8') as f:
        #         script_content = f.read()
        pass # Keep placeholder for now
    except Exception as e:
        print(f"Error reading script for API {topic_slug}: {e}")
        script_content = f"Error loading script: {e}"

    return jsonify({"script": script_content})

@app.route('/api/save_edits/<topic_slug>', methods=['POST'])
def api_save_edits(topic_slug):
    # TODO: Receive JSON data (image order, script text, style choices)
    # TODO: Save this data temporarily or update relevant files
    print(f"Placeholder: API Save Edits called for: {topic_slug}")
    print("Received data:", request.json)
    return jsonify({"status": "success", "message": "Edits saved (Placeholder)"})

@app.route('/api/render/<topic_slug>', methods=['POST'])
def api_render_video(topic_slug):
    # TODO: Get saved edits/parameters
    # TODO: Call VideoEditor.render_video() - Needs background task handling!
    # TODO: Update sheet status
    print(f"Placeholder: API Render Video called for: {topic_slug}")
    return jsonify({"status": "success", "message": "Render started (Placeholder - will take time)"})

# --- Configuration Page Route (Placeholder) ---
@app.route('/config')
def config_page():
     # TODO: Load current settings from config/env
     # TODO: Render config_page.html with options
     print("Placeholder: Config page requested.")
     flash("Configuration page not implemented yet.", "info")
     return redirect(url_for('index')) # Redirect back until implemented

# --- Main Execution ---
if __name__ == '__main__':
    debug_mode = config.get('FLASK_DEBUG')
    host = config.get('FLASK_HOST')
    port = config.get('FLASK_PORT')
    print(f"Starting Flask server on http://{host}:{port}/ with debug mode: {debug_mode}")
    # Ensure database directory exists if db_path includes directories
    if db_manager and db_manager.db_path:
         db_dir = os.path.dirname(db_manager.db_path)
         if db_dir: os.makedirs(db_dir, exist_ok=True)

    app.run(debug=debug_mode, host=host, port=port)