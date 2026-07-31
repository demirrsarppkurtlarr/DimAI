"""Stage 7 — reasoning layer (internal representation before answering)."""
from __future__ import annotations

from typing import List, Optional, Sequence

from .types import (
    Entity,
    Intent,
    IntentResult,
    MemoryHit,
    ReasoningFrame,
)


class ReasoningEngine:
    def reason(
        self,
        *,
        message: str,
        intent: IntentResult,
        entities: Sequence[Entity],
        memory: Sequence[MemoryHit],
        resolved_refs: dict[str, str],
    ) -> ReasoningFrame:
        goal = self._goal(message, intent, entities, resolved_refs)
        assumptions: list[str] = []
        constraints: list[str] = []
        open_q: list[str] = []
        facts: list[str] = []
        notes: list[str] = []

        if resolved_refs:
            assumptions.append(
                "User refers to prior discourse: "
                + ", ".join(f"{k}→{v}" for k, v in resolved_refs.items())
            )
        topic_hits = [m for m in memory if m.kind == "topic"]
        if topic_hits:
            assumptions.append(f"Active topic: {topic_hits[0].content}")
        code_hits = [m for m in memory if m.kind == "code"]
        if code_hits:
            facts.append("Previous code is available in memory.")
        pref = [m for m in memory if m.kind == "preference"]
        if pref:
            facts.append(f"User preferences: {pref[0].content}")

        for e in entities[:8]:
            facts.append(f"Entity[{e.type.value}]={e.normalized or e.text} ({e.score:.2f})")

        if intent.confidence < 0.35 or intent.intent == Intent.CLARIFY:
            open_q.append("Intent is ambiguous — may need a short clarification.")

        if intent.intent == Intent.CODING and not any(
            e.type.value in {"language", "product", "topic"} for e in entities
        ):
            if len(message.split()) <= 3:
                open_q.append("Coding request is vague; may invent a concrete starter app.")

        strategy = {
            Intent.CODING: "Produce working code tailored to entities/goal; explain briefly.",
            Intent.QUESTION: "Answer factually using KB/memory/web; stay on topic.",
            Intent.EXPLANATION: "Explain step by step with examples.",
            Intent.SEARCH: "Gather external or learned knowledge, then summarize.",
            Intent.TRANSLATION: "Translate faithfully; keep register.",
            Intent.MATH: "Compute exactly; show brief reasoning.",
            Intent.WEATHER: "Fetch live weather and report temperature in Celsius only.",
            Intent.CONVERSATION: "Reply warmly with DimAI personality; keep thread; never sound robotic.",
            Intent.OPINION: "Give a balanced, practical opinion with reasons.",
            Intent.CREATIVE: "Generate original creative text.",
            Intent.PLANNING: "Break into ordered actionable steps.",
            Intent.COMMAND: "Interpret as actionable instruction; confirm result.",
            Intent.CLARIFY: "Ask one precise clarifying question.",
            Intent.UNKNOWN: "Ask clarifying question or give best-effort helpful reply.",
        }.get(intent.intent, "Be helpful and context-aware.")

        if intent.secondary:
            notes.append(f"Secondary intent signal: {intent.secondary.value}")

        # Prefer continuity over clarification when memory has a topic
        if topic_hits and intent.intent in {Intent.CLARIFY, Intent.UNKNOWN}:
            notes.append("Prefer continuing active topic over blank clarify.")
            if open_q:
                open_q = [q for q in open_q if "ambiguous" not in q.lower()]

        return ReasoningFrame(
            user_goal=goal,
            assumptions=assumptions,
            constraints=constraints,
            open_questions=open_q,
            relevant_facts=facts,
            resolved_refs=dict(resolved_refs),
            strategy=strategy,
            notes=notes,
        )

    def _goal(
        self,
        message: str,
        intent: IntentResult,
        entities: Sequence[Entity],
        refs: dict[str, str],
    ) -> str:
        ent = ", ".join((e.normalized or e.text) for e in entities[:5]) or "general"
        ref = ", ".join(refs.values()) if refs else ""
        base = f"{intent.intent.value}: {message.strip()}"
        if ref:
            base += f" (about {ref})"
        if ent and ent != "general":
            base += f" | entities: {ent}"
        return base[:400]


reasoning_engine = ReasoningEngine()
