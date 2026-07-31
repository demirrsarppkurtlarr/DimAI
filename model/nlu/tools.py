"""Tool manager — bridges planning decisions to DimAI capabilities."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from .types import Intent, PipelineState, ResponsePlan, ToolName, ToolResult


class ToolManager:
    """Independent tool runner; each tool is optional and fail-soft."""

    def run(self, state: PipelineState) -> List[ToolResult]:
        plan = state.plan or ResponsePlan()
        results: list[ToolResult] = []
        for tool in plan.tools:
            try:
                results.append(self._dispatch(tool, state))
            except Exception as exc:  # noqa: BLE001 — tools must not crash pipeline
                results.append(ToolResult(name=tool, ok=False, error=str(exc)[:200]))
        return results

    def _dispatch(self, tool: ToolName, state: PipelineState) -> ToolResult:
        msg = (
            state.meaning_expanded
            or state.normalized
            or state.raw
        )
        if tool == ToolName.CODEGEN:
            return self._codegen(msg, state)
        if tool == ToolName.MATH:
            return self._math(msg)
        if tool == ToolName.TRANSLATE:
            return self._translate(msg)
        if tool == ToolName.WEATHER:
            return self._weather(msg)
        if tool == ToolName.TIME:
            return self._time(msg)
        if tool == ToolName.KB:
            return self._kb(msg, state)
        if tool == ToolName.WEB:
            return self._web(msg, state)
        if tool == ToolName.MEMORY:
            return ToolResult(
                name=tool,
                ok=True,
                payload={"hits": [h.__dict__ for h in state.memory_hits[:5]]},
            )
        if tool == ToolName.CHAT:
            return ToolResult(name=tool, ok=True, payload={"mode": "chat"})
        return ToolResult(name=tool, ok=False, error="unknown tool")

    def _codegen(self, msg: str, state: PipelineState) -> ToolResult:
        from model import codegen

        plan = state.plan
        prior = ""
        lang = "python"
        for h in state.memory_hits:
            if h.kind == "code" and h.content:
                prior = h.content
                lang = str((h.meta or {}).get("lang") or "python")
                break
        if not prior:
            try:
                from model.nlu.memory import memory_engine

                prior = memory_engine.store.last_code or ""
                lang = memory_engine.store.last_lang or lang
            except Exception:
                prior = ""

        # Extract from history AI messages if still empty
        if not prior:
            import re as _re

            for h in reversed(state.history[-12:]):
                if h.get("role") not in ("ai", "assistant"):
                    continue
                content = str(h.get("content") or "")
                m = _re.search(r"```(?:\w+)?\n(.*?)```", content, _re.S)
                if m:
                    prior = m.group(1).strip()
                    break
                # bare code blocks without fences
                if "def " in content and "return" in content:
                    prior = content
                    break

        if plan and plan.improve_code and prior:
            made = codegen.improve(
                prior,
                msg,
                lang=lang,
                project_context=self._project_context(state),
                user_language=(state.plan.language if state.plan else "tr"),
            )
            if made:
                return ToolResult(name=ToolName.CODEGEN, ok=True, payload=made)

        refs = (state.reasoning.resolved_refs if state.reasoning else {}) or {}
        if refs and len(msg.split()) <= 4:
            topic = next(iter(refs.values()))
            msg = f"{topic} {msg}"
        made = codegen.synthesize(
            msg,
            project_context=self._project_context(state),
            user_language=(state.plan.language if state.plan else "tr"),
        )
        if not made:
            return ToolResult(name=ToolName.CODEGEN, ok=False, error="no code synthesized")
        return ToolResult(name=ToolName.CODEGEN, ok=True, payload=made)

    def _project_context(self, state: PipelineState) -> str:
        bits: list[str] = []
        for h in state.memory_hits:
            if h.kind in {"project", "topic"} and h.content:
                bits.append(h.content)
        if state.reasoning and state.reasoning.user_goal:
            bits.append(state.reasoning.user_goal[:120])
        return " | ".join(bits[:3])

    def _web(self, msg: str, state: PipelineState) -> ToolResult:
        q = (state.plan.search_query if state.plan and state.plan.search_query else "") or msg
        if state.reasoning and state.reasoning.resolved_refs and not (state.plan and state.plan.search_query):
            topic = next(iter(state.reasoning.resolved_refs.values()))
            if topic.lower() not in q.lower():
                q = f"{topic} nedir"
        # Prefer live research immediately when possible (person / kimdir)
        try:
            from model import web_research

            found = web_research.research_deep(q)
            if found and found.get("answer"):
                return ToolResult(
                    name=ToolName.WEB,
                    ok=True,
                    payload={
                        "reply": found["answer"],
                        "source": "web",
                        "url": found.get("url", ""),
                        "provider": found.get("provider", ""),
                        "allow_web": False,
                    },
                )
        except Exception as exc:
            return ToolResult(
                name=ToolName.WEB,
                ok=True,
                payload={
                    "reply": "Bunu bilgi olarak araştırayım…",
                    "source": "fallback",
                    "research_query": q,
                    "allow_web": True,
                    "error": str(exc)[:120],
                },
            )
        return ToolResult(
            name=ToolName.WEB,
            ok=True,
            payload={
                "reply": "Bunu bilgi olarak araştırayım…",
                "source": "fallback",
                "research_query": q,
                "allow_web": True,
            },
        )

    def _math(self, msg: str) -> ToolResult:
        from model import skills

        ans = skills.solve_math(msg) or skills.convert_units(msg)
        if not ans:
            return ToolResult(name=ToolName.MATH, ok=False, error="not a math query")
        return ToolResult(name=ToolName.MATH, ok=True, payload={"reply": ans})

    def _translate(self, msg: str) -> ToolResult:
        from model import skills

        if not skills.looks_like_translate(msg):
            # still try
            pass
        ans = skills.translate(msg)
        if not ans:
            return ToolResult(name=ToolName.TRANSLATE, ok=False, error="no translation")
        return ToolResult(name=ToolName.TRANSLATE, ok=True, payload={"reply": ans})

    def _weather(self, msg: str) -> ToolResult:
        from model import skills

        ans = skills.answer_weather(msg)
        if not ans:
            return ToolResult(name=ToolName.WEATHER, ok=False, error="no weather")
        return ToolResult(name=ToolName.WEATHER, ok=True, payload={"reply": ans})

    def _time(self, msg: str) -> ToolResult:
        from model import skills

        ans = skills.answer_time(msg) if skills.looks_like_time(msg) else skills.answer_time("saat kaç")
        return ToolResult(name=ToolName.TIME, ok=True, payload={"reply": ans or ""})

    def _kb(self, msg: str, state: PipelineState) -> ToolResult:
        from model.brain import brain, _norm

        q = msg
        intent = state.intent.intent.value if state.intent else ""
        if state.reasoning and state.reasoning.resolved_refs:
            topic = next(iter(state.reasoning.resolved_refs.values()))
            if intent in {"explanation", "question", "search"}:
                q = f"{topic} nedir"
            elif topic.lower() not in q.lower():
                q = f"{topic} {q}"
        ranked = brain._rank_kb(_norm(q))
        if not ranked or ranked[0][1] < 2.0:
            return ToolResult(name=ToolName.KB, ok=False, error="no kb hit")
        entry = ranked[0][0]
        payload = {"reply": entry["a"], "score": ranked[0][1], "source": "kb"}
        if entry.get("c") and intent == "coding":
            payload["code"] = entry["c"]
            payload["lang"] = entry.get("l", "python")
        return ToolResult(name=ToolName.KB, ok=True, payload=payload)


tool_manager = ToolManager()
