"""NLU reasoning pipeline orchestrator — stages 1→10."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

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
from .types import Intent, PipelineState
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
        if refs:
            # Re-embed expanded utterance for better intent/retrieval
            state.embedding = self.emb.encode(expanded)
            state.add_trace(f"coref:{list(refs.values())[:3]}")

        # 4 Intent on meaning vector
        state.intent = self.intents.predict(expanded, state.embedding)
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
        state.add_trace(f"reason:{state.reasoning.strategy[:48]}")

        # Plan with language from original user text
        state.plan = self.planning.plan(
            message=state.normalized or state.raw,
            intent=state.intent,
            reasoning=state.reasoning,
        )
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
        self.memory.remember_turn("user", state.raw, entities=state.entities)
        self.memory.remember_turn(
            "ai",
            str(draft.get("reply") or ""),
            code=str(draft.get("code") or ""),
            lang=str(draft.get("lang") or ""),
        )
        # Update topic from substantive coding/question turns
        if state.intent and state.intent.intent.value in {
            "coding", "question", "explanation", "search"
        }:
            self.memory.store.topic = state.normalized[:160]

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
                "plan_tools": [t.value for t in (state.plan.tools if state.plan else [])],
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
        if draft.get("research_query"):
            payload["research_query"] = draft["research_query"]
            payload["source"] = draft.get("source") or "fallback"
            payload["allow_web"] = True

        state.final_payload = payload
        state.final_reply = payload["reply"]
        return payload


# Module-level singleton used by the server
nlu_pipeline = NLUPipeline()
