import logging
import hashlib
import json
import time
import requests
from typing import Optional, Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)

# Simple in-memory cache for query results
_IN_MEMORY_CACHE: Dict[str, str] = {}


class LLMClientError(Exception):
    """Base exception for LLM Client failures."""
    pass


def get_cache_key(
    text: str,
    system_prompt: str,
    user_prompt: str,
    provider: str,
    model: str,
    temperature: float,
) -> str:
    """Computes a deterministic MD5 hash key for caching LLM outputs."""
    raw_str = (
        f"{text}||{system_prompt}||{user_prompt}||"
        f"{provider}||{model}||{temperature:.2f}||"
        f"{settings.PROMPT_VERSION}"
    )
    return hashlib.md5(raw_str.encode("utf-8")).hexdigest()


def query_llm(
    text: str,
    system_prompt: str,
    user_prompt: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.4,
    timeout: Optional[float] = None,
) -> str:
    """
    Unified client that routes text rewriting requests to the configured LLM API.
    
    If successful, returns the rewritten string.
    Raises LLMClientError on failure, enabling fallback logic at the orchestrator level.
    """
    prov = (provider or settings.LLM_PROVIDER or "openai").lower()
    t_out = timeout or settings.LLM_TIMEOUT or 30.0

    # 1. Resolve model and keys
    if prov == "openai":
        api_key = settings.OPENAI_API_KEY
        m_name = model or settings.LLM_MODEL or "gpt-4o-mini"
        base_url = settings.LLM_BASE_URL or "https://api.openai.com/v1"
    elif prov == "gemini":
        api_key = settings.GEMINI_API_KEY
        m_name = model or settings.LLM_MODEL or "gemini-1.5-flash"
        base_url = settings.LLM_BASE_URL or "https://generativelanguage.googleapis.com"
    elif prov == "anthropic" or prov == "claude":
        api_key = settings.ANTHROPIC_API_KEY
        m_name = model or settings.LLM_MODEL or "claude-3-5-sonnet-latest"
        base_url = settings.LLM_BASE_URL or "https://api.anthropic.com"
    elif prov == "huggingface":
        api_key = settings.HUGGINGFACE_API_KEY or settings.HF_API_KEY
        m_name = model or settings.LLM_MODEL or "meta-llama/Meta-Llama-3-8B-Instruct"
        base_url = settings.LLM_BASE_URL or "https://api-inference.huggingface.co/models"
    elif prov == "local":
        api_key = settings.OPENAI_API_KEY  # Optional for local
        m_name = model or settings.LLM_MODEL or "local-model"
        base_url = settings.LLM_BASE_URL or "http://localhost:11434/v1"
    else:
        raise LLMClientError(f"Unsupported LLM provider: {prov}")

    # 2. Check Cache
    cache_key = get_cache_key(text, system_prompt, user_prompt, prov, m_name, temperature)
    if cache_key in _IN_MEMORY_CACHE:
        logger.info(f"LLM Cache Hit for key: {cache_key}")
        return _IN_MEMORY_CACHE[cache_key]

    # Attempt query with 1 retry
    max_retries = 2
    last_err = None

    for attempt in range(max_retries):
        try:
            logger.info(f"Querying LLM Provider={prov} Model={m_name} (Attempt {attempt+1}/{max_retries})")
            
            if prov in ("openai", "local"):
                if not api_key and prov == "openai":
                    raise LLMClientError("OpenAI API key is missing.")
                
                headers = {"Content-Type": "application/json"}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

                payload = {
                    "model": m_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": temperature,
                    "top_p": settings.LLM_TOP_P,
                    "max_tokens": settings.LLM_MAX_TOKENS,
                }
                url = f"{base_url.rstrip('/')}/chat/completions"
                resp = requests.post(url, headers=headers, json=payload, timeout=t_out)
                resp.raise_for_status()
                res_json = resp.json()
                result = res_json["choices"][0]["message"]["content"].strip()

            elif prov == "gemini":
                if not api_key:
                    raise LLMClientError("Gemini API key is missing.")
                
                headers = {"Content-Type": "application/json"}
                payload = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": user_prompt}]
                        }
                    ],
                    "systemInstruction": {
                        "parts": [{"text": system_prompt}]
                    },
                    "generationConfig": {
                        "temperature": temperature,
                        "topP": settings.LLM_TOP_P,
                        "maxOutputTokens": settings.LLM_MAX_TOKENS,
                    }
                }
                url = f"{base_url.rstrip('/')}/v1beta/models/{m_name}:generateContent?key={api_key}"
                resp = requests.post(url, headers=headers, json=payload, timeout=t_out)
                resp.raise_for_status()
                res_json = resp.json()
                
                # Check structure of Gemini response
                candidates = res_json.get("candidates", [])
                if not candidates:
                    raise LLMClientError("No content generated by Gemini API.")
                result = candidates[0]["content"]["parts"][0]["text"].strip()

            elif prov in ("anthropic", "claude"):
                if not api_key:
                    raise LLMClientError("Anthropic API key is missing.")
                
                headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                payload = {
                    "model": m_name,
                    "max_tokens": settings.LLM_MAX_TOKENS,
                    "system": system_prompt,
                    "messages": [
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": temperature
                }
                url = f"{base_url.rstrip('/')}/v1/messages"
                resp = requests.post(url, headers=headers, json=payload, timeout=t_out)
                resp.raise_for_status()
                res_json = resp.json()
                result = res_json["content"][0]["text"].strip()

            elif prov == "huggingface":
                headers = {"Content-Type": "application/json"}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

                payload = {
                    "inputs": f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>\n{user_prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n",
                    "parameters": {
                        "max_new_tokens": settings.LLM_MAX_TOKENS,
                        "temperature": max(0.01, temperature),
                        "return_full_text": False
                    }
                }
                url = f"{base_url.rstrip('/')}/{m_name}"
                resp = requests.post(url, headers=headers, json=payload, timeout=t_out)
                resp.raise_for_status()
                res_json = resp.json()
                
                if isinstance(res_json, list) and len(res_json) > 0:
                    result = res_json[0].get("generated_text", "").strip()
                elif isinstance(res_json, dict):
                    result = res_json.get("generated_text", "").strip()
                else:
                    raise LLMClientError(f"Unexpected response format from Hugging Face: {res_json}")
            
            else:
                raise LLMClientError(f"Provider {prov} handler is not implemented.")

            # Store in cache
            _IN_MEMORY_CACHE[cache_key] = result
            return result

        except Exception as e:
            logger.warning(f"Error querying {prov} on attempt {attempt+1}: {e}")
            last_err = e
            time.sleep(0.5)

    raise LLMClientError(f"LLM invocation failed after retries. Last error: {last_err}")
