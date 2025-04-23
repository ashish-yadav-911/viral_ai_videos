from .database_manager import DatabaseManager
from .input_processor import InputProcessor
from .llm_service import LLMService

class TopicGenerator:
    """Handles generating topics and adding them to the internal database."""

    def __init__(self):
        self.input_processor = InputProcessor()
        self.llm_service = LLMService()
        # INITIALIZATION CHANGE
        self.db_manager = DatabaseManager()
        print("TopicGenerator initialized with DatabaseManager.")

    def generate_and_store_topics(self, input_data, input_type, num_topics=10):
        """
        Processes input, generates topics, and stores them in the database.
        Returns the list of *newly added* topics or None on failure.
        """
        print(f"Starting topic generation process for input type: {input_type}")

        text_content = self.input_processor.process_input(input_data, input_type)
        if not text_content:
            print("ERROR: Failed to get text content from input. Aborting topic generation.")
            return None

        generated_topics = self.llm_service.generate_topics(text_content, num_topics=num_topics)
        if not generated_topics:
            print("ERROR: Failed to generate topics using LLM.")
            return None

        added_count = 0
        skipped_count = 0
        failed_count = 0
        added_topics_list = []

        for topic in generated_topics:
            # DETAIL EXTRACTION (Example - adapt as needed)
            detail = ""
            if isinstance(input_data, str):
                detail = input_data[:200] # Truncate long scripts/URLs
            elif isinstance(input_data, list):
                detail = f"Based on {len(input_data)} samples."

            # CALL DB MANAGER
            success = self.db_manager.add_topic(
                topic_name=topic,
                source_type=input_type,
                source_detail=detail
            )
            # add_topic returns True if added, False if skipped (duplicate) or error
            if success is True: # Explicitly check for True (newly added)
                added_count += 1
                added_topics_list.append(topic)
            elif success is False: # Check for False (skipped or failed)
                # Check if it already exists to differentiate skipped vs failed
                if self.db_manager.get_topic_details(topic):
                    skipped_count += 1
                else:
                    failed_count += 1 # Treat other False returns as failures


        print(f"Topic storage complete: {added_count} added, {skipped_count} skipped (duplicates), {failed_count} failed.")

        if added_count > 0:
            return added_topics_list
        else:
            # Distinguish between error and just no new topics
            if failed_count > 0:
                 print("ERROR: Some topics failed to be added to the database.")
                 return None # Indicate failure
            else:
                 print("Info: No new topics were added to the database (likely duplicates).")
                 return [] # Indicate success but zero new topics