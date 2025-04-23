# src/llm_service.py
import openai
import time
from .config_manager import manager as config

class LLMService:
    """Handles interactions with the OpenAI API (GPT and DALL-E)."""

    def __init__(self):
        self.api_key = config.get('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not configured in .env.")
        self.client = openai.OpenAI(api_key=self.api_key)
        self.gpt_model = config.get('OPENAI_GPT_MODEL', "gpt-3.5-turbo")
        self.image_model = config.get('OPENAI_IMAGE_MODEL', "dall-e-2")
        print(f"LLMService initialized with GPT model: {self.gpt_model}, Image model: {self.image_model}")

    def _call_gpt(self, messages, temperature=0.7, max_tokens=1500):
        """ Generic function to call the OpenAI Chat Completion endpoint. """
        try:
            print(f"Calling OpenAI Chat Completion API (model: {self.gpt_model})...")
            start_time = time.time()
            response = self.client.chat.completions.create(
                model=self.gpt_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            duration = time.time() - start_time
            print(f"OpenAI API call completed in {duration:.2f} seconds.")
            content = response.choices[0].message.content.strip()
            return content
        except openai.AuthenticationError as e:
             print(f"ERROR: OpenAI Authentication Failed. Check API Key. {e}")
             raise
        except openai.RateLimitError as e:
            print(f"ERROR: OpenAI Rate Limit Exceeded. Check your plan and usage limits. {e}")
            raise
        except openai.APIConnectionError as e:
            print(f"ERROR: OpenAI API Connection Error: {e}")
            raise
        except Exception as e:
            print(f"ERROR: An unexpected error occurred during OpenAI API call: {e}")
            raise

    def generate_topics(self, input_text, num_topics=10):
        """ Generates video topic ideas based on input text (script, URL content, etc.). """
        print(f"Generating {num_topics} topics based on input...")
        system_prompt = "You are an assistant skilled in creating engaging YouTube video topic ideas."
        user_prompt = f"""Based on the following input text, generate a list of {num_topics} distinct and catchy YouTube video topic ideas suitable for faceless videos (like slideshows with voiceover). Format the output as a numbered list, with each topic on a new line.

Input Text:
---
{input_text[:3000]}
---

Example Output Format:
1. Topic Idea One
2. Another Interesting Topic
3. A Third Topic Suggestion
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        raw_response = self._call_gpt(messages, max_tokens=300 * num_topics // 10) # Estimate tokens

        # Process the response to extract topics
        topics = []
        if raw_response:
            lines = raw_response.strip().split('\n')
            for line in lines:
                line = line.strip()
                # Try to remove numbering (e.g., "1. ", "2. ", "- ")
                if line and (line[0].isdigit() or line.startswith('-')):
                    parts = line.split('.', 1)
                    if len(parts) > 1:
                        topic = parts[1].strip()
                    else: # Handle cases like "- Topic"
                       topic = line[1:].strip()

                    if topic:
                       topics.append(topic)
                elif line: # If no numbering, assume the line is the topic
                    topics.append(line)
        print(f"Generated {len(topics)} topic ideas.")
        return topics[:num_topics] # Return only the requested number

    def generate_script(self, topic, target_word_count=300):
        """Generates a video script (hook, body) for a given topic."""
        print(f"Generating script for topic: '{topic}'...")
        system_prompt = """You are a helpful assistant skilled in writing engaging scripts for short, faceless YouTube videos (like informative slideshows).
        The script should have a clear Hook and Body section.
        The tone should be informative, clear, and easy to follow.
        Keep sentences relatively short for easy voiceover and captioning."""

        user_prompt = f"""Please write a script for a faceless YouTube video on the topic: "{topic}"

        Target approximate word count: {target_word_count} words.

        Structure the output exactly like this:

        Hook:
        [Engaging opening sentence or question related to the topic. Max 1-2 sentences.]

        Body:
        [Main content discussing the topic. Break it down into logical points or steps. Use paragraphs for separation. Avoid overly complex language. Aim for clarity and conciseness.]

        Example:
        Hook:
        Ever wondered how black holes actually work? Let's break down this cosmic mystery!

        Body:
        Imagine a star much bigger than our sun running out of fuel. Its own gravity becomes overwhelming...
        This collapse creates an incredibly dense point called a singularity, with gravity so strong not even light can escape. That's the defining feature of a black hole.
        The edge of no return is called the event horizon. Cross this boundary, and there's no turning back...
        Scientists study black holes indirectly by observing their effects on nearby stars and gas clouds. It's fascinating detective work!
        So, black holes are nature's ultimate compact objects, born from the death of massive stars.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        # Estimate max tokens based on word count (approx 1.5 tokens per word + prompt overhead)
        estimated_tokens = int(target_word_count * 1.5) + 300
        script_content = self._call_gpt(messages, max_tokens=estimated_tokens, temperature=0.6)

        # Basic validation: Check if Hook and Body markers are present
        if script_content and "Hook:" in script_content and "Body:" in script_content:
             print(f"Script generated successfully for '{topic}'. Length: {len(script_content)} chars.")
             return script_content
        else:
             print(f"ERROR: Generated script for '{topic}' is missing expected structure (Hook:/Body:). Response:\n{script_content}")
             # Fallback or error handling
             # You might return a placeholder or raise an error depending on desired behavior
             # For now, let's return None to indicate failure
             return None

    def generate_metadata(self, script):
        """Generates Title, Description, and Tags based on the script."""
        # TODO: Implement metadata generation prompt
        print("Generating metadata (Title, Description, Tags) (Placeholder)...")
        time.sleep(0.2) # Simulate work
        return {
            "title": f"Everything About {script[:20]}...",
            "description": f"In this video, we explore:\n- Point A\n- Point B\n- Point C\n\nLearn more about {script[:20]}!",
            "tags": ["topic", "faceless", "info", "tutorial"]
        }

    def generate_image_prompts(self, script_section, image_style):
        """Generates DALL-E prompts based on a script section and desired style."""
        # TODO: Implement image prompt generation logic
        print(f"Generating image prompt for style '{image_style}' (Placeholder)...")
        time.sleep(0.1)
        return f"{image_style} illustration of {script_section[:50]}" # Basic placeholder

    def generate_images(self, prompt, n=1, size="1024x1024"):
        """ Calls DALL-E API to generate images. """
        try:
            print(f"Calling DALL-E API (model: {self.image_model}) with prompt: '{prompt[:50]}...'")
            start_time = time.time()
            response = self.client.images.generate(
                model=self.image_model,
                prompt=prompt,
                n=n,
                size=size, # e.g., "1024x1024", "1792x1024", "1024x1792" for dall-e-3
                response_format="url" # Or "b64_json"
            )
            duration = time.time() - start_time
            print(f"DALL-E API call completed in {duration:.2f} seconds.")
            image_urls = [img.url for img in response.data if img.url]
            # If using b64_json: image_data = [img.b64_json for img in response.data]
            return image_urls
        except openai.AuthenticationError as e:
             print(f"ERROR: OpenAI DALL-E Authentication Failed. {e}")
             raise
        except openai.RateLimitError as e:
            print(f"ERROR: OpenAI DALL-E Rate Limit Exceeded. {e}")
            raise
        except openai.BadRequestError as e:
             print(f"ERROR: OpenAI DALL-E Bad Request (check prompt/parameters?): {e}")
             raise
        except Exception as e:
            print(f"ERROR: An unexpected error occurred during DALL-E API call: {e}")
            raise