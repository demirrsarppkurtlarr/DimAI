"""Stage 7 — reasoning layer (analyze → reason → plan signals before answer).

Phase 4: subgoals, alternative comparison, confidence, contradiction checks,
and self-review notes that planning/validation can use.
"""
from __future__ import annotations

import re
from typing import List, Optional, Sequence

from .types import (
    Entity,
    Intent,
    IntentResult,
    MemoryHit,
    ReasoningFrame,
)


def _fold(text: str) -> str:
    t = (text or "").lower().replace("İ", "i").replace("I", "i").replace("ı", "i")
    return t.translate(str.maketrans("çğıöşü", "cgiosu"))


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
        alternatives: list[str] = []
        contradictions: list[str] = []
        self_checks: list[str] = []
        subgoals: list[str] = []

        folded = _fold(message)

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

        # Fresh substantive asks should not be treated as ambiguous clarifies
        substantive = any(
            x in folded
            for x in (
                "karsilastir", "nedir", "nasil", "yaz", "compare", "what", "how",
                "vs", "farki", "kimdir", "arastir", "calisiyorsun",
            )
        )
        if intent.intent == Intent.CLARIFY and substantive:
            notes.append("Override clarify: message is substantive.")
            open_q = []
        elif intent.confidence < 0.35 or intent.intent == Intent.CLARIFY:
            if not substantive:
                open_q.append("Intent is ambiguous — may need a short clarification.")

        if intent.intent == Intent.CODING and not any(
            e.type.value in {"language", "product", "topic"} for e in entities
        ):
            if len(message.split()) <= 3:
                open_q.append("Coding request is vague; may invent a concrete starter app.")

        # Subgoals — break the problem down
        subgoals = self._subgoals(intent.intent, folded, resolved_refs)

        # Alternatives — compare approaches before committing
        alternatives = self._alternatives(intent.intent, folded)

        # Contradiction detection vs memory
        if topic_hits and substantive:
            topic = _fold(topic_hits[0].content)
            # New named entities that conflict with forcing old topic
            if intent.intent in {
                Intent.CONVERSATION, Intent.OPINION, Intent.QUESTION, Intent.SEARCH
            }:
                if topic and topic not in folded and len(folded.split()) >= 3:
                    notes.append("New question differs from sticky topic — do not force prior topic.")
                    assumptions.append("Prior topic is background only for this turn.")

        for h in memory:
            if h.kind == "preference" and "name=" in h.content:
                name = h.content.split("name=")[-1].split(",")[0].strip()
                if name and re.search(r"adimi bilmiyorum|don't know your name", folded):
                    contradictions.append(f"User denies known name {name}")

        strategy = {
            Intent.CODING: "Design architecture first (modules, data, invariants), then implement original code; never paste tutorials.",
            Intent.QUESTION: "Answer factually using KB/memory/web; stay on topic.",
            Intent.EXPLANATION: "Explain step by step with examples.",
            Intent.SEARCH: "Gather external or learned knowledge, then summarize.",
            Intent.TRANSLATION: "Translate faithfully; keep register.",
            Intent.MATH: "Compute exactly; show brief reasoning.",
            Intent.WEATHER: "Fetch live weather and report temperature in Celsius only.",
            Intent.CONVERSATION: "Reply warmly with DimAI personality; keep thread; never sound robotic.",
            Intent.OPINION: "Compare options with clear criteria; give a practical recommendation.",
            Intent.CREATIVE: "Generate original creative text.",
            Intent.PLANNING: "Break into ordered actionable steps.",
            Intent.COMMAND: "Interpret as actionable instruction; confirm result.",
            Intent.CLARIFY: "Ask one precise clarifying question.",
            Intent.UNKNOWN: "Ask clarifying question or give best-effort helpful reply.",
        }.get(intent.intent, "Be helpful and context-aware.")

        if intent.secondary:
            notes.append(f"Secondary intent signal: {intent.secondary.value}")

        if topic_hits and intent.intent in {Intent.CLARIFY, Intent.UNKNOWN} and not substantive:
            notes.append("Prefer continuing active topic over blank clarify.")
            if open_q:
                open_q = [q for q in open_q if "ambiguous" not in q.lower()]

        # Confidence estimate
        confidence = float(intent.confidence or 0.5)
        if substantive:
            confidence = max(confidence, 0.7)
        if intent.intent in {Intent.OPINION, Intent.QUESTION, Intent.SEARCH} and (
            "karsilastir" in folded or "vs" in folded or "nedir" in folded
        ):
            confidence = max(confidence, 0.85)
        if contradictions:
            confidence = min(confidence, 0.4)
        if open_q:
            confidence = min(confidence, 0.55)

        # Self-review checklist (consumed by validation / generation)
        self_checks = [
            "Does the answer address the latest user message (not only prior topic)?",
            "Were tools considered (KB/codegen/web) when needed?",
            "Is the reply free of robotic clarify-loops?",
        ]
        if intent.intent == Intent.CODING:
            self_checks.append("Was architecture designed before code?")
        if intent.intent == Intent.OPINION:
            self_checks.append("Were at least two options compared with criteria?")

        return ReasoningFrame(
            user_goal=goal,
            assumptions=assumptions,
            constraints=constraints,
            open_questions=open_q,
            relevant_facts=facts,
            resolved_refs=dict(resolved_refs),
            strategy=strategy,
            notes=notes,
            alternatives=alternatives,
            confidence=confidence,
            contradictions=contradictions,
            self_checks=self_checks,
            subgoals=subgoals,
        )

    def _subgoals(
        self,
        intent: Intent,
        folded: str,
        refs: dict[str, str],
    ) -> list[str]:
        if intent == Intent.CODING:
            return [
                "Capture requirements from utterance",
                "Design modules / data model",
                "Implement and review",
            ]
        if intent == Intent.OPINION or "karsilastir" in folded or " vs " in folded:
            return [
                "Identify the options being compared",
                "Pick 2–4 decision criteria",
                "Recommend with caveats",
            ]
        if intent in {Intent.QUESTION, Intent.EXPLANATION, Intent.SEARCH}:
            return [
                "Locate authoritative facts (KB/web)",
                "Answer directly in plain language",
                "Offer one optional follow-up",
            ]
        if intent == Intent.CONVERSATION:
            return ["Acknowledge user", "Answer the ask", "Invite next step lightly"]
        if refs:
            return ["Resolve reference", "Answer about antecedent", "Stay coherent"]
        return ["Understand goal", "Choose tool", "Answer"]

    def _alternatives(self, intent: Intent, folded: str) -> list[str]:
        if intent == Intent.CODING:
            return [
                "A) Design-first modular single file (preferred)",
                "B) Minimal snippet only — weaker for production",
                "C) Reach for heavy frameworks — avoid unless asked",
            ]
        if intent == Intent.OPINION or "karsilastir" in folded:
            return [
                "A) Criteria-based comparison with recommendation (preferred)",
                "B) One-sided marketing answer — reject",
                "C) Ask clarifying niche first — only if options unclear",
            ]
        if intent in {Intent.QUESTION, Intent.SEARCH}:
            return [
                "A) KB then web summarize (preferred)",
                "B) Clarify instead of answering — avoid if ask is clear",
                "C) Dump unrelated prior topic — reject",
            ]
        return [
            "A) Direct helpful answer (preferred)",
            "B) Generic clarify loop — avoid",
        ]

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
