"""NLU reasoning pipeline orchestrator — stages 1→10."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .conversation import analyze_meaning
from .embedding import EmbeddingEngine, embedding_engine
from .entity import EntityEngine, entity_engine
from .generation import ResponseGenerator, response_generator
from .intent import IntentEngine, intent_engine
from .memory import MemoryEngine, memory_engine
from .normalize import normalize
from .planning import PlanningEngine, planning_engine
from .reasoning import ReasoningEngine, reasoning_engine
from .tokenizer import tokenize
from .tools import ToolManager, tool_manager
from .types import Intent, PipelineState, ToolName
from .validation import ValidationEngine, validation_engine


class NLUPipeline:
    """
    Modern LLM-style reasoning pipeline.

    Stages:
      normalize → tokenize → embed → memory → intent → entity
      → reason → plan → tools → generate → validate → final
    """

    def __init__(
        self,
        *,
        emb: EmbeddingEngine | None = None,
        intents: IntentEngine | None = None,
        entities: EntityEngine | None = None,
        memory: MemoryEngine | None = None,
        reasoning: ReasoningEngine | None = None,
        planning: PlanningEngine | None = None,
        tools: ToolManager | None = None,
        generator: ResponseGenerator | None = None,
        validator: ValidationEngine | None = None,
    ) -> None:
        self.emb = emb or embedding_engine
        self.intents = intents or intent_engine
        self.entities = entities or entity_engine
        self.memory = memory or memory_engine
        self.reasoning = reasoning or reasoning_engine
        self.planning = planning or planning_engine
        self.tools = tools or tool_manager
        self.generator = generator or response_generator
        self.validator = validator or validation_engine

    def run(self, message: str, history: Optional[List[dict]] = None) -> Dict[str, Any]:
        state = PipelineState(raw=message or "", history=list(history or [])[-24:])

        # Easter eggs — exact whole message only; short-circuit before NLU
        try:
            from model import skills as _skills

            if _skills.looks_like_special_code(state.raw):
                ans = _skills.answer_special_code(state.raw)
                if ans:
                    return {
                        "reply": ans,
                        "source": "chat",
                        "intent": "conversation",
                        "intent_confidence": 1.0,
                        "thinking": "easter-egg",
                        "nlu": {"egg": True},
                        "allow_web": False,
                    }
        except Exception as exc:  # noqa: BLE001
            # Never silently skip eggs due to import glitches
            state.add_trace(f"egg-error:{type(exc).__name__}")

        # 1 Normalize
        state.normalized = normalize(state.raw)
        state.add_trace("normalize")

        # 2 Tokenize
        state.tokens = tokenize(state.normalized)
        state.add_trace(f"tokenize:{len(state.tokens)}")

        # 3 Embed
        state.embedding = self.emb.encode(state.normalized)
        state.add_trace("embed")

        # 6 Memory first (RAG) — needed for coref before intent nuances
        self.memory.ingest_history(state.history)
        state.memory_hits = self.memory.retrieve(state.normalized, state.embedding)
        state.add_trace(f"memory:{len(state.memory_hits)}")

        # 5 Entities (on normalized text)
        state.entities = self.entities.extract(state.normalized, state.tokens)

        # Coreference expansion
        expanded, refs, ents = self.memory.resolve_references(state.normalized, state.entities)
        state.entities = ents

        # Conversation meaning: incomplete / indirect / continue / same project
        meaning = analyze_meaning(
            expanded,
            topic=self.memory.store.topic,
            last_code=self.memory.store.last_code,
            entities=state.entities,
            memory=state.memory_hits,
        )
        state.meaning_notes = list(meaning.notes)
        state.meaning_expanded = meaning.expanded
        if meaning.expanded and meaning.expanded != expanded:
            expanded = meaning.expanded
            note = ",".join(meaning.notes[:3]) if meaning.notes else "expand"
            state.add_trace(f"meaning:{note}")
        elif meaning.notes:
            state.add_trace("meaning:" + ",".join(meaning.notes[:3]))

        if refs:
            # Re-embed expanded utterance for better intent/retrieval
            state.embedding = self.emb.encode(expanded)
            state.add_trace(f"coref:{list(refs.values())[:3]}")
        elif meaning.expanded != state.normalized:
            state.embedding = self.emb.encode(expanded)

        # 4 Intent on meaning vector
        state.intent = self.intents.predict(expanded, state.embedding)

        # Discourse speech-acts override weak embedding decisions
        from .discourse import decide as discourse_decide

        has_code = bool(self.memory.store.last_code) or any(
            h.kind == "code" and h.content for h in state.memory_hits
        )
        # Also detect code fences in recent AI history
        if not has_code:
            for h in reversed(state.history[-8:]):
                if h.get("role") in ("ai", "assistant") and "```" in str(h.get("content") or ""):
                    has_code = True
                    break
                c = str(h.get("content") or "")
                if h.get("role") in ("ai", "assistant") and ("def " in c or "import " in c):
                    has_code = True
                    break

        has_topic = bool(self.memory.store.topic or self.memory.store.project)
        disc = discourse_decide(
            state.raw,
            has_prior_code=has_code,
            has_topic=has_topic,
        )
        if disc.intent and disc.confidence >= 0.7:
            state.intent.intent = disc.intent
            state.intent.confidence = max(state.intent.confidence, disc.confidence)
            state.discourse_search_query = disc.search_query
            state.discourse_improve = disc.improve_code
            state.add_trace(f"discourse:{disc.reason}")

        # Never leave clear asks as clarify
        if state.intent.intent == Intent.CLARIFY:
            fold = (state.normalized or state.raw).lower().replace("ı", "i")
            fold = fold.translate(str.maketrans("çğıöşü", "cgiosu"))
            if any(x in fold for x in ("karsilastir", "vs", "farki", "compare")):
                state.intent.intent = Intent.OPINION
                state.intent.confidence = max(state.intent.confidence, 0.8)
                state.add_trace("clarify→opinion")
            elif any(x in fold for x in ("nedir", "ne demek", "what is", "kimdir")):
                state.intent.intent = Intent.QUESTION
                state.intent.confidence = max(state.intent.confidence, 0.75)
                state.add_trace("clarify→question")
            elif any(x in fold for x in ("calisiyorsun", "how do you work", "sen kimsin")):
                state.intent.intent = Intent.CONVERSATION
                state.intent.confidence = max(state.intent.confidence, 0.9)
                state.add_trace("clarify→conversation")
            elif any(x in fold for x in ("yaz", "yap", "oyun", "kod", "3d", "game", "todo", "olustur")):
                state.intent.intent = Intent.CODING
                state.intent.confidence = max(state.intent.confidence, 0.9)
                state.add_trace("clarify→coding")

        # Soft meaning-implied intent when embedding is weak
        if (
            meaning.implied_intent
            and state.intent.confidence < 0.45
            and state.intent.intent in {Intent.CLARIFY, Intent.UNKNOWN, Intent.CONVERSATION}
        ):
            state.intent.intent = meaning.implied_intent
            state.intent.confidence = max(state.intent.confidence, 0.55)
            state.add_trace(f"meaning-intent:{meaning.implied_intent.value}")

        # Discourse: resolved refs + elaboration cues → explanation
        if refs and state.intent.intent in {
            Intent.CLARIFY, Intent.UNKNOWN, Intent.CONVERSATION, Intent.COMMAND
        }:
            fold = expanded.lower().replace("ı", "i")
            if any(x in fold for x in ("anlat", "acikla", "detay", "more", "elaborate", "neden", "nasil")):
                state.intent.intent = Intent.EXPLANATION
                state.intent.confidence = max(state.intent.confidence, 0.55)
        # Bare arithmetic expressions → math
        import re as _re
        if _re.fullmatch(r"[\d\s\+\-\*/\(\)\.,]+", state.normalized or ""):
            state.intent.intent = Intent.MATH
            state.intent.confidence = max(state.intent.confidence, 0.8)
        # Weather cues → weather intent (don't let clarify steal it)
        try:
            from model import skills as _skills

            if _skills.looks_like_weather(state.raw) or _skills.looks_like_weather(state.normalized):
                state.intent.intent = Intent.WEATHER
                state.intent.confidence = max(state.intent.confidence, 0.85)
        except Exception:
            pass
        state.add_trace(
            f"intent:{state.intent.intent.value}@{state.intent.confidence:.2f}"
        )

        # 7 Reason
        state.reasoning = self.reasoning.reason(
            message=expanded,
            intent=state.intent,
            entities=state.entities,
            memory=state.memory_hits,
            resolved_refs=refs,
        )
        if state.discourse_search_query:
            state.reasoning.notes.append(f"search_query={state.discourse_search_query}")
        if state.discourse_improve:
            state.reasoning.notes.append("improve_prior_code")
        if meaning.is_incomplete:
            state.reasoning.notes.append("incomplete_utterance")
            state.reasoning.assumptions.append("User message is incomplete; filled from context.")
        if meaning.is_indirect:
            state.reasoning.notes.append("indirect_question")
        if meaning.same_project:
            state.reasoning.notes.append("same_project")
            if self.memory.store.project:
                state.reasoning.assumptions.append(
                    f"Continuing project: {self.memory.store.project}"
                )
        state.add_trace(f"reason:{state.reasoning.strategy[:48]}")

        # Plan with language from original user text
        state.plan = self.planning.plan(
            message=state.normalized or state.raw,
            intent=state.intent,
            reasoning=state.reasoning,
        )
        if state.discourse_search_query and state.plan:
            state.plan.search_query = state.discourse_search_query
            # Only force WEB for search intents — comparisons keep KB+CHAT(+WEB)
            if state.intent and state.intent.intent == Intent.SEARCH:
                state.plan.tools = [ToolName.WEB]
                state.plan.needs_clarification = False
            elif state.intent and state.intent.intent == Intent.OPINION:
                state.plan.tools = [ToolName.KB, ToolName.CHAT, ToolName.WEB]
                state.plan.needs_clarification = False
            elif state.intent and state.intent.intent == Intent.QUESTION:
                state.plan.tools = [ToolName.KB, ToolName.WEB]
                state.plan.needs_clarification = False
        if state.discourse_improve and state.plan:
            state.plan.improve_code = True
            state.plan.tools = [ToolName.CODEGEN]
            state.plan.needs_clarification = False
            state.plan.answer_points = [
                "Improve the previous code",
                "Add features, structure, and error handling",
                "Keep it runnable",
            ]
        # Incomplete continue → prefer KB then chat, not clarify
        if meaning.wants_continue and state.plan and state.intent.intent == Intent.EXPLANATION:
            state.plan.tools = [ToolName.KB, ToolName.CHAT]
            state.plan.needs_clarification = False
            state.plan.style = "step_by_step"
        state.add_trace(
            "plan:tools=" + ",".join(t.value for t in state.plan.tools)
        )

        # Tool calling
        state.tool_results = self.tools.run(state)
        state.add_trace(
            "tools:" + ",".join(
                f"{t.name.value}:{'ok' if t.ok else 'fail'}" for t in state.tool_results
            )
        )

        # 9 Generate
        draft = self.generator.generate(state)
        state.draft_reply = str(draft.get("reply") or "")
        state.draft_extras = dict(draft)

        # 10 Validate (+ one repair pass)
        state.validation = self.validator.evaluate(state, draft)
        state.add_trace(f"validate:{state.validation.score:.2f}")
        if state.validation.should_regenerate:
            draft = self.validator.repair(state, draft, state.validation)
            state.validation = self.validator.evaluate(state, draft)
            state.add_trace("regenerated")

        # Persist memory for this turn
        action = ""
        if state.intent:
            action = f"intent:{state.intent.intent.value}"
        self.memory.remember_turn("user", state.raw, entities=state.entities, action=action)
        self.memory.remember_turn(
            "ai",
            str(draft.get("reply") or ""),
            code=str(draft.get("code") or ""),
            lang=str(draft.get("lang") or ""),
            action=f"source:{draft.get('source') or 'nlu'}",
        )
        # Update topic from substantive coding/question turns
        if state.intent and state.intent.intent.value in {
            "coding", "question", "explanation", "search"
        }:
            incomplete = any(
                "incomplete" in n or "continue" in n or "same-project" in n
                for n in (state.meaning_notes or [])
            )
            # Don't clobber a good topic with "daha / devam" fragments
            if not incomplete and len((state.normalized or "").split()) >= 2:
                label = state.normalized[:160]
                for e in state.entities:
                    if e.type.value in {"product", "language", "topic", "person", "company"}:
                        label = e.normalized or e.text
                        break
                import re as _re
                label = _re.sub(
                    r"\b(nedir|nasil|anlat|acikla|yaz|what|is|how|why)\b",
                    " ",
                    label,
                    flags=_re.I,
                )
                label = _re.sub(r"\s+", " ", label).strip() or state.normalized[:80]
                # Ignore ultra-generic labels
                if label.lower() not in {"daha", "devam", "continue", "more", "peki", "ok"}:
                    self.memory.store.topic = label[:160]
                    if state.intent.intent.value == "coding":
                        self.memory.store.project = label[:120]

        thinking = " → ".join(state.trace[-10:])
        payload: Dict[str, Any] = {
            "reply": draft.get("reply") or "",
            "source": draft.get("source") or "nlu",
            "thinking": thinking,
            "intent": state.intent.intent.value if state.intent else "unknown",
            "intent_confidence": state.intent.confidence if state.intent else 0.0,
            "nlu": {
                "normalized": state.normalized,
                "tokens": len(state.tokens),
                "entities": [
                    {
                        "text": e.text,
                        "type": e.type.value,
                        "score": round(e.score, 3),
                        "resolved_from": e.resolved_from,
                    }
                    for e in state.entities[:12]
                ],
                "refs": refs,
                "meaning": state.meaning_notes,
                "plan_tools": [t.value for t in (state.plan.tools if state.plan else [])],
                "reasoning": {
                    "confidence": state.reasoning.confidence if state.reasoning else 0,
                    "subgoals": (state.reasoning.subgoals if state.reasoning else [])[:4],
                    "alternatives": (state.reasoning.alternatives if state.reasoning else [])[:3],
                    "self_checks": (state.reasoning.self_checks if state.reasoning else [])[:3],
                },
                "validation": {
                    "score": state.validation.score if state.validation else 0,
                    "issues": state.validation.issues if state.validation else [],
                },
                "goal": state.reasoning.user_goal if state.reasoning else "",
            },
            "allow_web": bool(draft.get("allow_web")),
        }
        if draft.get("code"):
            payload["code"] = draft["code"]
            payload["lang"] = draft.get("lang") or "python"
        if draft.get("design"):
            payload["design"] = draft["design"]
        if draft.get("review"):
            payload["review"] = draft["review"]
        if draft.get("research_query"):
            payload["research_query"] = draft["research_query"]
            payload["source"] = draft.get("source") or "fallback"
            payload["allow_web"] = True

        state.final_payload = payload
        state.final_reply = payload["reply"]
        return payload


# Module-level singleton used by the server
nlu_pipeline = NLUPipeline()
