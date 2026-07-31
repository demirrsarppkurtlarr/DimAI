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
            "nedir", "nasil", "yaz", "yap", "anlat", "icin", "bir", "bu", "ne", "mi", "mu",
            "misin", "kod", "oyun", "lutfen", "merhaba", "selam", "tesekkur", "kac", "neden",
            "hakkinda", "ornek", "cevir", "ingilizce", "gelistir", "olustur", "bana",
            "todo", "chatbot", "karsilastir", "farki",
        }
        words = set(
            folded.translate(str.maketrans("çğıöşü", "cgiosu")).split()
        )
        # Default Turkish for this product unless clearly English prose
        if words & tr_markers or any(c in message for c in "çğıöşüÇĞİÖŞÜ"):
            lang = "tr"
        elif message.isascii() and len(message.split()) >= 4 and not (words & {
            "oyun", "kod", "yap", "yaz", "todo", "3d", "gelistir",
        }):
            # Longer ASCII without TR tech verbs → English
            en_hints = {"the", "what", "how", "please", "write", "make", "create", "about"}
            if words & en_hints:
                lang = "en"
            else:
                lang = "tr"
        else:
            lang = "tr"

        plan = ResponsePlan(language=lang, tone="helpful", style="natural")

        g = (reasoning.user_goal + " " + message).lower().replace("ı", "i")
        g = g.translate(str.maketrans("çğıöşü", "cgiosu"))
        weather_cue = any(
            w in g
            for w in ("hava", "weather", "sicaklik", "derece", "forecast", "yagmur")
        )
        if weather_cue or intent.intent == Intent.WEATHER:
            plan.tools = [ToolName.WEATHER]
            plan.answer_points = [
                "Report current temperature in Celsius",
                "Mention city and conditions",
            ]
            return plan
        if any(w in g for w in ("saat kac", "what time", "tarih bugun")) or "saat" in words and "kac" in words:
            plan.tools = [ToolName.TIME]
            return plan

        if reasoning.open_questions and intent.intent in {Intent.CLARIFY, Intent.UNKNOWN}:
            # Don't clarify if the message already looks like a real ask
            fold = "".join(c for c in message.lower().replace("ı", "i"))
            fold = fold.translate(str.maketrans("çğıöşü", "cgiosu"))
            substantive = any(
                x in fold
                for x in (
                    "karsilastir", "nedir", "nasil", "yaz", "yap", "oyun", "kod",
                    "compare", "what", "how", "vs", "farki", "kimdir", "arastir",
                    "3d", "game", "todo", "olustur",
                )
            )
            if substantive and any(x in fold for x in ("yaz", "yap", "oyun", "kod", "game", "3d", "todo", "olustur")):
                plan.tools = [ToolName.CODEGEN]
                plan.needs_clarification = False
                return plan
            if not substantive:
                plan.needs_clarification = True
                plan.clarification_question = (
                    "Tam olarak neyi istediğini bir cümleyle söylersen daha isabetli yardımcı olurum."
                    if lang == "tr"
                    else "Could you rephrase what you need in one clear sentence?"
                )
                plan.tools = [ToolName.CHAT]
                plan.answer_points = ["Ask for clarification"]
                return plan
            # Fall through — treat as question/opinion instead of blocking
            plan.tools = [ToolName.KB, ToolName.WEB, ToolName.CHAT]
            plan.needs_clarification = False

        intent_map = {
            Intent.CODING: [ToolName.CODEGEN],
            Intent.MATH: [ToolName.MATH],
            Intent.WEATHER: [ToolName.WEATHER],
            Intent.TRANSLATION: [ToolName.TRANSLATE],
            Intent.SEARCH: [ToolName.WEB, ToolName.KB],
            Intent.QUESTION: [ToolName.KB, ToolName.WEB],
            Intent.EXPLANATION: [ToolName.KB, ToolName.CHAT],
            Intent.CONVERSATION: [ToolName.CHAT],
            Intent.OPINION: [ToolName.KB, ToolName.CHAT, ToolName.WEB],
            Intent.CREATIVE: [ToolName.CHAT],
            Intent.PLANNING: [ToolName.CHAT],
            Intent.COMMAND: [ToolName.CHAT],
        }
        plan.tools = list(intent_map.get(intent.intent, [ToolName.CHAT]))

        if intent.intent == Intent.EXPLANATION:
            plan.style = "step_by_step"
        if intent.intent == Intent.PLANNING:
            plan.style = "step_by_step"
        if intent.intent == Intent.CODING:
            plan.answer_points = [
                "State the architecture briefly (modules + decisions)",
                "Provide complete original runnable code for this project",
                "Avoid tutorial clones and unnecessary dependencies",
                "Add a short usage note",
            ]
            plan.ignore = [
                "generic fibonacci unless requested",
                "copying GitHub/tutorial structures",
                "searching the web for full source implementations first",
            ]
            plan.style = "step_by_step"
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

        # Continuity cues in reasoning notes
        if any("incomplete" in n or "continue" in n or "same_project" in n for n in reasoning.notes):
            plan.needs_clarification = False
            if ToolName.CHAT in plan.tools and ToolName.KB not in plan.tools:
                if intent.intent in {Intent.EXPLANATION, Intent.QUESTION}:
                    plan.tools = [ToolName.KB, ToolName.CHAT]
            plan.answer_points.insert(0, "Continue prior topic naturally")

        # If coding but extremely vague, still generate — don't block with clarify
        if intent.intent == Intent.CODING and reasoning.open_questions:
            plan.needs_clarification = False
            plan.answer_points.append("Pick a sensible concrete default if underspecified")

        return plan


planning_engine = PlanningEngine()
