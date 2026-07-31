"""Stage 9 — natural language generation + abstract LLM provider."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence

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
        return (prompt or "")[: max(200, max_tokens * 8)]


class ResponseGenerator:
    def __init__(self, llm: LLMProvider | None = None) -> None:
        self.llm = llm or LocalTemplateProvider()

    def generate(self, state: PipelineState) -> Dict[str, Any]:
        plan = state.plan or ResponsePlan()
        lang = plan.language
        tools = state.tool_results or []

        # Prefer successful tool payloads
        for tr in tools:
            if not tr.ok:
                continue
            if tr.name == ToolName.CODEGEN:
                return self._with_voice(
                    {
                        "reply": tr.payload.get("reply") or ("İşte kod:" if lang == "tr" else "Here is the code:"),
                        "code": tr.payload.get("code"),
                        "lang": tr.payload.get("lang", "python"),
                        "source": "codegen",
                    },
                    state,
                )
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
                return {
                    "reply": tr.payload.get("reply", ""),
                    "source": "fallback",
                    "research_query": tr.payload.get("research_query", state.raw),
                    "allow_web": True,
                }

        if plan.needs_clarification and plan.clarification_question:
            return self._with_voice(
                {"reply": plan.clarification_question, "source": "chat"},
                state,
            )

        return self._with_voice({"reply": self._chat_fallback(state), "source": "chat"}, state)

    def _chat_fallback(self, state: PipelineState) -> str:
        plan = state.plan or ResponsePlan()
        name = ""
        for h in state.memory_hits:
            if h.kind == "preference" and "name=" in h.content:
                name = h.content.split("name=")[-1].split(",")[0].strip()
                break
        who = f"{name}, " if name else ""
        intent = state.intent.intent if state.intent else Intent.CONVERSATION
        refs = (state.reasoning.resolved_refs if state.reasoning else {}) or {}
        about = next(iter(refs.values())) if refs else ""

        if plan.language == "en":
            if intent == Intent.OPINION:
                return (
                    f"{who}I think it depends on your constraints — "
                    f"for most teams, clarity and maintainability beat cleverness. "
                    f"Want me to compare two options specifically?"
                )
            if intent == Intent.PLANNING:
                return (
                    f"{who}Let's break it down: 1) define the goal, 2) list constraints, "
                    f"3) pick the smallest shippable slice, 4) iterate. "
                    f"Tell me the project and I'll draft a concrete plan."
                )
            if about:
                return (
                    f"{who}Continuing on {about}: what do you want next — "
                    f"a deeper explanation, an example, or working code?"
                )
            return (
                f"{who}I'm here with you. Ask me to explain something, write code, "
                f"translate, or just chat — I'll keep the thread in mind."
            )

        # Turkish default
        if intent == Intent.OPINION:
            return (
                f"{who}Bence en iyi seçim bağlama göre değişir; "
                f"netlik ve sürdürülebilirlik genelde 'zeki' çözümden daha değerlidir. "
                f"İki seçeneği somut karşılaştırayım mı?"
            )
        if intent == Intent.PLANNING:
            return (
                f"{who}Şöyle ilerleyelim: 1) hedefi netleştir, 2) kısıtları yaz, "
                f"3) en küçük teslim edilebilir parçayı seç, 4) döngüyle büyüt. "
                f"Projeyi söylersen adım adım plan çıkarırım."
            )
        if about:
            return (
                f"{who}{about} konusunda devam ediyorum — "
                f"daha derin açıklama, örnek, yoksa çalışan kod ister misin?"
            )
        if intent == Intent.CONVERSATION:
            return (
                f"{who}Buradayım 🙂 İstersen bir konuyu açıklayayım, kod yazayım "
                f"veya sadece sohbet edelim — sen seç."
            )
        return (
            f"{who}Anladım. İsteğini biraz daha somut yazarsan "
            f"(ör. bir kavram sorusu veya 'todo yaz') doğrudan ilerlerim."
        )

    def _with_voice(self, payload: Dict[str, Any], state: PipelineState) -> Dict[str, Any]:
        plan = state.plan or ResponsePlan()
        reply = str(payload.get("reply") or "")
        if plan.style == "step_by_step" and reply and "\n" not in reply and len(reply) > 80:
            # Light structuring without sounding robotic
            reply = reply
        # Soft follow-up for short factual answers
        intent = state.intent.intent if state.intent else None
        if (
            intent in {Intent.QUESTION, Intent.EXPLANATION}
            and payload.get("source") == "kb"
            and "ister" not in reply.lower()
            and len(reply) < 600
        ):
            follow = (
                "\n\nİstersen bunun üzerine örnek de yazabilirim."
                if plan.language == "tr"
                else "\n\nI can also add a concrete example if you want."
            )
            reply = reply.rstrip() + follow
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
