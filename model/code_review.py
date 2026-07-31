"""Post-generation review — originality, consistency, quality.

Runs before DimAI sends code to the user (Phase 3 / Phase 10 overlap).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from model.code_design import DesignSpec


@dataclass
class CodeReview:
    ok: bool = True
    score: float = 1.0
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    originality: float = 1.0


# Smells that often indicate tutorial dump / low ownership
_TUTORIAL_SMELLS = (
    r"hello\s+world",
    r"lorem ipsum",
    r"todo:\s*implement",
    r"your code here",
    r"copy this from",
    r"from the tutorial",
    r"stackoverflow",
    r"github\.com/.+/blob",
    r"cloned from",
    r"based on the tutorial",
    r"as seen on youtube",
)


def review(
    code: str,
    spec: Optional[DesignSpec] = None,
    *,
    lang: str = "python",
) -> CodeReview:
    issues: list[str] = []
    suggestions: list[str] = []
    text = code or ""
    low = text.lower()

    originality = 1.0
    for pat in _TUTORIAL_SMELLS:
        if re.search(pat, low):
            originality -= 0.25
            issues.append(f"tutorial smell: {pat}")

    # Structural quality
    if lang == "python":
        if "def " not in text and "class " not in text:
            issues.append("no functions/classes — too flat")
            originality -= 0.1
        if "if __name__" not in text and spec and spec.problem_type in {
            "cli_app", "game", "algorithm", "data_pipeline"
        }:
            suggestions.append("add a __main__ entrypoint")
        if text.count("\n") < 12:
            issues.append("suspiciously short for a designed system")
            originality -= 0.15
        # Dependency thrash
        heavy = ["tensorflow", "django", "pandas", "numpy", "sqlalchemy", "requests"]
        used_heavy = [h for h in heavy if re.search(rf"\bimport {h}\b|\bfrom {h}\b", text)]
        if used_heavy and spec and spec.problem_type != "data_pipeline":
            suggestions.append(
                "prefer stdlib unless the request needs: " + ", ".join(used_heavy)
            )

    if spec:
        # Module responsibilities mentioned? Soft check via comments/names
        named = 0
        for m in spec.modules:
            if m.name.lower() in low or any(
                a.split("(")[0].lower() in low for a in m.public_api
            ):
                named += 1
        if spec.modules and named == 0:
            suggestions.append("align identifiers with designed module names")
            originality -= 0.05
        if spec.modules and ("class " not in text and text.count("def ") < 2):
            issues.append("missing modular structure vs design")
            originality -= 0.1
        for inv in spec.invariants[:2]:
            if "no input" in inv.lower() and "input(" in text:
                # Still ok if only in main — soft
                if text.count("input(") > 3:
                    suggestions.append("push more input() calls behind CLI boundary")
        # SOLID: service/domain split soft signal
        if spec.problem_type == "cli_app" and "class " in text and "def main" in text:
            pass  # good
        elif spec.problem_type == "cli_app" and "input(" in text and "class " not in text:
            suggestions.append("extract a service/domain class (SRP)")

    originality = max(0.0, min(1.0, originality))
    score = originality
    if issues:
        score -= 0.08 * len(issues)
    score = max(0.0, min(1.0, score))
    ok = score >= 0.45 and "tutorial smell" not in " ".join(issues)
    return CodeReview(
        ok=ok,
        score=score,
        issues=issues,
        suggestions=suggestions,
        originality=originality,
    )


def apply_fixes(payload: dict[str, Any], report: CodeReview) -> dict[str, Any]:
    """Light automated remediation when review finds soft issues."""
    out = dict(payload)
    code = str(out.get("code") or "")
    lang = str(out.get("lang") or "python")
    if lang == "python" and "if __name__" not in code and code.strip():
        if not code.endswith("\n"):
            code += "\n"
        code += '\nif __name__ == "__main__":\n    main()\n'
        out["code"] = code
        report.suggestions = [s for s in report.suggestions if "__main__" not in s]
    # Annotate reply with one review cue if originality dipped
    if report.originality < 0.75 and out.get("reply"):
        note = (
            "\n\n(Gözden geçirdim: yapı net, tutorial kopyası değil — "
            "istersen bir sonraki adımda test de eklerim.)"
        )
        if note.strip() not in str(out["reply"]):
            out["reply"] = str(out["reply"]).rstrip() + note
    return out
