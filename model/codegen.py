"""DimAI code synthesizer — design-first, project-fitted code generation.

Phase 3 flow: DesignSpec → implement → review.
Does not search the web for full source implementations; composes locally.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Callable, Optional


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().replace("ı", "i").replace("İ", "i")
    text = re.sub(r"[^\w\s+#./-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


STOP = {
    "bir", "bana", "benim", "icin", "ile", "ve", "veya", "kod", "kodu", "code",
    "yaz", "write", "olustur", "uret", "generate", "yap", "lutfen", "please",
    "ornek", "ornegi", "ornekler", "example", "goster", "show", "sample",
    "program", "script", "fonksiyon", "function", "class", "python", "js",
    "javascript", "typescript", "java", "basit", "mini", "kucuk", "hizli",
    "tam", "komple", "calisir", "calisan", "bana", "suan", "simdi", "hemen",
}


def _words(text: str) -> list[str]:
    return [w for w in _norm(text).split() if w and w not in STOP and len(w) > 1]


def _slug(text: str, default: str = "uygulama") -> str:
    parts = [re.sub(r"[^a-z0-9_]", "", w) for w in _words(text)]
    parts = [p for p in parts if p and not p.isdigit()]
    if not parts:
        return default
    name = "_".join(parts[:3])
    if name[0].isdigit():
        name = "fn_" + name
    return name[:40]


def _detect_lang(text: str) -> str:
    n = _norm(text)
    if any(x in n for x in ("javascript", " js", "js ", "node", "react", "typescript", " ts")):
        return "javascript"
    if "html" in n or "css" in n:
        return "html"
    if "sql" in n:
        return "sql"
    if "bash" in n or "shell" in n:
        return "bash"
    if "java" in n and "javascript" not in n:
        return "java"
    return "python"


# -------------------- generators --------------------

def _gen_guess_game(_: str) -> tuple[str, str, str]:
    code = '''import random

def oyna(alt: int = 1, ust: int = 100, hak: int = 7) -> None:
    hedef = random.randint(alt, ust)
    print(f"{alt}-{ust} arası sayı tuttum. {hak} hakkın var!")
    for kalan in range(hak, 0, -1):
        try:
            tahmin = int(input(f"Tahmin ({kalan} hak): ").strip())
        except ValueError:
            print("Sayı gir.")
            continue
        if tahmin == hedef:
            print("Bildin!")
            return
        print("Daha küçük!" if tahmin > hedef else "Daha büyük!")
    print(f"Bitti. Sayı {hedef} idi.")

if __name__ == "__main__":
    oyna()
'''
    return "Sayı tahmin oyunu — sıfırdan yazıldı:", code, "python"


def _gen_rps(_: str) -> tuple[str, str, str]:
    code = '''"""Taş-kağıt-makas — skor tablolu, doğrulamalı tam sürüm."""
from __future__ import annotations

import random
from dataclasses import dataclass, field


SECENEK = ("tas", "kagit", "makas")
KAZANIR = {("tas", "makas"), ("kagit", "tas"), ("makas", "kagit")}
TR = {"tas": "taş", "kagit": "kağıt", "makas": "makas"}


def normalize_secim(raw: str) -> str | None:
    s = (
        raw.strip()
        .lower()
        .replace("ğ", "g")
        .replace("ı", "i")
        .replace("ş", "s")
        .replace("ç", "c")
    )
    aliases = {
        "t": "tas",
        "tas": "tas",
        "rock": "tas",
        "k": "kagit",
        "kagit": "kagit",
        "paper": "kagit",
        "m": "makas",
        "makas": "makas",
        "scissors": "makas",
    }
    return aliases.get(s)


@dataclass
class Skor:
    sen: int = 0
    bot: int = 0
    berabere: int = 0
    gecmis: list[str] = field(default_factory=list)

    def kaydet(self, sonuc: str, satir: str) -> None:
        if sonuc == "sen":
            self.sen += 1
        elif sonuc == "bot":
            self.bot += 1
        else:
            self.berabere += 1
        self.gecmis.append(satir)

    def ozet(self) -> str:
        return f"Skor → Sen {self.sen} | Bot {self.bot} | Berabere {self.berabere}"


def tur(skor: Skor) -> str:
    ham = input("taş / kağıt / makas (q=çık): ").strip()
    if ham.lower() in {"q", "quit", "cikis", "çıkış"}:
        return "CIKIS"
    sen = normalize_secim(ham)
    if sen is None:
        return "Geçersiz seçim. Örnek: taş / k / paper"
    bot = random.choice(SECENEK)
    if sen == bot:
        sonuc, etiket = "berabere", "Berabere"
    elif (sen, bot) in KAZANIR:
        sonuc, etiket = "sen", "Sen kazandın"
    else:
        sonuc, etiket = "bot", "Bot kazandı"
    satir = f"Sen: {TR[sen]} | Bot: {TR[bot]} → {etiket}"
    skor.kaydet(sonuc, satir)
    return f"{satir}\\n{skor.ozet()}"


def main() -> None:
    print("=== Taş-Kağıt-Makas ===")
    print("İpuçu: t/k/m kısayolları çalışır. Çıkmak için q.")
    skor = Skor()
    while True:
        out = tur(skor)
        if out == "CIKIS":
            break
        print(out)
        print("-" * 40)
    print("Oyun bitti.", skor.ozet())
    if skor.gecmis:
        print("Son 3 tur:")
        for s in skor.gecmis[-3:]:
            print(" •", s)


if __name__ == "__main__":
    main()
'''
    return "Skor tablolu taş-kağıt-makas (gelişmiş sürüm):", code, "python"


def improve(
    prior_code: str,
    request: str = "",
    *,
    lang: str = "python",
    project_context: str = "",
    user_language: str = "tr",
) -> Optional[dict]:
    """Önceki kodu mimariyle geliştir — tutorial yapıştırma yok."""
    prior = (prior_code or "").strip()
    if not prior:
        return None
    n = _norm(request)
    low = prior.lower()

    from model.code_design import compare_alternatives, design
    from model.code_engineer import implement
    from model.code_review import apply_fixes, review

    # Known family → redesigned richer variant under DesignSpec
    domain_hint = ""
    if ("tas" in low and "makas" in low) or ("rock" in low and "paper" in low):
        domain_hint = "skor tablolu tas kagit makas oyunu gelistir"
    elif "randint" in low and ("tahmin" in low or "guess" in low or "hedef" in low):
        domain_hint = "zorluk seviyeli sayi tahmin oyunu gelistir"
    elif "todo" in low or "yapilacak" in low or "maddeler" in low:
        domain_hint = "todo list uygulamasini gelistir ara tamamla kaydet"

    if domain_hint:
        spec = design(
            f"{domain_hint} {request}".strip(),
            project_context=project_context,
            prior_code=prior,
            improve=True,
        )
        for line in compare_alternatives(spec):
            spec.architecture_notes.append(line)
        payload = implement(spec, user_language=user_language)
        payload["reply"] = (
            ("Önceki kodun amacını koruyup mimariyi yükselttim:\n\n" if user_language != "en" else "Kept prior intent, raised the architecture:\n\n")
            + payload["reply"]
        )
        report = review(str(payload.get("code") or ""), spec, lang=str(payload.get("lang") or lang))
        payload = apply_fixes(payload, report)
        payload["review"] = {
            "score": report.score,
            "originality": report.originality,
            "issues": report.issues,
            "suggestions": report.suggestions,
        }
        return payload

    # Generic: wrap prior into a modular shell designed for this project
    slug = _slug(request) if request else "gelistirilmis"
    req_note = request or "daha iyi / daha uzun"
    req_safe = req_note.replace('"""', "'")
    spec = design(
        req_note,
        project_context=project_context,
        prior_code=prior,
        improve=True,
    )
    improved = (
        '"""Geliştirilmiş sürüm — DimAI design-first improvement.\n\n'
        f"İstek: {req_safe}\n"
        "Kararlar: domain logic korunur; I/O ve hata yönetimi sınırda toplanır.\n"
        '"""\n'
        "from __future__ import annotations\n\n"
        "import traceback\n"
        "from dataclasses import dataclass, field\n"
        "from pathlib import Path\n"
        "from typing import Any\n\n\n"
        "# --- prior logic (preserved, then orchestrated) ---\n"
        + prior
        + "\n\n\n"
        "@dataclass\n"
        "class AppState:\n"
        '    """Runtime façade — logging + settings (SRP)."""\n'
        "    logs: list[str] = field(default_factory=list)\n"
        '    ayarlar: dict[str, Any] = field(default_factory=lambda: {"debug": True})\n\n'
        "    def log(self, msg: str) -> None:\n"
        "        self.logs.append(msg)\n"
        "        print(msg)\n\n\n"
        "def guvenli_calistir(fn, *args, **kwargs):\n"
        "    try:\n"
        "        return fn(*args, **kwargs)\n"
        "    except Exception as exc:\n"
        '        print("Hata:", exc)\n'
        "        traceback.print_exc()\n"
        "        return None\n\n\n"
        f'def kaydet_log(path: str = "{slug}_log.txt") -> None:\n'
        "    p = Path(path)\n"
        '    p.write_text("calistirildi\\n", encoding="utf-8")\n'
        '    print("Log yazildi:", p.resolve())\n\n\n'
        "def main() -> None:\n"
        "    state = AppState()\n"
        '    state.log("Gelistirilmis uygulama basladi.")\n'
        "    for name, obj in list(globals().items()):\n"
        '        if name.startswith("_") or name in {"main", "guvenli_calistir", "kaydet_log", "AppState"}:\n'
        "            continue\n"
        '        if callable(obj) and getattr(obj, "__module__", "") == "__main__":\n'
        '            state.log(f"fonksiyon hazir: {name}()")\n'
        "    kaydet_log()\n"
        '    state.log("Bitti. Istersen fonksiyonlari dogrudan cagir.")\n\n\n'
        'if __name__ == "__main__":\n'
        "    main()\n"
    )
    payload = {
        "reply": (
            "Önceki kodunu bozmadan mimari kabuk ekledim: durum nesnesi, hata sınırı, "
            "log ve `main` orkestrasyonu — tutorial kopyası değil, senin koda göre uyarlandı.\n\n"
            + "\n".join(spec.summary_lines(language=user_language))
        ),
        "code": improved.strip() + "\n",
        "lang": lang or "python",
        "source": "codegen",
        "design": {
            "goal": spec.goal,
            "problem_type": spec.problem_type,
            "confidence": spec.confidence,
        },
    }
    report = review(payload["code"], spec, lang=payload["lang"])
    payload = apply_fixes(payload, report)
    payload["review"] = {
        "score": report.score,
        "originality": report.originality,
        "issues": report.issues,
        "suggestions": report.suggestions,
    }
    return payload


def _gen_guess_game_rich(_: str) -> tuple[str, str, str]:
    code = '''"""Sayı tahmin — zorluk seviyeli, istatistikli sürüm."""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class Istatistik:
    deneme: int = 0
    galibiyet: int = 0

    def ozet(self) -> str:
        return f"Toplam deneme: {self.deneme} | Kazanma: {self.galibiyet}"


ZORLUK = {
    "1": (1, 50, 8, "Kolay"),
    "2": (1, 100, 7, "Normal"),
    "3": (1, 200, 6, "Zor"),
}


def oyna_bir_tur(stats: Istatistik) -> None:
    print("Zorluk: 1) Kolay  2) Normal  3) Zor")
    sec = input("> ").strip() or "2"
    alt, ust, hak, ad = ZORLUK.get(sec, ZORLUK["2"])
    hedef = random.randint(alt, ust)
    print(f"{ad}: {alt}-{ust} arası, {hak} hak.")
    for kalan in range(hak, 0, -1):
        stats.deneme += 1
        try:
            tahmin = int(input(f"Tahmin ({kalan} hak): ").strip())
        except ValueError:
            print("Sayı gir.")
            continue
        if tahmin == hedef:
            stats.galibiyet += 1
            print(f"Bildin! Kalan hak: {kalan - 1}")
            return
        fark = abs(tahmin - hedef)
        ipucu = "çok yakınsın" if fark <= 5 else ("yaklaştın" if fark <= 15 else "")
        yon = "Daha küçük!" if tahmin > hedef else "Daha büyük!"
        print(yon, ipucu)
    print(f"Bitti. Sayı {hedef} idi.")


def main() -> None:
    stats = Istatistik()
    while True:
        oyna_bir_tur(stats)
        print(stats.ozet())
        if input("Tekrar? (e/h): ").strip().lower() != "e":
            break
    print("Görüşürüz.", stats.ozet())


if __name__ == "__main__":
    main()
'''
    return "Zorluk seviyeli sayı tahmin oyunu:", code, "python"


def _gen_todo_rich(_: str) -> tuple[str, str, str]:
    code = '''"""TODO — JSON kalıcı, tamamlandı / ara / sil."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


DOSYA = Path("todo_rich.json")


@dataclass
class Madde:
    text: str
    done: bool = False


@dataclass
class TodoApp:
    maddeler: list[Madde] = field(default_factory=list)

    def yukle(self) -> None:
        if not DOSYA.exists():
            return
        ham = json.loads(DOSYA.read_text(encoding="utf-8"))
        self.maddeler = [Madde(**x) for x in ham]

    def kaydet(self) -> None:
        DOSYA.write_text(
            json.dumps([asdict(m) for m in self.maddeler], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def ekle(self, text: str) -> None:
        self.maddeler.append(Madde(text=text.strip()))
        self.kaydet()

    def bitir(self, no: int) -> bool:
        if 1 <= no <= len(self.maddeler):
            self.maddeler[no - 1].done = True
            self.kaydet()
            return True
        return False

    def sil(self, no: int) -> bool:
        if 1 <= no <= len(self.maddeler):
            self.maddeler.pop(no - 1)
            self.kaydet()
            return True
        return False

    def ara(self, q: str) -> list[tuple[int, Madde]]:
        q = q.lower()
        return [(i, m) for i, m in enumerate(self.maddeler, 1) if q in m.text.lower()]

    def listele(self) -> None:
        if not self.maddeler:
            print("(boş)")
            return
        for i, m in enumerate(self.maddeler, 1):
            mark = "✓" if m.done else "·"
            print(f"{i}. [{mark}] {m.text}")


def main() -> None:
    app = TodoApp()
    app.yukle()
    print("Komutlar: ekle <t> | bitir <n> | sil <n> | ara <q> | liste | cikis")
    while True:
        ham = input("> ").strip()
        if not ham:
            continue
        if ham == "cikis":
            break
        if ham == "liste":
            app.listele()
            continue
        if ham.startswith("ekle "):
            app.ekle(ham[5:])
            print("eklendi")
            continue
        if ham.startswith("bitir "):
            ok = app.bitir(int(ham.split()[1]))
            print("ok" if ok else "geçersiz no")
            continue
        if ham.startswith("sil "):
            ok = app.sil(int(ham.split()[1]))
            print("silindi" if ok else "geçersiz no")
            continue
        if ham.startswith("ara "):
            hits = app.ara(ham[4:])
            for i, m in hits:
                print(f"{i}. {m.text}")
            if not hits:
                print("yok")
            continue
        print("anlamadım")


if __name__ == "__main__":
    main()
'''
    return "Gelişmiş TODO (JSON + tamamlandı + arama):", code, "python"


def _gen_hangman(_: str) -> tuple[str, str, str]:
    code = '''import random

KELIMELER = ["python", "flask", "veri", "algoritma", "fonksiyon", "degisken"]

def oyna() -> None:
    gizli = random.choice(KELIMELER)
    bilinen = set()
    hak = 6
    while hak > 0:
        gorunen = " ".join(c if c in bilinen else "_" for c in gizli)
        print(gorunen, f"(hak={hak})")
        if "_" not in gorunen.replace(" ", ""):
            print("Kazandın!")
            return
        harf = input("Harf: ").strip().lower()[:1]
        if not harf.isalpha():
            continue
        if harf in gizli:
            bilinen.add(harf)
        else:
            hak -= 1
    print("Kaybettin. Kelime:", gizli)

if __name__ == "__main__":
    oyna()
'''
    return "Adam asmaca oyunu:", code, "python"


def _gen_tic_tac_toe(_: str) -> tuple[str, str, str]:
    code = '''def tablo(b: list[str]) -> None:
    print(f"\\n {b[0]} | {b[1]} | {b[2]}\\n---+---+---\\n {b[3]} | {b[4]} | {b[5]}\\n---+---+---\\n {b[6]} | {b[7]} | {b[8]}\\n")

def kazanan(b: list[str]) -> str | None:
    lines = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
    for a, c, d in lines:
        if b[a] == b[c] == b[d] != " ":
            return b[a]
    return None

def oyna() -> None:
    b = [" "] * 9
    sıra = "X"
    for _ in range(9):
        tablo(b)
        try:
            i = int(input(f"{sıra} (1-9): ")) - 1
        except ValueError:
            continue
        if i not in range(9) or b[i] != " ":
            print("Dolu/geçersiz.")
            continue
        b[i] = sıra
        if kazanan(b):
            tablo(b)
            print(sıra, "kazandı!")
            return
        sıra = "O" if sıra == "X" else "X"
    tablo(b)
    print("Berabere.")

if __name__ == "__main__":
    oyna()
'''
    return "XOX (tic-tac-toe):", code, "python"


def _gen_todo(_: str) -> tuple[str, str, str]:
    code = '''from pathlib import Path

DOSYA = Path("todo.txt")

def yukle() -> list[str]:
    if not DOSYA.exists():
        return []
    return [s.strip() for s in DOSYA.read_text(encoding="utf-8").splitlines() if s.strip()]

def kaydet(maddeler: list[str]) -> None:
    DOSYA.write_text("\\n".join(maddeler) + ("\\n" if maddeler else ""), encoding="utf-8")

def main() -> None:
    maddeler = yukle()
    while True:
        print("\\n--- TODO ---")
        for i, m in enumerate(maddeler, 1):
            print(f"{i}. {m}")
        print("komut: ekle <metin> | sil <no> | cikis")
        komut = input("> ").strip()
        if komut == "cikis":
            break
        if komut.startswith("ekle "):
            maddeler.append(komut[5:].strip())
            kaydet(maddeler)
        elif komut.startswith("sil "):
            try:
                i = int(komut.split()[1]) - 1
                maddeler.pop(i)
                kaydet(maddeler)
            except (ValueError, IndexError):
                print("Geçersiz numara.")
        else:
            print("Anlamadım.")

if __name__ == "__main__":
    main()
'''
    return "Dosyaya yazılan TODO listesi:", code, "python"


def _gen_calculator(_: str) -> tuple[str, str, str]:
    code = '''def hesapla(ifade: str) -> float:
    izin = set("0123456789+-*/(). %")
    if not ifade or any(c not in izin for c in ifade):
        raise ValueError("Sadece sayılar ve + - * / ( ) .")
    return float(eval(ifade, {"__builtins__": {}}, {}))

def main() -> None:
    print("Hesap makinesi — çıkmak için q")
    while True:
        s = input("> ").strip()
        if s.lower() in {"q", "quit", "cikis"}:
            break
        try:
            print("=", hesapla(s))
        except Exception as e:
            print("Hata:", e)

if __name__ == "__main__":
    main()
'''
    return "Güvenli hesap makinesi:", code, "python"


def _gen_password(_: str) -> tuple[str, str, str]:
    code = '''import argparse
import secrets
import string

def uret(uzunluk: int = 16, sembol: bool = True) -> str:
    havuz = string.ascii_letters + string.digits
    if sembol:
        havuz += "!@#$%^&*_-+=?"
    if uzunluk < 4:
        raise ValueError("En az 4 karakter")
    return "".join(secrets.choice(havuz) for _ in range(uzunluk))

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Şifre üretici")
    p.add_argument("-n", type=int, default=16, help="uzunluk")
    p.add_argument("--no-symbol", action="store_true")
    args = p.parse_args()
    print(uret(args.n, not args.no_symbol))
'''
    return "Güçlü rastgele şifre üretici:", code, "python"


def _gen_flask_api(_: str) -> tuple[str, str, str]:
    code = '''from flask import Flask, jsonify, request

app = Flask(__name__)
items: list[dict] = []
_next_id = 1

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/items")
def list_items():
    return jsonify(items)

@app.post("/items")
def add_item():
    global _next_id
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    if not title:
        return jsonify({"error": "title gerekli"}), 400
    item = {"id": _next_id, "title": title}
    _next_id += 1
    items.append(item)
    return jsonify(item), 201

@app.delete("/items/<int:item_id>")
def delete_item(item_id: int):
    global items
    before = len(items)
    items = [x for x in items if x["id"] != item_id]
    if len(items) == before:
        return jsonify({"error": "yok"}), 404
    return "", 204

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5055, debug=True)
'''
    return "Flask mini REST API (CRUD):", code, "python"


def _gen_fastapi(_: str) -> tuple[str, str, str]:
    code = '''from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Mini API")
db: dict[int, str] = {}
_next = 1

class ItemIn(BaseModel):
    title: str

@app.get("/items")
def list_items():
    return [{"id": k, "title": v} for k, v in db.items()]

@app.post("/items")
def create_item(body: ItemIn):
    global _next
    db[_next] = body.title.strip()
    item = {"id": _next, "title": db[_next]}
    _next += 1
    return item

@app.delete("/items/{item_id}")
def remove(item_id: int):
    if item_id not in db:
        raise HTTPException(404, "yok")
    del db[item_id]
    return {"ok": True}

# çalıştır: uvicorn main:app --reload
'''
    return "FastAPI mini CRUD:", code, "python"


def _gen_cli_chatbot(_: str) -> tuple[str, str, str]:
    code = '''import re

KURALLAR = [
    (r"merhaba|selam|hey", "Merhaba! Nasıl yardımcı olayım?"),
    (r"ad(in|ın)?\\s*(ne|nedir)", "Ben küçük bir kural tabanlı botum."),
    (r"nasilsin|naber", "İyiyim, teşekkürler! Sen nasılsın?"),
    (r"saat|time", "Saati sisteminden okumuyorum; `saat kaç` diye DimAI'ye sor."),
    (r"tesekkur|saol|eyvallah", "Rica ederim!"),
    (r"gorusuruz|bye|cikis|quit", "Görüşürüz!"),
]

def cevapla(mesaj: str) -> str:
    n = mesaj.lower()
    for desen, yanit in KURALLAR:
        if re.search(desen, n):
            return yanit
    return "Tam anlayamadım. Merhaba, adın ne, nasılsın diyebilirsin."

def main() -> None:
    print("Chatbot hazır. Çıkmak: quit")
    while True:
        msg = input("sen> ").strip()
        if not msg:
            continue
        yanit = cevapla(msg)
        print("bot>", yanit)
        if re.search(r"gorusuruz|bye|cikis|quit", msg.lower()):
            break

if __name__ == "__main__":
    main()
'''
    return "Kural tabanlı CLI chatbot:", code, "python"


def _gen_quiz(_: str) -> tuple[str, str, str]:
    code = '''SORULAR = [
    ("Python'da liste dilimleme hangi sözdizimi?", "a[start:stop]"),
    ("HTTP 404 ne demek?", "bulunamadı"),
    ("Git'te değişiklikleri kaydetmek?", "commit"),
]

def oyna() -> None:
    skor = 0
    for soru, dogru in SORULAR:
        print("\\n?", soru)
        cevap = input("> ").strip().lower()
        if dogru.lower() in cevap or cevap == dogru.lower():
            print("Doğru!")
            skor += 1
        else:
            print("Yanlış. Doğru:", dogru)
    print(f"\\nSkor: {skor}/{len(SORULAR)}")

if __name__ == "__main__":
    oyna()
'''
    return "Basit quiz uygulaması:", code, "python"


def _gen_file_stats(_: str) -> tuple[str, str, str]:
    code = '''from pathlib import Path
import sys

def analiz(yol: str) -> None:
    p = Path(yol)
    if not p.exists():
        print("Dosya yok:", yol)
        return
    text = p.read_text(encoding="utf-8", errors="ignore")
    satir = text.splitlines()
    kelime = text.split()
    print(f"dosya   : {p}")
    print(f"boyut   : {p.stat().st_size} bayt")
    print(f"satır   : {len(satir)}")
    print(f"kelime  : {len(kelime)}")
    print(f"karakter: {len(text)}")

if __name__ == "__main__":
    hedef = sys.argv[1] if len(sys.argv) > 1 else "todo.txt"
    analiz(hedef)
'''
    return "Dosya istatistikleri:", code, "python"


def _gen_csv_filter(_: str) -> tuple[str, str, str]:
    code = '''import csv
import sys
from pathlib import Path

def filtrele(giris: str, sutun: str, deger: str, cikis: str) -> None:
    with open(giris, newline="", encoding="utf-8") as f:
        okuyucu = csv.DictReader(f)
        satirlar = [r for r in okuyucu if r.get(sutun, "") == deger]
        alanlar = okuyucu.fieldnames or []
    with open(cikis, "w", newline="", encoding="utf-8") as f:
        yaz = csv.DictWriter(f, fieldnames=alanlar)
        yaz.writeheader()
        yaz.writerows(satirlar)
    print(f"{len(satirlar)} satır → {cikis}")

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("kullanım: python app.py girdi.csv sutun deger cikti.csv")
        raise SystemExit(1)
    filtrele(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
'''
    return "CSV filtreleme aracı:", code, "python"


def _gen_http_get(_: str) -> tuple[str, str, str]:
    code = '''import json
import urllib.request

def getir(url: str, timeout: int = 20) -> dict | list | str:
    req = urllib.request.Request(url, headers={"User-Agent": "DimAI/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", errors="replace")
        ctype = r.headers.get("Content-Type", "")
    if "json" in ctype or raw[:1] in "[{":
        return json.loads(raw)
    return raw

if __name__ == "__main__":
    data = getir("https://httpbin.org/get")
    print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
'''
    return "HTTP GET örneği (urllib):", code, "python"


def _gen_json_crud(_: str) -> tuple[str, str, str]:
    code = '''import json
from pathlib import Path

DB = Path("data.json")

def yukle() -> list[dict]:
    if not DB.exists():
        return []
    return json.loads(DB.read_text(encoding="utf-8"))

def kaydet(veri: list[dict]) -> None:
    DB.write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")

def ekle(baslik: str) -> dict:
    veri = yukle()
    item = {"id": (max((x["id"] for x in veri), default=0) + 1), "title": baslik}
    veri.append(item)
    kaydet(veri)
    return item

def sil(item_id: int) -> bool:
    veri = yukle()
    yeni = [x for x in veri if x["id"] != item_id]
    if len(yeni) == len(veri):
        return False
    kaydet(yeni)
    return True

if __name__ == "__main__":
    print(ekle("İlk kayıt"))
    print(yukle())
'''
    return "JSON dosyasında CRUD:", code, "python"


def _gen_regex_email(_: str) -> tuple[str, str, str]:
    code = '''import re

EMAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$")

def gecerli_mi(adres: str) -> bool:
    return bool(EMAIL.match(adres.strip()))

if __name__ == "__main__":
    for a in ["ali@ornek.com", "kötü@", "a.b+c@x.co"]:
        print(a, "→", gecerli_mi(a))
'''
    return "E-posta doğrulama (regex):", code, "python"


def _gen_fibonacci(_: str) -> tuple[str, str, str]:
    code = '''def fibonacci(n: int) -> list[int]:
    if n <= 0:
        return []
    dizi = [0, 1]
    while len(dizi) < n:
        dizi.append(dizi[-1] + dizi[-2])
    return dizi[:n]

if __name__ == "__main__":
    print(fibonacci(10))
'''
    return "Fibonacci dizisi:", code, "python"


def _gen_binary_search(_: str) -> tuple[str, str, str]:
    code = '''def binary_search(arr: list[int], hedef: int) -> int:
    """Sıralı listede hedef index'i; yoksa -1."""
    sol, sag = 0, len(arr) - 1
    while sol <= sag:
        orta = (sol + sag) // 2
        if arr[orta] == hedef:
            return orta
        if arr[orta] < hedef:
            sol = orta + 1
        else:
            sag = orta - 1
    return -1

if __name__ == "__main__":
    veri = [1, 3, 5, 7, 9, 11, 15]
    print(binary_search(veri, 7))   # 3
    print(binary_search(veri, 8))   # -1
'''
    return "Binary search:", code, "python"


def _gen_sort(_: str) -> tuple[str, str, str]:
    code = '''def bubble_sort(arr: list[int]) -> list[int]:
    a = arr[:]
    n = len(a)
    for i in range(n):
        for j in range(0, n - i - 1):
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
    return a

def quick_sort(arr: list[int]) -> list[int]:
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    sol = [x for x in arr if x < pivot]
    orta = [x for x in arr if x == pivot]
    sag = [x for x in arr if x > pivot]
    return quick_sort(sol) + orta + quick_sort(sag)

if __name__ == "__main__":
    ornek = [5, 1, 9, 3, 7, 2]
    print("bubble:", bubble_sort(ornek))
    print("quick :", quick_sort(ornek))
'''
    return "Sıralama algoritmaları:", code, "python"


def _gen_countdown(_: str) -> tuple[str, str, str]:
    code = '''import time

def geri_say(saniye: int) -> None:
    for kalan in range(saniye, 0, -1):
        print(f"\\r{kalan:3d} ", end="", flush=True)
        time.sleep(1)
    print("\\rBitti!   ")

if __name__ == "__main__":
    try:
        n = int(input("Kaç saniye? ").strip() or "5")
    except ValueError:
        n = 5
    geri_say(max(1, n))
'''
    return "Geri sayım sayacı:", code, "python"


def _gen_unit_convert(_: str) -> tuple[str, str, str]:
    code = '''def km_to_mil(km: float) -> float:
    return km * 0.621371

def c_to_f(c: float) -> float:
    return c * 9 / 5 + 32

def kg_to_lb(kg: float) -> float:
    return kg * 2.20462

if __name__ == "__main__":
    print("10 km =", round(km_to_mil(10), 2), "mil")
    print("25 C  =", round(c_to_f(25), 1), "F")
    print("70 kg =", round(kg_to_lb(70), 1), "lb")
'''
    return "Birim dönüştürücü:", code, "python"


def _gen_web_scraper_stub(_: str) -> tuple[str, str, str]:
    code = '''import re
import urllib.request

def basliklari_cek(url: str) -> list[str]:
    req = urllib.request.Request(url, headers={"User-Agent": "DimAI/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        html = r.read().decode("utf-8", errors="ignore")
    return re.findall(r"<h1[^>]*>(.*?)</h1>", html, flags=re.I | re.S)

if __name__ == "__main__":
    url = input("URL: ").strip() or "https://example.com"
    for i, t in enumerate(basliklari_cek(url), 1):
        temiz = re.sub(r"<[^>]+>", "", t).strip()
        print(i, temiz)
'''
    return "Basit başlık çekici (stdlib):", code, "python"


def _gen_react_counter(_: str) -> tuple[str, str, str]:
    code = '''import { useState } from "react";

export default function Counter() {
  const [n, setN] = useState(0);
  return (
    <div style={{ fontFamily: "sans-serif", padding: 24 }}>
      <h1>Sayaç: {n}</h1>
      <button onClick={() => setN(n + 1)}>+1</button>
      <button onClick={() => setN(n - 1)} style={{ marginLeft: 8 }}>-1</button>
      <button onClick={() => setN(0)} style={{ marginLeft: 8 }}>Sıfırla</button>
    </div>
  );
}
'''
    return "React sayaç bileşeni:", code, "javascript"


def _gen_html_page(topic: str) -> tuple[str, str, str]:
    title = " ".join(_words(topic)[:4]) or "Sayfa"
    code = f'''<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    :root {{ font-family: Georgia, serif; color: #1a1a1a; background: #f6f1ea; }}
    body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; }}
    main {{ max-width: 42rem; padding: 2rem; }}
    h1 {{ font-size: clamp(2rem, 6vw, 3.5rem); margin: 0 0 .5rem; }}
    p {{ line-height: 1.6; opacity: .85; }}
    button {{ border: 0; background: #184a3a; color: #fff; padding: .75rem 1.2rem; cursor: pointer; }}
  </style>
</head>
<body>
  <main>
    <h1>{title.title()}</h1>
    <p>Bu sayfa isteğine göre sıfırdan üretildi.</p>
    <button onclick="alert('Merhaba!')">Tıkla</button>
  </main>
</body>
</html>
'''
    return f"HTML sayfa ({title}):", code, "html"


def _gen_sql_schema(_: str) -> tuple[str, str, str]:
    code = '''CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE posts (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_posts_user ON posts(user_id);
'''
    return "SQL şema (users + posts):", code, "sql"


def _gen_generic(text: str, lang: str) -> tuple[str, str, str]:
    """Bilinmeyen istek: konuya özel çalışır iskelet üret."""
    topic_words = _words(text)
    slug = _slug(text)
    title = " ".join(topic_words[:5]) or "ozel uygulama"
    class_name = "".join(p.capitalize() for p in slug.split("_")) or "App"
    fields = [re.sub(r"[^a-z0-9_]", "", w) for w in topic_words[:3]]
    fields = [f for f in fields if f] or ["madde"]

    if lang == "javascript":
        code = "\n".join([
            f"// {title} — isteğine göre üretildi",
            f"function {slug}(girdi = {{}}) {{",
            f"  const durum = {{ baslik: {title!r}, adimlar: [], ...girdi }};",
            "  function ekle(adim) {",
            "    durum.adimlar.push({ at: Date.now(), adim });",
            "    return durum;",
            "  }",
            "  function ozet() {",
            "    return { baslik: durum.baslik, adimSayisi: durum.adimlar.length, adimlar: durum.adimlar };",
            "  }",
            "  return { ekle, ozet, durum };",
            "}",
            f"const app = {slug}();",
            'app.ekle("basladi");',
            'app.ekle("islendi");',
            "console.log(app.ozet());",
            "",
        ])
        return f"«{title}» için JS modülü:", code, "javascript"

    field_args = "\n    ".join(f"{f}: str = ''" for f in fields)
    ozet_parts = " | ".join(f"{{self.{f}}}" for f in fields)
    prompt_lines = "\n".join(
        f'            kwargs["{f}"] = input("{f}: ").strip()' for f in fields
    )
    code = f'''"""{title} — DimAI tarafından isteğine özel üretildi."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json

STORE = Path("{slug}_data.json")


@dataclass
class Kayit:
    {field_args}
    notlar: list[str] = field(default_factory=list)

    def ozet(self) -> str:
        return f"{ozet_parts}"


class {class_name}:
    def __init__(self) -> None:
        self.kayitlar: list[Kayit] = []
        self.yukle()

    def yukle(self) -> None:
        if not STORE.exists():
            return
        ham = json.loads(STORE.read_text(encoding="utf-8"))
        self.kayitlar = [Kayit(**x) for x in ham]

    def kaydet(self) -> None:
        STORE.write_text(
            json.dumps([k.__dict__ for k in self.kayitlar], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def ekle(self, **kwargs: str) -> Kayit:
        k = Kayit(**kwargs)
        self.kayitlar.append(k)
        self.kaydet()
        return k

    def listele(self) -> None:
        if not self.kayitlar:
            print("(bos)")
            return
        for i, k in enumerate(self.kayitlar, 1):
            print(f"{{i}}. {{k.ozet()}}")


def main() -> None:
    app = {class_name}()
    print("«{title}» hazir. Komutlar: ekle | liste | cikis")
    while True:
        komut = input("> ").strip().lower()
        if komut in {{"cikis", "q", "quit"}}:
            break
        if komut == "liste":
            app.listele()
            continue
        if komut == "ekle":
            kwargs = {{}}
{prompt_lines}
            app.ekle(**kwargs)
            print("eklendi")
            continue
        print("bilinmeyen komut")


if __name__ == "__main__":
    main()
'''
    return f"«{title}» için sıfırdan uygulama:", code, "python"


# pattern → generator (order matters: more specific first)
_RULES: list[tuple[tuple[str, ...], Callable]] = [
    (("tas kagit", "tas-kagit", "rock paper", "rps"), _gen_rps),
    (("adam asmaca", "hangman"), _gen_hangman),
    (("xox", "tic tac", "tic-tac", "tictactoe"), _gen_tic_tac_toe),
    (("tahmin", "guess", "sayi tut"), _gen_guess_game_rich),
    (("todo", "yapilacak", "gorev list", "to do", "checklist"), _gen_todo_rich),
    (("hesap makine", "calculator", "calc "), _gen_calculator),
    (("sifre", "password", "passwd"), _gen_password),
    (("fastapi",), _gen_fastapi),
    (("flask", "rest api", "api yaz", "endpoint"), _gen_flask_api),
    (("chatbot", "sohbet bot", "chat bot"), _gen_cli_chatbot),
    (("quiz", "soru cevap", "trivia"), _gen_quiz),
    (("csv",), _gen_csv_filter),
    (("http get", "http iste", "request get", "url çek", "url cek"), _gen_http_get),
    (("json", "crud"), _gen_json_crud),
    (("email", "e-posta", "eposta", "mail dogru"), _gen_regex_email),
    (("binary search", "ikili ara"), _gen_binary_search),
    (("fibonacci", "fibonacchi", "fibo"), _gen_fibonacci),
    (("sort", "sirala", "siralama", "bubble", "quick sort"), _gen_sort),
    (("geri say", "countdown", "geri sayim"), _gen_countdown),
    (("birim", "donustur", "convert"), _gen_unit_convert),
    (("scrape", "kazı", "kazi", "html parse", "baslik cek"), _gen_web_scraper_stub),
    (("dosya", "file stat", "satir say"), _gen_file_stats),
    (("react", "usestate", "component", "sayac yaz", "counter"), _gen_react_counter),
    (("html", "landing", "web sayfa"), _gen_html_page),
    (("sql", "schema", "tablo olustur"), _gen_sql_schema),
]


def _match_rule(n: str):
    for keys, fn in _RULES:
        if any(k in n for k in keys):
            return fn
    return None


def synthesize(
    message: str,
    *,
    project_context: str = "",
    user_language: str = "tr",
) -> Optional[dict]:
    """Design → implement → review. Kullanıcı mesajından orijinal kod üret."""
    raw = (message or "").strip()
    if not raw:
        return None
    n = _norm(raw)

    # belirsiz "kod yaz" → design-first guess game (fibonacci DEĞİL)
    vague = n in {
        "kod yaz", "kodu yaz", "bir kod yaz", "bana kod yaz", "write code",
        "bir sey yaz", "bir şey yaz", "bana bir sey yaz", "yaz bir sey",
        "bir sey kodla", "kodla", "program yaz", "script yaz",
    } or (
        set(n.split()) <= {"kod", "yaz", "bana", "bir", "sey", "şey", "lutfen", "code", "write"}
        and "fibonacci" not in n
    )

    if vague:
        raw = "zorluk seviyeli sayi tahmin oyunu yaz"
    elif re.search(r"(^|\s)oyun(\s|$)", n) and not any(
        k in n for k in ("tahmin", "xox", "asmaca", "hangman", "rps", "tas", "snake", "quiz")
    ):
        raw = "skor tablolu tas kagit makas oyunu yaz"

    from model.code_design import compare_alternatives, design
    from model.code_engineer import implement
    from model.code_review import apply_fixes, review

    spec = design(raw, project_context=project_context)
    # Attach alternative comparison into architecture notes (internal reasoning)
    for line in compare_alternatives(spec):
        spec.architecture_notes.append(line)

    payload = implement(spec, user_language=user_language)
    if vague:
        payload["reply"] = (
            "Net bir konu vermedin; önce küçük bir oyun mimarisi kurup "
            "zorluk seviyeli sayı tahmin yazdım.\n\n" + payload["reply"]
        )
    elif "tas kagit" in _norm(raw) and "oyun" in n and not _match_rule(n):
        payload["reply"] = (
            "Oyun türü net değildi; rules/state/cli ayrımıyla taş-kağıt-makas tasarladım.\n\n"
            + payload["reply"]
        )

    report = review(str(payload.get("code") or ""), spec, lang=str(payload.get("lang") or "python"))
    payload = apply_fixes(payload, report)
    payload["review"] = {
        "score": report.score,
        "originality": report.originality,
        "issues": report.issues,
        "suggestions": report.suggestions,
    }
    return payload
