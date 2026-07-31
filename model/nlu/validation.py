"""Stage 10 — self evaluation before sending the final response."""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

from .types import Intent, PipelineState, ValidationReport


class ValidationEngine:
    def evaluate(self, state: PipelineState, draft: Dict[str, Any]) -> ValidationReport:
        issues: list[str] = []
        reply = str(draft.get("reply") or "")
        intent = state.intent.intent if state.intent else Intent.UNKNOWN

        answered = bool(reply.strip())
        if intent == Intent.CODING and not draft.get("code") and "```" not in reply:
            answered = False
            issues.append("coding intent without code")
        if intent == Intent.MATH and not any(ch.isdigit() for ch in reply):
            # soft — unit answers may lack digits rarely
            pass

        used_context = True
        if state.reasoning and state.reasoning.resolved_refs:
            ante = next(iter(state.reasoning.resolved_refs.values())).lower()
            blob = (reply + " " + str(draft.get("code") or "")).lower()
            if ante and ante not in blob and intent != Intent.CONVERSATION:
                # not fatal for chat, but flag for regen on coding/search
                if intent in {Intent.CODING, Intent.QUESTION, Intent.EXPLANATION, Intent.SEARCH}:
                    used_context = False
                    issues.append(f"missing resolved referent '{ante}'")

        consistent = True
        # Contradiction heuristic: denying previous preference name
        for h in state.memory_hits:
            if h.kind == "preference" and "name=" in h.content:
                name = h.content.split("name=")[-1].split(",")[0].strip()
                if name and re.search(r"adini bilmiyorum|don't know your name", reply, re.I):
                    consistent = False
                    issues.append("contradicts known user name")

        fluent = len(reply) >= 8 and not reply.lower().startswith("error")
        if reply.count("?") > 3 and intent != Intent.CLARIFY:
            issues.append("too many questions")

        score = 1.0
        if not answered:
            score -= 0.45
        if not used_context:
            score -= 0.25
        if not consistent:
            score -= 0.25
        if not fluent:
            score -= 0.2
        score -= 0.05 * len(issues)
        score = max(0.0, min(1.0, score))

        should = score < 0.55 or (not answered)
        return ValidationReport(
            answered_question=answered,
            used_context=used_context,
            consistent=consistent,
            fluent=fluent,
            score=score,
            issues=issues,
            should_regenerate=should,
        )

    def repair(self, state: PipelineState, draft: Dict[str, Any], report: ValidationReport) -> Dict[str, Any]:
        """One-shot regeneration heuristics."""
        out = dict(draft)
        reply = str(out.get("reply") or "")
        lang = state.plan.language if state.plan else "tr"
        if "coding intent without code" in report.issues:
            try:
                from model import codegen

                made = codegen.synthesize(state.normalized or state.raw)
                if made and made.get("code"):
                    out.update(made)
                    return out
            except Exception:
                pass
        if not report.used_context and state.reasoning and state.reasoning.resolved_refs:
            topic = next(iter(state.reasoning.resolved_refs.values()))
            prefix = (
                f"{topic} hakkında: "
                if lang == "tr"
                else f"Regarding {topic}: "
            )
            if topic.lower() not in reply.lower():
                out["reply"] = prefix + reply
        if not out.get("reply"):
            out["reply"] = (
                "Bir saniye — isteğini net anlayamadım. Bir cümleyle tekrar yazar mısın?"
                if lang == "tr"
                else "I didn't catch that clearly — could you rephrase in one sentence?"
            )
            out["source"] = "chat"
        return out


validation_engine = ValidationEngine()
