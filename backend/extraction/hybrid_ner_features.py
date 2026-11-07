"""Shared tokenisation and CRF features for the PULSE hybrid NER tagger.

Both the trainer (scripts/train_hybrid_ner.py) and the runtime extractor
(backend/extraction/hybrid_ner_extractor.py) import from here, so training and
inference features cannot drift apart.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

TOKEN_RE = re.compile(r"[A-Za-z0-9°%][^\s,.;:!?()\[\]\"“”]*")
STRIP_CHARS = " \t\r\n.,;:!?\"'()[]"


def normalize_surface(surface: str) -> str:
    """Lowercase and trim a span so lexicon lookups are boundary-insensitive."""
    return re.sub(r"\s+", " ", surface).strip(STRIP_CHARS).lower()


def tokenize(text: str) -> List[Tuple[int, int, str]]:
    return [(m.start(), m.end(), m.group(0)) for m in TOKEN_RE.finditer(text)]


def shape_of(word: str) -> str:
    out = []
    for ch in word:
        if ch.isupper():
            out.append("X")
        elif ch.islower():
            out.append("x")
        elif ch.isdigit():
            out.append("d")
        else:
            out.append(ch)
    return "".join(out)


def token_features(tokens, i: int, gaz) -> Dict[str, Any]:
    _s, _e, word = tokens[i]
    low = word.lower()

    def w_at(idx: int) -> str:
        return tokens[idx][2].lower() if 0 <= idx < len(tokens) else ("<s>" if idx < 0 else "</s>")

    feats: Dict[str, Any] = {
        "bias": 1.0,
        "w": low,
        "w-1": w_at(i - 1),
        "w+1": w_at(i + 1),
        "pre3": low[:3],
        "suf3": low[-3:],
        "suf4": low[-4:],
        "len": min(len(word), 12),
        "shape": shape_of(word)[:8],
        "is_digit": word.isdigit(),
        "is_upper": word.isupper(),
        "is_title": word.istitle(),
        "has_digit": any(c.isdigit() for c in word),
        "has_hyphen": "-" in word,
        "has_slash": "/" in word,
    }

    solo = gaz.get(normalize_surface(word))
    if solo:
        feats["gaz_w=" + solo.most_common(1)[0][0]] = 1.0
    if i > 0:
        bigram = normalize_surface(tokens[i - 1][2] + " " + word)
        if bigram in gaz:
            feats["gaz_b=" + gaz[bigram].most_common(1)[0][0]] = 1.0
    trigram = normalize_surface(" ".join(t[2] for t in tokens[max(0, i - 1) : i + 2]))
    if trigram in gaz:
        feats["gaz_t=" + gaz[trigram].most_common(1)[0][0]] = 1.0
    return feats


SENTENCE_RE = re.compile(r"[^.!?]+[.!?]?")


def clean_spans(spans: List[Dict[str, Any]], text: str) -> List[Dict[str, Any]]:
    """Keep each decoded span inside one sentence and drop duplicates.

    The tokenizer drops punctuation, so the CRF can tag a run that swallows
    several statements. Splitting at sentence boundaries is the only
    post-processing step kept, because trimming or filtering spans measurably
    *lowered* strict F1 on the gold folds (fold_0: 60.91 raw vs 58.12 fully
    cleaned), so it is not applied. The measured cost of splitting alone is
    small and buys readable handover output.
    """
    cleaned: List[Dict[str, Any]] = []
    seen = set()
    for span in spans:
        covered = text[span["start_char"] : span["end_char"]]
        pieces: List[Tuple[int, int]] = []
        if re.search(r"[.!?]", covered):
            for match in SENTENCE_RE.finditer(covered):
                piece = match.group(0)
                lead = len(piece) - len(piece.lstrip())
                tail = len(piece.rstrip())
                start = span["start_char"] + match.start() + lead
                end = span["start_char"] + match.start() + tail
                if end > start:
                    pieces.append((start, end))
        else:
            pieces.append((span["start_char"], span["end_char"]))

        for start, end in pieces:
            key = (start, end, span.get("category"))
            if key in seen:
                continue
            seen.add(key)
            cleaned.append({**span, "start_char": start, "end_char": end, "text": text[start:end]})
    return cleaned


def tags_to_spans(tokens, tags, text: str) -> List[Dict[str, Any]]:
    spans: List[Dict[str, Any]] = []
    current = None
    for (s, e, _w), tag in zip(tokens, tags):
        if tag == "O":
            if current:
                spans.append(current)
                current = None
            continue
        bio, cat = tag.split("-", 1)
        if bio == "B" or current is None or current["category"] != cat:
            if current:
                spans.append(current)
            current = {"category": cat, "start_char": s, "end_char": e, "text": text[s:e]}
        else:
            current["end_char"] = e
            current["text"] = text[current["start_char"] : e]
    if current:
        spans.append(current)
    return spans
