"""Stage 9 — natural language generation + abstract LLM provider."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence

from .conversation import (
    answer_comparison,
    anti_robotic,
    detect_chitchat_key,
    looks_like_new_question,
    memory_name,
    persona_reply,
    weave_context_prefix,
)
from .types import (
    Intent,
    PipelineState,
    ResponsePlan,
    ToolName,
    ToolResult,
)


class LLMProvider(ABC):
    """Swap this for OpenAI / Claude / local LLM later."""

    name: str = "base"

    @abstractmethod
    def generate(self, prompt: str, *, max_tokens: int = 512) -> str:
        raise NotImplementedError


class LocalTemplateProvider(LLMProvider):
    """Deterministic fluent generator used until an external LLM is wired."""

    name = "local-template"

    def generate(self, prompt: str, *, max_tokens: int = 512) -> str:
        return (prompt or "")[: max(4000, max_tokens * 16)]


class ResponseGenerator:
    def __init__(self, llm: LLMProvider | None = None) -> None:
        self.llm = llm or LocalTemplateProvider()

    def generate(self, state: PipelineState) -> Dict[str, Any]:
        plan = state.plan or ResponsePlan()
        lang = plan.language
        tools = state.tool_results or []

        # Exact easter eggs / special codes — whole message only
        try:
            from model import skills as _skills

            if _skills.looks_like_special_code(state.raw):
                ans = _skills.answer_special_code(state.raw)
                if ans:
                    return {"reply": ans, "source": "chat"}
        except Exception:
            pass

        # Personality / how-you-work — even if prior topic exists
        chat_key = detect_chitchat_key(state.raw)
        if chat_key:
            name = memory_name(state.memory_hits)
            return self._with_voice(
                {
                    "reply": persona_reply(chat_key, language=lang, name=name),
                    "source": "chat",
                },
                state,
            )

        # Built-in comparisons when tools didn't answer
        cmp = answer_comparison(state.raw, language=lang)
        if cmp and (
            not tools
            or all(not t.ok or t.name in {ToolName.CHAT, ToolName.MEMORY} for t in tools)
            or (
                state.intent
                and state.intent.intent == Intent.OPINION
                and not any(t.ok and t.name == ToolName.KB and t.payload.get("reply") for t in tools)
            )
        ):
            # Prefer KB if it already has a hit
            kb_hit = next(
                (t for t in tools if t.ok and t.name == ToolName.KB and t.payload.get("reply")),
                None,
            )
            if not kb_hit:
                return self._with_voice({"reply": cmp, "source": "chat"}, state)

        # Prefer successful tool payloads
        for tr in tools:
            if not tr.ok:
                continue
            if tr.name == ToolName.CODEGEN:
                reply = tr.payload.get("reply") or (
                    "İşte senin isteğine göre tasarladığım kod:"
                    if lang == "tr"
                    else "Here's code designed for your request:"
                )
                out = {
                    "reply": reply,
                    "code": tr.payload.get("code"),
                    "lang": tr.payload.get("lang", "python"),
                    "source": "codegen",
                }
                if tr.payload.get("design"):
                    out["design"] = tr.payload["design"]
                if tr.payload.get("review"):
                    out["review"] = tr.payload["review"]
                return self._with_voice(out, state)
            if tr.name in {ToolName.MATH, ToolName.TRANSLATE, ToolName.WEATHER, ToolName.TIME}:
                return self._with_voice(
                    {"reply": tr.payload.get("reply", ""), "source": tr.name.value},
                    state,
                )
            if tr.name == ToolName.KB and tr.payload.get("reply"):
                from .quality import present_code_answer

                intent_v = state.intent.intent if state.intent else None
                if tr.payload.get("code") and intent_v in {
                    Intent.QUESTION, Intent.EXPLANATION, Intent.CODING, Intent.COMMAND,
                }:
                    shaped = present_code_answer(
                        question=state.raw,
                        answer=str(tr.payload.get("reply") or ""),
                        code=str(tr.payload.get("code") or ""),
                        lang=str(tr.payload.get("lang") or "python"),
                        language=lang,
                    )
                    return self._with_voice(shaped, state)
                out = {
                    "reply": tr.payload["reply"],
                    "source": tr.payload.get("source") or "kb",
                }
                if tr.payload.get("code"):
                    out["code"] = tr.payload["code"]
                    out["lang"] = tr.payload.get("lang", "python")
                return self._with_voice(out, state)
            if tr.name == ToolName.WEB:
                src = tr.payload.get("source") or "fallback"
                out = {
                    "reply": tr.payload.get("reply", ""),
                    "source": src,
                }
                if tr.payload.get("url"):
                    out["url"] = tr.payload["url"]
                if src == "fallback":
                    out["research_query"] = tr.payload.get("research_query", state.raw)
                    out["allow_web"] = True
                return self._with_voice(out, state) if src != "fallback" else out

        # Comparison fallback after tools
        if cmp:
            return self._with_voice({"reply": cmp, "source": "chat"}, state)

        # Phase 13: knowledge index top-k, then legacy learned lookup
        try:
            from model.rag import retrieve
            from .quality import present_code_answer

            intent_v = state.intent.intent.value if state.intent and state.intent.intent else ""
            rag_hit = retrieve(state.raw, intent=intent_v) or retrieve(
                state.normalized or state.raw, intent=intent_v
            )
            if rag_hit and rag_hit.reply and len(rag_hit.reply) >= 24:
                if rag_hit.code and intent_v in {"coding", "command", "question", "explanation"}:
                    shaped = present_code_answer(
                        question=state.raw,
                        answer=rag_hit.reply,
                        code=rag_hit.code,
                        lang=rag_hit.lang or "python",
                        language=lang,
                    )
                    shaped["source"] = rag_hit.source
                    return self._with_voice(shaped, state)
                return self._with_voice(
                    {
                        "reply": rag_hit.reply,
                        "source": rag_hit.source,
                        "url": rag_hit.url or "",
                    },
                    state,
                )
        except Exception:
            pass

        try:
            from model.web_research import learned
            from .quality import present_code_answer

            hit = learned.lookup(state.raw) or learned.lookup(state.normalized or state.raw)
            if hit and hit.get("a") and len(str(hit["a"])) >= 24:
                if hit.get("c"):
                    shaped = present_code_answer(
                        question=state.raw,
                        answer=str(hit["a"]),
                        code=str(hit["c"]),
                        lang=str(hit.get("l") or "python"),
                        language=lang,
                    )
                    return self._with_voice(shaped, state)
                return self._with_voice(
                    {
                        "reply": str(hit["a"]),
                        "source": "learned",
                        "url": hit.get("url") or "",
                    },
                    state,
                )
        except Exception:
            pass

        if plan.needs_clarification and plan.clarification_question:
            # Never clarify away a clear new question
            if looks_like_new_question(state.raw):
                return self._with_voice(
                    {"reply": self._chat_fallback(state), "source": "chat"},
                    state,
                )
            return self._with_voice(
                {"reply": plan.clarification_question, "source": "chat"},
                state,
            )

        return self._with_voice({"reply": self._chat_fallback(state), "source": "chat"}, state)

    def _chat_fallback(self, state: PipelineState) -> str:
        plan = state.plan or ResponsePlan()
        name = memory_name(state.memory_hits)
        who = f"{name}, " if name else ""
        intent = state.intent.intent if state.intent else Intent.CONVERSATION
        refs = (state.reasoning.resolved_refs if state.reasoning else {}) or {}
        about = next(iter(refs.values())) if refs else ""
        topic = ""
        project = ""
        for h in state.memory_hits:
            if h.kind == "topic" and not topic:
                topic = h.content
            if h.kind == "project" and not project:
                project = h.content

        meaning = getattr(state, "meaning_notes", None) or []
        wants_continue = any("continue" in n or "incomplete" in n for n in meaning)
        fresh = looks_like_new_question(state.raw)

        # Never surface sticky project/topic prompts on fresh asks
        project = ""
        if not wants_continue:
            about = ""
            topic = ""

        if plan.language == "en":
            if intent == Intent.OPINION:
                cmp = answer_comparison(state.raw, language="en")
                if cmp:
                    return cmp
                return (
                    f"{who}I'd weigh trade-offs against your constraints — "
                    f"clarity and maintainability usually beat cleverness. "
                    f"Want two concrete options side by side?"
                )
            if intent == Intent.PLANNING:
                return (
                    f"{who}Let's slice it: clarify the goal, list constraints, "
                    f"ship the smallest useful piece, then iterate. "
                    f"Share the project and I'll draft the first steps."
                )
            if wants_continue and about:
                return (
                    f"{who}Still on {about} — I can go deeper, show an example, "
                    f"or sketch working code. Which helps more right now?"
                )
            if intent in {Intent.QUESTION, Intent.EXPLANATION, Intent.SEARCH}:
                return (
                    f"{who}I don't have a crisp answer cached for that yet. "
                    f"Ask it as 'X nedir' or say `araştır` and I'll dig in."
                )
            if intent == Intent.CONVERSATION:
                return (
                    f"{who}I'm with you. Ask me to explain something, design code, "
                    f"translate, or just talk — I'll keep the thread."
                )
            return (
                f"{who}Got it. Give me one concrete ask "
                f"(a concept, a comparison, or `todo yaz`) and I'll move."
            )

        # Turkish default
        if intent == Intent.OPINION:
            cmp = answer_comparison(state.raw, language="tr")
            if cmp:
                return cmp
            return (
                f"{who}Ben kısıtlarına bakarak düşünürüm; "
                f"netlik ve sürdürülebilirlik genelde 'zeki' çözümden daha değerlidir. "
                f"İki seçeneği isimlendirirsen somut karşılaştırırım."
            )
        if intent == Intent.PLANNING:
            return (
                f"{who}Şöyle keselim: hedefi netleştir, kısıtları yaz, "
                f"en küçük faydalı parçayı çıkar, sonra büyüt. "
                f"Projeyi söylersen ilk adımları yazarım."
            )
        if wants_continue and about:
            return (
                f"{who}{about} üzerindeyiz — daha derin anlatayım, "
                f"örnek vereyim, yoksa çalışan kod mu istersin?"
            )
        if intent in {Intent.QUESTION, Intent.EXPLANATION, Intent.SEARCH}:
            return (
                f"{who}Bunu net cevaplayamadım. "
                f"`X nedir` diye sor veya `araştır` dersen bakayım."
            )
        if intent == Intent.CONVERSATION:
            return (
                f"{who}Buradayım. İstersen bir konuyu rahatça açıklayayım, "
                f"sıfırdan kod tasarlayayım ya da sadece sohbet edelim."
            )
        return (
            f"{who}Tamam — somut bir istek yaz "
            f"(karşılaştırma, kavram veya `todo yaz`) doğrudan ilerlerim."
        )

    def _with_voice(self, payload: Dict[str, Any], state: PipelineState) -> Dict[str, Any]:
        from .quality import lead_with_answer, polish

        plan = state.plan or ResponsePlan()
        reply = str(payload.get("reply") or "")
        reply = anti_robotic(reply)
        reply = polish(reply, language=plan.language)

        style_pref = ""
        topic = ""
        for h in state.memory_hits:
            if h.kind == "preference" and "style=" in h.content:
                style_pref = h.content.split("style=")[-1].split(",")[0].strip()
            if h.kind == "topic" and not topic:
                topic = h.content

        meaning = getattr(state, "meaning_notes", None) or []
        wants_continue = any("continue" in n or "incomplete" in n for n in meaning)
        if wants_continue and payload.get("source") in {"kb", "chat", "web", "learned"}:
            reply = weave_context_prefix(
                reply,
                topic=topic,
                language=plan.language,
                wants_continue=True,
            )

        intent = state.intent.intent if state.intent else None
        if (
            intent in {Intent.QUESTION, Intent.EXPLANATION}
            and payload.get("source") in {"kb", "learned"}
            and not payload.get("code")
            and "ister" not in reply.lower()
            and "want" not in reply.lower()
            and len(reply) < 600
            and style_pref != "concise"
        ):
            follow = (
                "\n\nİstersen bunun üzerine küçük bir örnek de kurabilirim."
                if plan.language == "tr"
                else "\n\nI can also sketch a small example on top of this."
            )
            reply = reply.rstrip() + follow

        if style_pref == "concise" and len(reply) > 400:
            parts = [p for p in reply.split("\n\n") if p.strip()]
            if len(parts) > 2:
                reply = parts[0] + "\n\n" + parts[-1]

        reply = lead_with_answer(reply, language=plan.language)
        payload = dict(payload)
        payload["reply"] = self.llm.generate(reply)
        return payload


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str = "", model: str = "gpt-4o-mini") -> None:
        self.api_key = api_key
        self.model = model

    def generate(self, prompt: str, *, max_tokens: int = 512) -> str:
        if not self.api_key:
            return LocalTemplateProvider().generate(prompt, max_tokens=max_tokens)
        return LocalTemplateProvider().generate(prompt, max_tokens=max_tokens)


response_generator = ResponseGenerator()
