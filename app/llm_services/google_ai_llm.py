import json
import google.generativeai as genai
from typing import Dict, Any
from app.core.services import BaseLLMService


class GoogleAiService(BaseLLMService):
    """
    Implementation of LLMService using Google's Generative AI (Gemini).
    """

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Google AI Studio key is not provided.")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name="gemini-2.5-pro")
        print("GoogleAiService initialized with gemini-2.5-pro model.")

    def process_data(self, data: str, schema_content) -> Dict[str, Any]:
        """
        Uses the Gemini LLM to format the scraped data.
        Returns a dictionary with predefined properties.
        """
        print("Processing data with Google Gemini LLM...")

        formatted_schema = ', '.join(
            [f"[{field}: {details['description']} ({details['format']})]" 
             for field, details in schema_content.items()])

        # Craft a prompt to instruct the LLM to return a JSON object
        prompt = f"""
        Analyze the below text content from a web page. 
        Extract and summarize the content into a JSON object with the following properties:
        {formatted_schema}.

        The final output must be a single JSON object. Do not include any other text or formatting.
        It is important to assign the HttpUrl fields with the URL values from the text. 
        
        Text Content:
        {data[:3000]} 
        """

        try:
            # Make the API call to the Gemini model
            response = self.model.generate_content(prompt)
            # The model's response contains the JSON as a string
            json_str = response.text.strip().replace("`", "").replace("json", "").strip()

            # Parse the JSON string into a Python dictionary
            processed_data = json.loads(json_str)

            return processed_data
        except Exception as e:
            print(f"Error processing with LLM: {e}")
            raise RuntimeError(f"LLM processing failed. Please check the API key and model output.")
