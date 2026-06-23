"""Validation automatique de la banque d'items (exécution Epic 2).

Trois niveaux :
  1. Structure (déterministe) : content_en parse ItemContent, règle MCQ.
  2. Doublons : stems identiques au sein d'une même compétence.
  3. Juge LLM indépendant : un AUTRE modèle vérifie que la réponse marquée est
     mathématiquement correcte et l'item bien posé (attrape les erreurs de contenu
     type « 4/8 non simplifié », réponse fausse, etc.).

Usage :
    GROQ_API_KEY=... python scripts/validate_bank.py [--judge] [--flag] [--limit N]

--judge : active la vérification LLM (sinon structure + doublons seulement).
--flag  : marque les items recalés par le juge (provenance + soft delete).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import ValidationError
from sqlalchemy import select

from src.db import SessionLocal, make_engine
from src.models.base import AnswerFormat
from src.models.competency import Competency
from src.models.item import Item, ItemContent

JUDGE_MODEL = "openai/gpt-oss-120b"  # modèle différent du générateur (anti-biais)

_JUDGE_SYSTEM = (
    "You are a strict K-12 mathematics grader. For a multiple-choice item, decide: "
    "is the marked `answer` mathematically correct AND present in `options`, and is the "
    "question well-posed for the stated skill? Output STRICT JSON only: "
    '{"correct": boolean, "reason": string (short)}.'
)


def _structural_issue(item: Item) -> str | None:
    try:
        c = ItemContent.model_validate(item.content_en)
    except ValidationError as e:
        return f"ItemContent invalide: {str(e)[:60]}"
    if item.answer_format == AnswerFormat.MCQ:
        opts = c.options or []
        if len(opts) < 2:
            return "MCQ < 2 options"
        if c.answer not in opts:
            return "answer hors options"
    return None


def _judge(client, comp: Competency, item: Item) -> dict:
    c = item.content_en
    user = (
        f"Skill: {comp.code} — {comp.label_en}\n"
        f"stem: {c.get('stem')}\noptions: {c.get('options')}\nanswer: {c.get('answer')}\n"
        "Return JSON only."
    )
    raw = client.complete_json(_JUDGE_SYSTEM, user, temperature=0.0)
    return json.loads(raw)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--judge", action="store_true")
    p.add_argument("--flag", action="store_true")
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args()

    engine = make_engine()
    with SessionLocal(bind=engine) as s:
        comps = {c.id: c for c in s.execute(select(Competency)).scalars()}
        items = s.execute(
            select(Item).where(Item.deleted_at.is_(None)).order_by(Item.competency_id)
        ).scalars().all()
        if args.limit:
            items = items[: args.limit]

        per_comp = defaultdict(int)
        structural_fail, dupes, judge_fail = [], [], []
        seen_stems = defaultdict(set)

        for it in items:
            per_comp[it.competency_id] += 1
            issue = _structural_issue(it)
            if issue:
                structural_fail.append((it, issue))
                continue
            stem = it.content_en.get("stem", "").strip().lower()
            if stem in seen_stems[it.competency_id]:
                dupes.append(it)
            seen_stems[it.competency_id].add(stem)

        print(f"=== Banque : {len(items)} items, {len(per_comp)} compétences couvertes ===")
        cov = sorted(((comps[cid].code, n) for cid, n in per_comp.items()))
        print(f"min/compétence : {min(per_comp.values())}  max : {max(per_comp.values())}")
        print(f"compétences sans item : {len(comps) - len(per_comp)}")
        print(f"\nStructure : {len(structural_fail)} échec(s) | Doublons : {len(dupes)}")
        for it, issue in structural_fail[:10]:
            print(f"  ✗ {comps[it.competency_id].code}: {issue}")

        if args.judge:
            from src.llm.client import GroqClient
            client = GroqClient(model=JUDGE_MODEL)
            print(f"\n=== Juge LLM ({JUDGE_MODEL}) sur {len(items) - len(structural_fail)} items ===")
            for it in items:
                if _structural_issue(it):
                    continue
                try:
                    verdict = _judge(client, comps[it.competency_id], it)
                except Exception as e:
                    print(f"  … juge KO sur {it.id}: {str(e)[:60]}")
                    continue
                if not verdict.get("correct", True):
                    judge_fail.append((it, verdict.get("reason", "")))
                    if args.flag:
                        it.deleted_at = datetime.now()
                        it.provenance = {**(it.provenance or {}),
                                         "auto_rejected": True,
                                         "judge_model": JUDGE_MODEL,
                                         "judge_reason": verdict.get("reason", "")}
            if args.flag:
                s.commit()
            print(f"Recalés par le juge : {len(judge_fail)}"
                  + (" (marqués + soft delete)" if args.flag else " (rapport seul)"))
            for it, reason in judge_fail[:15]:
                print(f"  ✗ {comps[it.competency_id].code}: {it.content_en.get('stem')} → {reason[:70]}")

        good = len(items) - len(structural_fail) - len(judge_fail)
        print(f"\n→ {good}/{len(items)} items valides"
              + (" (structure + juge)" if args.judge else " (structure)"))


if __name__ == "__main__":
    main()
