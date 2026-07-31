"""Stage 9 — natural language generation + abstract LLM provider."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence

from .conversation import (
    anti_robotic,
    detect_chitchat_key,
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
        # Prompt is already a drafted reply in our local mode
        return (prompt or "")[: max(4000, max_tokens * 16)]


class ResponseGenerator:
    def __init__(self, llm: LLMProvider | None = None) -> None:
        self.llm = llm or LocalTemplateProvider()

    def generate(self, state: PipelineState) -> Dict[str, Any]:
        plan = state.plan or ResponsePlan()
        lang = plan.language
        tools = state.tool_results or []

        # Personality-first path for clear social acts
        chat_key = detect_chitchat_key(state.raw)
        if chat_key and (not state.intent or state.intent.intent in {
            Intent.CONVERSATION, Intent.CLARIFY, Intent.UNKNOWN, Intent.COMMAND
        }):
            name = memory_name(state.memory_hits)
            return self._with_voice(
                {
                    "reply": persona_reply(chat_key, language=lang, name=name),
                    "source": "chat",
                },
                state,
            )

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
                out = {
                    "reply": tr.payload["reply"],
                    "source": "kb",
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

        if plan.needs_clarification and plan.clarification_question:
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
        about = about or topic

        meaning = getattr(state, "meaning_notes", None) or []
        wants_continue = any("continue" in n or "incomplete" in n for n in meaning)

        if plan.language == "en":
            if intent == Intent.OPINION:
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
            if about:
                return (
                    f"{who}Keeping {about} in mind — deeper explanation, "
                    f"an example, or working code?"
                )
            if project:
                return (
                    f"{who}We're still on '{project}'. "
                    f"What should we tackle next on it?"
                )
            return (
                f"{who}I'm with you. Ask me to explain something, design code, "
                f"translate, or just talk — I'll keep the thread."
            )

        # Turkish default
        if intent == Intent.OPINION:
            return (
                f"{who}Ben kısıtlarına bakarak düşünürüm; "
                f"netlik ve sürdürülebilirlik genelde 'zeki' çözümden daha değerlidir. "
                f"İki seçeneği somut karşılaştırayım mı?"
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
        if about:
            return (
                f"{who}{about} aklımda — "
                f"daha derin açıklama, örnek, yoksa çalışan kod?"
            )
        if project:
            return (
                f"{who}'{project}' üzerindeyiz. "
                f"Sıradaki parça ne olsun?"
            )
        if intent == Intent.CONVERSATION:
            return (
                f"{who}Buradayım. İstersen bir konuyu rahatça açıklayayım, "
                f"sıfırdan kod tasarlayayım ya da sadece sohbet edelim."
            )
        return (
            f"{who}Tamam, yakaladım. Biraz daha somut yazarsan "
            f"(kavram sorusu veya 'todo yaz' gibi) doğrudan ilerlerim."
        )

    def _with_voice(self, payload: Dict[str, Any], state: PipelineState) -> Dict[str, Any]:
        plan = state.plan or ResponsePlan()
        reply = str(payload.get("reply") or "")
        reply = anti_robotic(reply)

        # Style preference from memory
        style_pref = ""
        topic = ""
        for h in state.memory_hits:
            if h.kind == "preference" and "style=" in h.content:
                style_pref = h.content.split("style=")[-1].split(",")[0].strip()
            if h.kind == "topic" and not topic:
                topic = h.content

        meaning = getattr(state, "meaning_notes", None) or []
        wants_continue = any("continue" in n or "incomplete" in n for n in meaning)
        if wants_continue and payload.get("source") in {"kb", "chat", "web"}:
            reply = weave_context_prefix(
                reply,
                topic=topic,
                language=plan.language,
                wants_continue=True,
            )

        intent = state.intent.intent if state.intent else None
        if (
            intent in {Intent.QUESTION, Intent.EXPLANATION}
            and payload.get("source") == "kb"
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
            # Keep first paragraph + last sentence if long
            parts = [p for p in reply.split("\n\n") if p.strip()]
            if len(parts) > 2:
                reply = parts[0] + "\n\n" + parts[-1]

        payload = dict(payload)
        payload["reply"] = self.llm.generate(reply)
        return payload


# Optional future providers
class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str = "", model: str = "gpt-4o-mini") -> None:
        self.api_key = api_key
        self.model = model

    def generate(self, prompt: str, *, max_tokens: int = 512) -> str:
        if not self.api_key:
            return LocalTemplateProvider().generate(prompt, max_tokens=max_tokens)
        # Placeholder — wire requests to OpenAI Chat Completions when key present
        return LocalTemplateProvider().generate(prompt, max_tokens=max_tokens)


response_generator = ResponseGenerator()
