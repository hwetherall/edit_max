import os
import requests
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

class OpenRouterClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key is required")
        
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_completion(self, 
                           model: str, 
                           prompt: str, 
                           system_prompt: Optional[str] = None,
                           temperature: float = 0.7,
                           max_tokens: int = 40000) -> Dict[Any, Any]:
        """
        Generate a completion using the specified model on OpenRouter
        """
        url = f"{self.base_url}/chat/completions"
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()
    
    def process_markdown(self, 
                        markdown_text: str, 
                        models: List[str],
                        system_prompt: str) -> Dict[str, str]:
        """
        Process markdown text through multiple models and return their responses
        """
        results = {}
        
        for model in models:
            try:
                response = self.generate_completion(
                    model=model,
                    prompt=markdown_text,
                    system_prompt=system_prompt
                )
                
                if 'choices' in response and len(response['choices']) > 0:
                    results[model] = response['choices'][0]['message']['content']
                else:
                    results[model] = "Error: No content in response"
            except Exception as e:
                results[model] = f"Error: {str(e)}"
        
        return results 