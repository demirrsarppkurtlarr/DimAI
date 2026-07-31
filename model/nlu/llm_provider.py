"""Swap-in LLM backends for Stage 9 generation.

Usage later:
    from model.nlu.llm_provider import build_provider
    from model.nlu.generation import ResponseGenerator
    gen = ResponseGenerator(llm=build_provider())
"""
from __future__ import annotations

import os
from typing import Optional

from .generation import LLMProvider, LocalTemplateProvider, OpenAIProvider


def build_provider(name: Optional[str] = None) -> LLMProvider:
    """
    Select provider via argument or env DIMAI_LLM_PROVIDER.
    Values: local | openai | (future: anthropic, ollama)
    """
    choice = (name or os.environ.get("DIMAI_LLM_PROVIDER") or "local").strip().lower()
    if choice == "openai":
        return OpenAIProvider(api_key=os.environ.get("OPENAI_API_KEY", ""))
    return LocalTemplateProvider()
