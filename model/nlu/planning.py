"""Stage 8 — response planning (what to say / ignore / which tools)."""
from __future__ import annotations

from typing import Sequence

from .types import Intent, IntentResult, ReasoningFrame, ResponsePlan, ToolName


class PlanningEngine:
    def plan(
        self,
        *,
        message: str,
        intent: IntentResult,
        reasoning: ReasoningFrame,
        language_hint: str = "tr",
    ) -> ResponsePlan:
        lang = language_hint
        folded = "".join(
            c for c in message.lower().replace("ı", "i").replace("İ", "i")
        )
        tr_markers = {
            "nedir", "nasil", "yaz", "anlat", "icin", "bir", "bu", "ne", "mi", "mu",
            "misin", "kod", "lutfen", "merhaba", "selam", "tesekkur", "kac", "neden",
            "hakkinda", "ornek", "cevir", "ingilizce",
        }
        words = set(
            folded.translate(str.maketrans("çğıöşü", "cgiosu")).split()
        )
        if words & tr_markers or any(c in message for c in "çğıöşüÇĞİÖŞÜ"):
            lang = "tr"
        elif message.isascii() and len(message.split()) >= 3:
            lang = "en"

        plan = ResponsePlan(language=lang, tone="helpful", style="natural")

        if reasoning.open_questions and intent.intent in {Intent.CLARIFY, Intent.UNKNOWN}:
            plan.needs_clarification = True
            plan.clarification_question = (
                "Tam olarak neyi istediğini bir cümleyle söylersen daha isabetli yardımcı olurum."
                if lang == "tr"
                else "Could you rephrase what you need in one clear sentence?"
            )
            plan.tools = [ToolName.CHAT]
            plan.answer_points = ["Ask for clarification"]
            return plan

        intent_map = {
            Intent.CODING: [ToolName.CODEGEN],
            Intent.MATH: [ToolName.MATH],
            Intent.TRANSLATION: [ToolName.TRANSLATE],
            Intent.SEARCH: [ToolName.WEB, ToolName.KB],
            Intent.QUESTION: [ToolName.KB, ToolName.WEB],
            Intent.EXPLANATION: [ToolName.KB, ToolName.CHAT],
            Intent.CONVERSATION: [ToolName.CHAT],
            Intent.OPINION: [ToolName.CHAT, ToolName.KB],
            Intent.CREATIVE: [ToolName.CHAT],
            Intent.PLANNING: [ToolName.CHAT],
            Intent.COMMAND: [ToolName.CHAT],
        }
        plan.tools = list(intent_map.get(intent.intent, [ToolName.CHAT]))

        # Weather / time soft routing via secondary cues in goal text
        g = (reasoning.user_goal + " " + message).lower()
        if any(w in g for w in ("hava", "weather", "sıcak", "sicak")):
            plan.tools = [ToolName.WEATHER]
        if any(w in g for w in ("saat kaç", "what time", "tarih")):
            plan.tools = [ToolName.TIME]

        if intent.intent == Intent.EXPLANATION:
            plan.style = "step_by_step"
        if intent.intent == Intent.PLANNING:
            plan.style = "step_by_step"
        if intent.intent == Intent.CODING:
            plan.answer_points = [
                "Acknowledge the coding goal",
                "Provide complete runnable code",
                "Add a short usage note",
            ]
            plan.ignore = ["generic fibonacci unless requested"]
        elif intent.intent in {Intent.QUESTION, Intent.SEARCH}:
            plan.answer_points = [
                "Answer the core question directly",
                "Add 2-4 supporting bullets if useful",
                "Offer a natural follow-up",
            ]
        elif intent.intent == Intent.CONVERSATION:
            plan.answer_points = ["Warm reply", "Invite a concrete next step"]
        else:
            plan.answer_points = ["Address the user goal", "Stay context-aware"]

        if reasoning.resolved_refs:
            plan.answer_points.insert(0, "Honor resolved references from memory")

        # If coding but extremely vague, still generate — don't block with clarify
        if intent.intent == Intent.CODING and reasoning.open_questions:
            plan.needs_clarification = False
            plan.answer_points.append("Pick a sensible concrete default if underspecified")

        return plan


planning_engine = PlanningEngine()
