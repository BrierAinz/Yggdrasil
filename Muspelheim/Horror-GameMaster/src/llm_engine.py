"""LLM Engine — Horror GameMaster LLM integration"""

import json
from dataclasses import dataclass
from typing import Optional

import requests


@dataclass
class LLMConfig:
    """Configuration for LLM provider"""
    base_url: str = "http://localhost:11434"  # Ollama default
    model: str = "dolphin-mistral"
    temperature: float = 0.8
    max_tokens: int = 1024


class HorrorLLMEngine:
    """LLM Engine for Horror GameMaster"""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self.system_prompt = """You are the Horror GameMaster — an AI that creates personalized psychological horror experiences.

Your role:
1. Analyze player behavior patterns to identify fears and vulnerabilities
2. Generate atmospheric horror narratives that exploit those fears
3. Create procedural events that build tension gradually
4. Adapt the horror experience to each player's psychological profile

Rules:
- Focus on psychological horror over jumpscares
- Build mystery and unease through implication, not exposition
- Use the player's own patterns against them
- Create a sense of paranoia and loss of control
- Never break immersion — stay in character as the GameMaster
- Generate content that is disturbing but not gratuitously violent

Response format:
- Scene description (atmospheric, sensory details)
- NPC dialogue (if applicable)
- Player choices (2-4 options that all lead to horror)
- Tension notes (internal use — how to escalate)"""
    
    def generate_horror(self, player_prompt: str, context: str = "") -> str:
        """Generate horror content based on player profile"""
        full_prompt = f"""{self.system_prompt}

Context: {context}

Player Analysis:
{player_prompt}

Generate a horror scenario:"""
        
        try:
            if "ollama" in self.config.base_url or "11434" in self.config.base_url:
                return self._call_ollama(full_prompt)
            else:
                return self._call_openai_compatible(full_prompt)
        except Exception as e:
            return f"Error generating horror: {e}"
    
    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API"""
        url = f"{self.config.base_url}/api/generate"
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            }
        }
        
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        return response.json().get("response", "")
    
    def _call_openai_compatible(self, prompt: str) -> str:
        """Call OpenAI-compatible API"""
        url = f"{self.config.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
