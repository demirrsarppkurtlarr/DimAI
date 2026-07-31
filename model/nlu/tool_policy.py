"""Phase 7 — automatic tool selection policy.

Chooses the best DimAI capability for the turn. Never uses the web as the
first move for code generation / full-source hunting.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .types import Intent, IntentResult, ReasoningFrame, ToolName


@dataclass
class ToolDecision:
    tools: list[ToolName]
    reason: str
    forbid: list[str]


def select_tools(
    *,
    message: str,
    intent: IntentResult,
    reasoning: ReasoningFrame,
) -> ToolDecision:
    folded = (
        (message or "").lower().replace("ı", "i").replace("İ", "i")
        .translate(str.maketrans("çğıöşü", "cgiosu"))
    )
    words = set(folded.split())
    forbid = [
        "web search for complete source code as first solution",
        "reproduce github/tutorial repos wholesale",
    ]

    # Hard routes
    if intent.intent == Intent.WEATHER or any(
        w in folded for w in ("hava", "weather", "sicaklik", "derece", "yagmur")
    ):
        return ToolDecision([ToolName.WEATHER], "live weather", forbid)

    if intent.intent == Intent.MATH or (
        len(words) <= 8 and any(ch in folded for ch in "+*/") and any(c.isdigit() for c in folded)
    ):
        return ToolDecision([ToolName.MATH], "exact compute", forbid)

    if intent.intent == Intent.TRANSLATION or "cevir" in folded or "translate" in folded:
        return ToolDecision([ToolName.TRANSLATE], "translation", forbid)

    if "saat" in words and "kac" in words:
        return ToolDecision([ToolName.TIME], "clock", forbid)

    # Coding — never WEB first. Trust CODING intent; soft-cues only for
    # ambiguous command-like turns (whole words — avoid "yapiyorsun" → yap).
    coding_words = words & {
        "yaz", "yap", "olustur", "uret", "kod", "oyun", "game", "todo",
        "flask", "api", "program", "script", "uygulama",
    }
    soft_codegen = intent.intent in {
        Intent.COMMAND, Intent.CREATIVE, Intent.UNKNOWN,
    } and (bool(coding_words) or "3d" in folded)

    if intent.intent == Intent.CODING or soft_codegen:
        tools = [ToolName.CODEGEN]
        if any(x in folded for x in ("gelistir", "improve", "refactor")):
            tools = [ToolName.MEMORY, ToolName.CODEGEN]
        return ToolDecision(
            tools,
            "design-first codegen; no web source hunt",
            forbid,
        )

    if intent.intent == Intent.OPINION:
        return ToolDecision(
            [ToolName.KB, ToolName.CHAT, ToolName.WEB],
            "compare with KB then optional web facts",
            forbid,
        )

    if intent.intent in {Intent.QUESTION, Intent.EXPLANATION}:
        # RAG first; web only as backup (planner still may call WEB)
        return ToolDecision(
            [ToolName.KB, ToolName.WEB, ToolName.CHAT],
            "RAG then web summarize; abstain if weak",
            forbid,
        )

    if intent.intent == Intent.SEARCH:
        return ToolDecision([ToolName.WEB, ToolName.KB], "explicit research", forbid)

    if intent.intent == Intent.CONVERSATION:
        return ToolDecision([ToolName.CHAT, ToolName.MEMORY], "persona + memory", forbid)

    if intent.intent == Intent.PLANNING:
        return ToolDecision([ToolName.CHAT, ToolName.MEMORY], "plan from context", forbid)

    # Continue / memory heavy
    if reasoning.resolved_refs or any("continue" in n or "incomplete" in n for n in reasoning.notes):
        return ToolDecision(
            [ToolName.MEMORY, ToolName.KB, ToolName.CHAT],
            "honor discourse memory",
            forbid,
        )

    return ToolDecision([ToolName.CHAT], "default chat", forbid)
