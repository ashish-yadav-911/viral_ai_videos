# # src/google_sheet_manager.py
# import time
# from .config_manager import manager as config # Use the instantiated manager

# # Placeholder for Google Sheet functionality
# class GoogleSheetManager:
#     def __init__(self):
#         self.sheet_id = config.get('GOOGLE_SHEET_ID')
#         self.worksheet_name = config.get('WORKSHEET_NAME')
#         # In a real scenario, authentication would happen here
#         print(f"Initializing GoogleSheetManager for Sheet ID: {self.sheet_id}, Worksheet: {self.worksheet_name}")
#         self.worksheet = None # Placeholder for the actual worksheet object
#         self._connect()

#     def _connect(self):
#         # TODO: Implement actual connection using gspread and OAuth2
#         print("Attempting to connect to Google Sheets...")
#         # Simulating connection delay/process
#         time.sleep(0.5)
#         print("Connection placeholder complete (No actual connection yet).")
#         # In real implementation, this would set self.worksheet using gspread

#     def get_all_videos_status(self):
#         """
#         Fetches all rows from the sheet.
#         Returns a list of dictionaries, where keys are column headers.
#         """
#         # TODO: Replace with actual gspread call worksheet.get_all_records()
#         print("Fetching all video statuses (Placeholder)...")
#         # Simulate fetching data
#         return [
#             {'Topic': 'Placeholder Topic 1', 'Pipeline Status': 'PENDING_SCRIPT', 'Generated Script Path': '', 'Final Video Path': '', 'YouTube URL': '', 'Last Error': '', 'Last Updated': '2023-10-27 10:00:00'},
#             {'Topic': 'Placeholder Topic 2', 'Pipeline Status': 'PENDING_ASSETS', 'Generated Script Path': './assets/placeholder2/script.txt', 'Final Video Path': '', 'YouTube URL': '', 'Last Error': '', 'Last Updated': '2023-10-27 11:00:00'},
#             {'Topic': 'Placeholder Topic 3', 'Pipeline Status': 'DONE', 'Generated Script Path': './assets/placeholder3/script.txt', 'Final Video Path': './assets/placeholder3/final_video.mp4', 'YouTube URL': 'https://youtu.be/example', 'Last Error': '', 'Last Updated': '2023-10-26 15:00:00'},
#         ]

#     def update_status(self, topic, status, **kwargs):
#         """
#         Finds a row by topic and updates its status and other columns.
#         kwargs can contain other column headers and their values.
#         """
#         # TODO: Implement actual gspread find and update logic
#         print(f"Updating status for topic '{topic}' to '{status}' with data: {kwargs} (Placeholder)...")
#         # Simulate finding and updating
#         time.sleep(0.1)
#         print("Update placeholder complete.")
#         return True # Indicate success/failure

#     def add_topic(self, topic_name, source_type="Manual", source_detail=""):
#         """Adds a new topic row to the sheet."""
#         # TODO: Implement actual gspread append_row logic
#         print(f"Adding topic '{topic_name}' (Placeholder)...")
#         # Prepare row data based on your sheet columns
#         new_row = {
#             'Topic': topic_name,
#             'Pipeline Status': 'PENDING_SCRIPT',
#             'Generated Script Path': '',
#             'Final Video Path': '',
#             'YouTube URL': '',
#             'Last Error': '',
#             'Last Updated': time.strftime("%Y-%m-%d %H:%M:%S"),
#             # Add other initial columns if needed (Source Type, Source Detail etc.)
#         }
#         # In a real scenario: self.worksheet.append_row(list(new_row.values()))
#         print(f"Append placeholder complete. Row data: {list(new_row.values())}")
#         return True

#     # Add other methods as needed (find_next_topic, log_error, etc.)

# src/google_sheet_manager.py
import gspread # type: ignore
from google.oauth2.service_account import Credentials
import time
import os
from .config_manager import manager as config

class GoogleSheetManager:
    """Handles interactions with the Google Sheet."""

    # Define expected column headers (ensure these match your sheet exactly)
    EXPECTED_COLUMNS = [
        'Topic', 'Pipeline Status', 'Generated Script Path',
        'Final Video Path', 'YouTube URL', 'Last Error', 'Last Updated',
        # Add any other columns you might need, e.g., 'Source Type', 'Source Detail'
    ]

    def __init__(self):
        self.sheet_id = config.get('GOOGLE_SHEET_ID')
        self.worksheet_name = config.get('WORKSHEET_NAME')
        self.scopes = config.get('SCOPES', [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/youtube.upload' # Keep youtube scope if needed elsewhere
        ])
        # Determine credentials path - search relative to config_manager.py then root
        cred_file = 'credentials.json' # Default name
        potential_paths = [
            os.path.join(os.path.dirname(__file__), cred_file),
            os.path.join(os.path.dirname(__file__), '..', cred_file) # Root directory
        ]
        self.credentials_path = None
        for path in potential_paths:
            if os.path.exists(path):
                self.credentials_path = path
                break

        if not self.credentials_path:
            print(f"ERROR: 'credentials.json' not found in expected locations.")
            raise FileNotFoundError("Could not find credentials.json")

        if not self.sheet_id:
             print(f"ERROR: 'GOOGLE_SHEET_ID' not configured in .env.")
             raise ValueError("GOOGLE_SHEET_ID not configured.")

        self.worksheet = None
        self._connect()

    def _connect(self):
        """Establishes connection to the Google Sheet worksheet."""
        try:
            print(f"Attempting to connect to Google Sheets using {self.credentials_path}...")
            creds = Credentials.from_service_account_file(self.credentials_path, scopes=self.scopes)
            client = gspread.authorize(creds)
            spreadsheet = client.open_by_key(self.sheet_id)
            self.worksheet = spreadsheet.worksheet(self.worksheet_name)
            print(f"Successfully connected to worksheet: '{self.worksheet_name}'")
            self._verify_columns() # Verify headers on connection
        except gspread.exceptions.SpreadsheetNotFound:
            print(f"ERROR: Spreadsheet not found. Check GOOGLE_SHEET_ID: {self.sheet_id}")
            raise
        except gspread.exceptions.WorksheetNotFound:
            print(f"ERROR: Worksheet not found. Check WORKSHEET_NAME: {self.worksheet_name}")
            # Consider creating it? For now, raise error.
            # self.worksheet = spreadsheet.add_worksheet(title=self.worksheet_name, rows="100", cols="20")
            # self.worksheet.append_row(self.EXPECTED_COLUMNS) # Add headers if creating
            raise
        except Exception as e:
            print(f"ERROR: Failed to connect to Google Sheets: {e}")
            self.worksheet = None # Ensure worksheet is None on failure
            raise # Re-raise the exception after logging

    def _verify_columns(self):
        """Checks if the sheet headers match the expected columns."""
        if not self.worksheet:
             print("ERROR: Cannot verify columns, worksheet not connected.")
             return
        try:
            headers = self.worksheet.row_values(1)
            if not headers:
                print(f"WARNING: Worksheet '{self.worksheet_name}' appears empty. Adding headers.")
                self.worksheet.update('A1', [self.EXPECTED_COLUMNS])
                print(f"Added headers: {self.EXPECTED_COLUMNS}")
                return

            # Basic check: are all expected columns present? (Order doesn't strictly matter for get_all_records)
            missing_columns = [col for col in self.EXPECTED_COLUMNS if col not in headers]
            if missing_columns:
                print(f"WARNING: Worksheet '{self.worksheet_name}' is missing expected columns: {missing_columns}")
                print(f"         Found headers: {headers}")
                # Decide on action: raise error, try to adapt, or just warn? Warning for now.
            # else:
            #     print("Sheet columns verified.")

        except Exception as e:
            print(f"ERROR: Could not verify sheet columns: {e}")


    def get_all_videos_status(self):
        """ Fetches all rows from the sheet as a list of dictionaries. """
        if not self.worksheet:
            print("ERROR: Google Sheet not connected.")
            return []
        try:
            print("Fetching all video statuses from Google Sheet...")
            records = self.worksheet.get_all_records()
            print(f"Fetched {len(records)} records.")
            return records
        except Exception as e:
            print(f"ERROR: Failed to fetch records from Google Sheet: {e}")
            # Consider re-connecting or raising the error
            # self._connect() # Optional: try reconnecting once
            return [] # Return empty list on failure

    def find_row_by_topic(self, topic):
        """Finds the first row matching the topic. Returns the row index or None."""
        if not self.worksheet: return None
        try:
            cell = self.worksheet.find(topic, in_column=1) # Assumes Topic is in Column A (index 1)
            return cell.row if cell else None
        except gspread.exceptions.CellNotFound:
            return None
        except Exception as e:
            print(f"ERROR finding row for topic '{topic}': {e}")
            return None

    def update_status(self, topic, status, **kwargs):
        """ Finds a row by topic and updates its status and other columns. """
        if not self.worksheet:
            print("ERROR: Google Sheet not connected.")
            return False
        try:
            row_index = self.find_row_by_topic(topic)
            if row_index is None:
                print(f"ERROR: Topic '{topic}' not found in sheet for updating status.")
                return False

            print(f"Updating status for topic '{topic}' (Row {row_index}) to '{status}'...")
            update_data = {'Pipeline Status': status, 'Last Updated': time.strftime("%Y-%m-%d %H:%M:%S")}
            update_data.update(kwargs) # Merge other updates

            headers = self.worksheet.row_values(1)
            col_updates = []
            for col_name, value in update_data.items():
                try:
                    # Find column index (1-based)
                    col_index = headers.index(col_name) + 1
                    col_updates.append({'range': gspread.utils.rowcol_to_a1(row_index, col_index), 'values': [[value]]})
                except ValueError:
                    print(f"Warning: Column '{col_name}' not found in sheet headers. Cannot update.")

            if col_updates:
                 self.worksheet.batch_update(col_updates)
                 print(f"Successfully updated row {row_index} for topic '{topic}'.")
                 return True
            else:
                 print(f"No valid columns found to update for topic '{topic}'.")
                 return False

        except Exception as e:
            print(f"ERROR: Failed to update status for topic '{topic}': {e}")
            return False

    def add_topic(self, topic_name, source_type="Manual", source_detail=""):
        """Adds a new topic row to the sheet."""
        if not self.worksheet:
            print("ERROR: Google Sheet not connected.")
            return False
        try:
            print(f"Adding topic '{topic_name}' to Google Sheet...")
            # Check if topic already exists
            if self.find_row_by_topic(topic_name):
                print(f"Topic '{topic_name}' already exists in the sheet.")
                return False # Or maybe update it? For now, skip adding duplicates.

            new_row_dict = {
                'Topic': topic_name,
                'Pipeline Status': 'PENDING_SCRIPT',
                'Generated Script Path': '',
                'Final Video Path': '',
                'YouTube URL': '',
                'Last Error': '',
                'Last Updated': time.strftime("%Y-%m-%d %H:%M:%S"),
                # Add source_type, source_detail if columns exist
                # 'Source Type': source_type,
                # 'Source Detail': source_detail,
            }

            # Ensure row aligns with EXPECTED_COLUMNS order for append_row
            headers = self.EXPECTED_COLUMNS # Use the defined expected order
            new_row_values = [new_row_dict.get(header, '') for header in headers]

            self.worksheet.append_row(new_row_values, value_input_option='USER_ENTERED')
            print(f"Successfully added topic '{topic_name}'.")
            return True
        except Exception as e:
            print(f"ERROR: Failed to add topic '{topic_name}': {e}")
            return False

    def find_topics_by_status(self, status, limit=1):
        """Finds topics matching a given status."""
        if not self.worksheet: return []
        try:
            all_videos = self.get_all_videos_status() # Fetch all records
            matching_topics = []
            for video in all_videos:
                if video.get('Pipeline Status') == status:
                    matching_topics.append(video.get('Topic'))
                    if len(matching_topics) >= limit:
                        break
            return matching_topics
        except Exception as e:
            print(f"ERROR finding topics by status '{status}': {e}")
            return []

    def get_topic_details(self, topic):
        """Gets all data for a specific topic row."""
        if not self.worksheet: return None
        try:
            row_index = self.find_row_by_topic(topic)
            if row_index:
                # Fetch the entire row data - get_all_records might be easier if recently fetched
                # Alternative: row_values = self.worksheet.row_values(row_index)
                # headers = self.worksheet.row_values(1)
                # return dict(zip(headers, row_values))

                # Using get_all_records and filtering is often simpler
                all_videos = self.get_all_videos_status()
                for video in all_videos:
                    if video.get('Topic') == topic:
                        return video
            return None
        except Exception as e:
            print(f"ERROR getting details for topic '{topic}': {e}")
            return None