# src/database_manager.py
import sqlite3
import time
import os
from .config_manager import manager as config

class DatabaseManager:
    """Handles interactions with the internal SQLite database."""

    TABLE_NAME = 'videos'
    # Define column names matching the intended schema
    COLUMNS = [
        'topic', 'pipeline_status', 'generated_script_path',
        'final_video_path', 'youtube_url', 'last_error', 'last_updated',
        'source_type', 'source_detail'
    ]

    def __init__(self):
        self.db_path = config.get('DATABASE_FILE')
        if not self.db_path:
            raise ValueError("DATABASE_FILE path is not configured.")
        print(f"Initializing DatabaseManager with DB path: {self.db_path}")
        self._create_table_if_not_exists()

    def _get_connection(self):
        """Establishes a connection to the SQLite database."""
        try:
            # isolation_level=None enables autocommit, simpler for this use case
            conn = sqlite3.connect(self.db_path, isolation_level=None)
            conn.row_factory = sqlite3.Row # Return rows as dictionary-like objects
            return conn
        except sqlite3.Error as e:
            print(f"ERROR: Failed to connect to database at {self.db_path}: {e}")
            raise

    def _create_table_if_not_exists(self):
        """Creates the videos table if it doesn't exist."""
        sql_create_table = f"""
        CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
            topic TEXT PRIMARY KEY NOT NULL UNIQUE,
            pipeline_status TEXT NOT NULL DEFAULT 'PENDING_SCRIPT',
            generated_script_path TEXT,
            final_video_path TEXT,
            youtube_url TEXT,
            last_error TEXT,
            last_updated TEXT NOT NULL,
            source_type TEXT,
            source_detail TEXT
        );
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql_create_table)
                print(f"Table '{self.TABLE_NAME}' checked/created successfully.")
        except sqlite3.Error as e:
            print(f"ERROR: Failed to create/check table '{self.TABLE_NAME}': {e}")
            raise

    def get_all_videos_status(self):
        """ Fetches all rows from the videos table. """
        sql_select_all = f"SELECT * FROM {self.TABLE_NAME} ORDER BY last_updated DESC"
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql_select_all)
                rows = cursor.fetchall()
                # Convert Row objects to standard dictionaries for consistency
                return [dict(row) for row in rows]
        except sqlite3.Error as e:
            print(f"ERROR: Failed to fetch all videos from database: {e}")
            return [] # Return empty list on failure

    def get_topic_details(self, topic):
        """Gets all data for a specific topic row."""
        sql_select_topic = f"SELECT * FROM {self.TABLE_NAME} WHERE topic = ?"
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql_select_topic, (topic,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            print(f"ERROR getting details for topic '{topic}': {e}")
            return None

    def update_status(self, topic, status, **kwargs):
        """ Finds a row by topic and updates its status and other columns. """
        print(f"Updating status for topic '{topic}' to '{status}'...")
        update_data = {'pipeline_status': status, 'last_updated': time.strftime("%Y-%m-%d %H:%M:%S")}
        update_data.update(kwargs)

        # Filter kwargs to only include valid columns
        valid_updates = {k: v for k, v in update_data.items() if k in self.COLUMNS}

        if not valid_updates:
             print("Warning: No valid columns provided for update.")
             return False

        set_clause = ", ".join([f"{key} = ?" for key in valid_updates.keys()])
        values = list(valid_updates.values())
        values.append(topic) # For the WHERE clause

        sql_update = f"UPDATE {self.TABLE_NAME} SET {set_clause} WHERE topic = ?"

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql_update, values)
                if cursor.rowcount == 0:
                     print(f"Warning: Topic '{topic}' not found for update.")
                     return False
                print(f"Successfully updated topic '{topic}'.")
                return True
        except sqlite3.Error as e:
            print(f"ERROR: Failed to update status for topic '{topic}': {e}")
            return False

    def add_topic(self, topic_name, source_type="Manual", source_detail="", initial_status='PENDING_SCRIPT'):
        """Adds a new topic row to the database."""
        print(f"Attempting to add topic '{topic_name}' to database...")
        sql_insert = f"""
        INSERT INTO {self.TABLE_NAME} (topic, pipeline_status, last_updated, source_type, source_detail)
        VALUES (?, ?, ?, ?, ?)
        """
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        values = (topic_name, initial_status, current_time, source_type, source_detail)

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql_insert, values)
                print(f"Successfully added topic '{topic_name}'.")
                return True
        except sqlite3.IntegrityError:
            # This happens if the topic (PRIMARY KEY) already exists
            print(f"Info: Topic '{topic_name}' already exists in the database. Skipping add.")
            return False # Indicate it wasn't newly added
        except sqlite3.Error as e:
            print(f"ERROR: Failed to add topic '{topic_name}': {e}")
            return False

    def find_topics_by_status(self, status, limit=1):
        """Finds topics matching a given status."""
        sql_select_status = f"""
        SELECT topic FROM {self.TABLE_NAME}
        WHERE pipeline_status = ?
        ORDER BY last_updated ASC  -- Process older items first
        LIMIT ?
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql_select_status, (status, limit))
                rows = cursor.fetchall()
                return [row['topic'] for row in rows] # Extract just the topic names
        except sqlite3.Error as e:
            print(f"ERROR finding topics by status '{status}': {e}")
            return []

    def delete_topic(self, topic):
        """Deletes a topic row from the database."""
        sql_delete = f"DELETE FROM {self.TABLE_NAME} WHERE topic = ?"
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql_delete, (topic,))
                if cursor.rowcount > 0:
                    print(f"Successfully deleted topic '{topic}'.")
                    return True
                else:
                    print(f"Info: Topic '{topic}' not found for deletion.")
                    return False
        except sqlite3.Error as e:
            print(f"ERROR deleting topic '{topic}': {e}")
            return False