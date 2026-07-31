"""Stage 4 — intent detection via semantic prototypes (not keyword rules)."""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np

from .embedding import EmbeddingEngine, embedding_engine
from .types import Intent, IntentResult


# Many paraphrases per intent → centroid in embedding space
_INTENT_EXAMPLES: Dict[Intent, List[str]] = {
    Intent.QUESTION: [
        "what is this",
        "how does it work",
        "can you tell me about docker",
        "react nedir",
        "bu ne anlama geliyor",
        "neden boyle oluyor",
        "who invented python",
        "when was kubernetes created",
        "farki nedir",
        "aciklar misin",
    ],
    Intent.COMMAND: [
        "open the file",
        "run the tests",
        "install the package",
        "bunu sil",
        "listele",
        "baslat",
        "stop the server",
        "deploy now",
    ],
    Intent.CONVERSATION: [
        "merhaba nasilsin",
        "hey how are you",
        "tesekkurler",
        "gorusuruz",
        "ne yapiyorsun",
        "sikildim konusaim",
        "good morning",
        "thanks a lot",
    ],
    Intent.OPINION: [
        "what do you think about this",
        "sence hangisi daha iyi",
        "ne dusunuyorsun",
        "is python better than java",
        "bence dogru mu",
        "your opinion on microservices",
    ],
    Intent.EXPLANATION: [
        "explain step by step",
        "adim adim anlat",
        "neden kullanilir detayli",
        "walk me through the process",
        "nasil calistigini uzun anlat",
        "onu daha anlat",
        "daha fazla acikla",
        "tell me more about it",
        "can you elaborate",
        "biraz daha detay",
    ],
    Intent.CODING: [
        "write a python function",
        "todo list yaz",
        "create a flask api",
        "fix this bug in my code",
        "kod yaz",
        "generate a react component",
        "sql sorgusu yaz",
        "sifre uretici yaz",
        "implement binary search",
        "chatbot yaz",
    ],
    Intent.TRANSLATION: [
        "translate to english",
        "ingilizceye cevir",
        "what does hello mean in turkish",
        "harika ingilizcede ne demek",
        "translate this sentence",
    ],
    Intent.CREATIVE: [
        "write a short story",
        "kisa bir hikaye yaz",
        "invent a poem",
        "creative name ideas",
        "siir yaz",
    ],
    Intent.PLANNING: [
        "help me plan my week",
        "proje plani yap",
        "break this into steps",
        "roadmap olustur",
        "how should i approach this project",
    ],
    Intent.SEARCH: [
        "search the web for latest news",
        "internetten bak",
        "araştır",
        "google this for me",
        "find sources about kubernetes",
        "guncel bilgi bul",
    ],
    Intent.MATH: [
        "what is 12 times 8",
        "2+2 kac",
        "calculate the square root",
        "100 / 4",
        "12*8",
        "15+7",
        "sqrt 16",
        "convert 10 km to miles",
        "kac eder 9*9",
        "hesapla 50/2",
    ],
    Intent.WEATHER: [
        "istanbul hava nasil",
        "what's the weather in ankara",
        "hava durumu",
        "kac derece",
        "izmir sicaklik",
        "will it rain today",
        "hava kac derece",
        "weather forecast turkey",
        "bugun hava nasil",
        "ankara weather celsius",
    ],
}


class IntentEngine:
    def __init__(self, emb: EmbeddingEngine | None = None) -> None:
        self.emb = emb or embedding_engine
        self._centroids: Dict[Intent, np.ndarray] = {}
        self._fit()

    def _fit(self) -> None:
        for intent, examples in _INTENT_EXAMPLES.items():
            mat = self.emb.encode_many(examples)
            centroid = mat.mean(axis=0)
            n = float(np.linalg.norm(centroid))
            if n > 1e-8:
                centroid = centroid / n
            self._centroids[intent] = centroid.astype(np.float32)

    def predict(self, text: str, embedding: np.ndarray | None = None) -> IntentResult:
        vec = embedding if embedding is not None else self.emb.encode(text)
        scores: Dict[str, float] = {}
        for intent, centroid in self._centroids.items():
            scores[intent.value] = self.emb.cosine(vec, centroid)
        ranked = sorted(scores.items(), key=lambda x: -x[1])
        top_name, top_score = ranked[0]
        second = Intent(ranked[1][0]) if len(ranked) > 1 else None
        # Softmax-ish confidence
        exps = [math_exp(s) for _, s in ranked[:5]]
        conf = exps[0] / max(sum(exps), 1e-8)
        intent = Intent(top_name)
        # Low margin → unknown/clarify
        if len(ranked) > 1 and (ranked[0][1] - ranked[1][1]) < 0.03 and top_score < 0.35:
            intent = Intent.CLARIFY
            conf *= 0.7
        return IntentResult(
            intent=intent,
            confidence=float(conf),
            scores=scores,
            secondary=second if second != intent else None,
        )


def math_exp(x: float) -> float:
    import math

    return math.exp(max(-20.0, min(20.0, x * 6.0)))


intent_engine = IntentEngine()
