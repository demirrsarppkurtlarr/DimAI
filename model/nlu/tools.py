"""Tool manager — bridges planning decisions to DimAI capabilities."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from .types import Intent, PipelineState, ResponsePlan, ToolName, ToolResult


class ToolManager:
    """Independent tool runner; each tool is optional and fail-soft."""

    # A solid hit from these tools means later/heavier tools can be skipped.
    _TERMINAL = {
        ToolName.CODEGEN,
        ToolName.MATH,
        ToolName.TRANSLATE,
        ToolName.WEATHER,
        ToolName.TIME,
    }

    def run(self, state: PipelineState) -> List[ToolResult]:
        plan = state.plan or ResponsePlan()
        results: list[ToolResult] = []
        answered = False
        for tool in plan.tools:
            # Phase 9: skip redundant work once we already have a usable answer
            if answered and tool in {ToolName.WEB, ToolName.CHAT, ToolName.KB}:
                results.append(
                    ToolResult(
                        name=tool,
                        ok=False,
                        error="skipped: earlier tool already answered",
                    )
                )
                continue
            if answered and tool == ToolName.MEMORY:
                # memory is cheap metadata; still ok but not required
                continue
            try:
                result = self._dispatch(tool, state)
            except Exception as exc:  # noqa: BLE001 — tools must not crash pipeline
                result = ToolResult(name=tool, ok=False, error=str(exc)[:200])
            results.append(result)
            if self._is_sufficient(result):
                answered = True
        return results

    @staticmethod
    def _is_sufficient(result: ToolResult) -> bool:
        if not result.ok:
            return False
        if result.name in ToolManager._TERMINAL:
            return bool(result.payload.get("reply") or result.payload.get("code"))
        if result.name == ToolName.KB:
            reply = str(result.payload.get("reply") or "")
            score = float(result.payload.get("score") or 0)
            source = str(result.payload.get("source") or "")
            meta = result.payload.get("meta") if isinstance(result.payload.get("meta"), dict) else {}
            # Weak / chatty index hits must NOT block WEB research.
            if source.startswith("kb_index"):
                if not meta.get("grounded"):
                    return False
                if score < 1.55:
                    return False
                # Reject slang / roleplay openings even if long
                head = reply[:80].casefold()
                if any(x in head for x in ("haha", "lan ", "ula ", "vallahi", "bir zamanlar")):
                    return False
            # Strong hand-KB or learned hit → skip WEB.
            if result.payload.get("code") and reply and source in {"kb", "learned"}:
                return True
            if source == "kb" and reply and score >= 2.0:
                return True
            return bool(reply) and score >= 1.55 and len(reply) >= 40
        return False

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

        # Prefer the FULL last_code store — memory hit content is only a preview.
        try:
            from model.nlu.memory import memory_engine

            prior = memory_engine.store.last_code or ""
            lang = memory_engine.store.last_lang or lang
        except Exception:
            prior = ""

        if not prior:
            for h in state.memory_hits:
                if h.kind != "code":
                    continue
                meta = h.meta or {}
                full = str(meta.get("code") or "").strip()
                if full:
                    prior = full
                    lang = str(meta.get("lang") or lang)
                    break
                if h.content and len(h.content) > 500:
                    prior = h.content
                    lang = str(meta.get("lang") or lang)
                    break

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
                if "def " in content and ("return" in content or "class " in content):
                    prior = content
                    break

        improve_ask = bool(plan and plan.improve_code)
        if not improve_ask:
            folded = (msg or "").casefold()
            improve_ask = any(
                x in folded
                for x in (
                    "geliştir", "gelistir", "improve", "refactor",
                    "optimize", "iyileştir", "iyilestir", "düzelt", "duzelt",
                )
            )

        if improve_ask and prior:
            made = codegen.improve(
                prior,
                msg,
                lang=lang,
                project_context=self._project_context(state),
                user_language=(state.plan.language if state.plan else "tr"),
            )
            if made:
                return ToolResult(name=ToolName.CODEGEN, ok=True, payload=made)

        if improve_ask and not prior:
            lang_ui = state.plan.language if state.plan else "tr"
            if lang_ui == "en":
                reply = (
                    "Improve needs the previous source. Paste the code "
                    "(or generate one first with e.g. `stok takip yaz`), "
                    "then say `improve`."
                )
            else:
                reply = (
                    "Geliştirmek için önceki kodu bulamadım. "
                    "Kodu yapıştır veya önce bir şey yazdır "
                    "(`stok takip yaz` gibi), sonra `geliştir` de."
                )
            return ToolResult(
                name=ToolName.CODEGEN,
                ok=True,
                payload={"reply": reply, "code": "", "lang": "text", "source": "codegen"},
            )

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
        # Never use web as first move for coding / full-source hunts
        intent = state.intent.intent if state.intent else None
        if intent == Intent.CODING:
            return ToolResult(
                name=ToolName.WEB,
                ok=False,
                error="policy: no web full-source for coding; use codegen",
            )
        fold = (msg or "").lower()
        if any(x in fold for x in ("github.com", "source code of", "clone repo", "full source")):
            if intent in {Intent.CODING, Intent.COMMAND}:
                return ToolResult(
                    name=ToolName.WEB,
                    ok=False,
                    error="policy: refuse full-source scrape; invent instead",
                )
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
        from model.rag import retrieve_for_tools

        q = msg
        intent = state.intent.intent.value if state.intent else ""
        if state.reasoning and state.reasoning.resolved_refs:
            topic = next(iter(state.reasoning.resolved_refs.values()))
            if intent in {"explanation", "question", "search"}:
                q = f"{topic} nedir"
            elif topic.lower() not in q.lower():
                q = f"{topic} {q}"
        payload = retrieve_for_tools(q, intent=intent)
        if not payload:
            return ToolResult(name=ToolName.KB, ok=False, error="no rag hit")
        return ToolResult(name=ToolName.KB, ok=True, payload=payload)


tool_manager = ToolManager()
