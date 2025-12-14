import os
import json
from typing import List
import httpx
from vlt.core.interfaces import ILLMProvider
from vlt.config import settings

class OpenRouterLLMProvider(ILLMProvider):
    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self.model = settings.openrouter_model
        self.embedding_model = "text-embedding-3-small" # Requires OpenAI or compatible provider via OpenRouter

    def generate_summary(self, context: str, new_content: str) -> str:
        if not self.api_key:
            return "LLM API Key missing. Cannot summarize."
            
        prompt = f"""
        Current State: {context}
        New Input: {new_content}
        
        Task: Update the Current State. 
        - If the New Input is a continuation, merge it.
        - If it is a pivot, record the state change.
        - If it contradicts previous state, update the 'Constraints'.
        
        Return ONLY the updated summary in Markdown.
        """
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://vlt.cli",
            "X-Title": "Vault CLI"
        }
        
        retries = 3
        for attempt in range(retries):
            try:
                with httpx.Client() as client:
                    response = client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json={
                            "model": self.model,
                            "messages": [{"role": "user", "content": prompt}]
                        },
                        timeout=30.0
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                if attempt == retries - 1:
                    return f"Error generating summary after {retries} attempts: {str(e)}"
                continue
        return "Error"

    def get_embedding(self, text: str) -> List[float]:
        if not self.api_key:
            return [0.0] * 1536
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://vlt.cli",
            "X-Title": "Vault CLI"
        }
        
        # OpenRouter might not support embeddings directly for all models.
        # If this fails, user might need to point base_url to OpenAI or another provider.
        try:
            with httpx.Client() as client:
                response = client.post(
                    f"{self.base_url}/embeddings",
                    headers=headers,
                    json={
                        "model": self.embedding_model,
                        "input": text
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                return data["data"][0]["embedding"]
        except Exception:
            # Fallback to zero vector for MVP if endpoint fails (to avoid crashing Librarian)
            # In production, we should log this error.
            return [0.0] * 1536