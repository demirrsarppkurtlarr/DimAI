"""Shared types for the DimAI NLU reasoning pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Intent(str, Enum):
    QUESTION = "question"
    COMMAND = "command"
    CONVERSATION = "conversation"
    OPINION = "opinion"
    EXPLANATION = "explanation"
    CODING = "coding"
    TRANSLATION = "translation"
    CREATIVE = "creative"
    PLANNING = "planning"
    SEARCH = "search"
    MATH = "math"
    WEATHER = "weather"
    CLARIFY = "clarify"
    UNKNOWN = "unknown"


class EntityType(str, Enum):
    PERSON = "person"
    COMPANY = "company"
    PRODUCT = "product"
    DATE = "date"
    TIME = "time"
    GAME = "game"
    LANGUAGE = "language"
    FILE = "file"
    VARIABLE = "variable"
    PROJECT = "project"
    LOCATION = "location"
    NUMBER = "number"
    TOPIC = "topic"
    OTHER = "other"


class ToolName(str, Enum):
    NONE = "none"
    CODEGEN = "codegen"
    MATH = "math"
    TRANSLATE = "translate"
    WEATHER = "weather"
    TIME = "time"
    KB = "kb"
    WEB = "web"
    MEMORY = "memory"
    CHAT = "chat"


@dataclass
class Token:
    text: str
    lemma: str
    index: int
    is_punct: bool = False
    is_number: bool = False


@dataclass
class Entity:
    text: str
    type: EntityType
    start: int
    end: int
    score: float = 1.0
    normalized: str = ""
    resolved_from: str = ""  # e.g. pronoun "it" → "Docker"


@dataclass
class MemoryHit:
    role: str
    content: str
    score: float
    kind: str = "turn"  # turn | code | preference | topic | task
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class IntentResult:
    intent: Intent
    confidence: float
    scores: dict[str, float] = field(default_factory=dict)
    secondary: Optional[Intent] = None


@dataclass
class ReasoningFrame:
    user_goal: str
    assumptions: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    relevant_facts: list[str] = field(default_factory=list)
    resolved_refs: dict[str, str] = field(default_factory=dict)
    strategy: str = ""
    notes: list[str] = field(default_factory=list)


@dataclass
class ResponsePlan:
    answer_points: list[str] = field(default_factory=list)
    ignore: list[str] = field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: str = ""
    tools: list[ToolName] = field(default_factory=list)
    tone: str = "helpful"
    style: str = "natural"  # natural | step_by_step | concise | summary
    language: str = "tr"
    search_query: str = ""
    improve_code: bool = False


@dataclass
class ToolResult:
    name: ToolName
    ok: bool
    payload: dict[str, Any] = field(default_factory=dict)
    error: str = ""


@dataclass
class ValidationReport:
    answered_question: bool = True
    used_context: bool = True
    consistent: bool = True
    fluent: bool = True
    score: float = 1.0
    issues: list[str] = field(default_factory=list)
    should_regenerate: bool = False


@dataclass
class PipelineState:
    """Mutable state flowing through all pipeline stages."""

    raw: str = ""
    history: list[dict[str, Any]] = field(default_factory=list)

    # Stage outputs
    normalized: str = ""
    tokens: list[Token] = field(default_factory=list)
    embedding: Any = None  # np.ndarray
    intent: Optional[IntentResult] = None
    entities: list[Entity] = field(default_factory=list)
    memory_hits: list[MemoryHit] = field(default_factory=list)
    reasoning: Optional[ReasoningFrame] = None
    plan: Optional[ResponsePlan] = None
    tool_results: list[ToolResult] = field(default_factory=list)
    draft_reply: str = ""
    draft_extras: dict[str, Any] = field(default_factory=dict)
    validation: Optional[ValidationReport] = None
    final_reply: str = ""
    final_payload: dict[str, Any] = field(default_factory=dict)
    discourse_search_query: str = ""
    discourse_improve: bool = False
    meaning_notes: list[str] = field(default_factory=list)
    meaning_expanded: str = ""

    # Trace for debugging / UI "thinking"
    trace: list[str] = field(default_factory=list)

    def add_trace(self, msg: str) -> None:
        self.trace.append(msg)
