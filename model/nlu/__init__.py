"""DimAI NLU package — modular LLM-style reasoning pipeline.

Public entry:
    from model.nlu import nlu_pipeline
    result = nlu_pipeline.run(message, history)
"""
from __future__ import annotations

from .pipeline import NLUPipeline, nlu_pipeline
from .types import Intent, EntityType, ToolName

__all__ = [
    "NLUPipeline",
    "nlu_pipeline",
    "Intent",
    "EntityType",
    "ToolName",
]
