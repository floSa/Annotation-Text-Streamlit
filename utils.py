"""Fonctions pures côté logique métier (chargement, tokenisation, exports).

Ce module ne dépend pas de Streamlit pour rester testable indépendamment.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

PREDEFINED_COLORS: list[str] = [
    "blue",
    "orange",
    "green",
    "red",
    "yellow",
    "purple",
    "cyan",
    "brown",
    "grey",
    "pink",
    "olive",
]

# Type aliases
Annotation = dict[str, Any]  # {"start": int, "end": int, "label": str, "text": str}
TaggedToken = tuple[str, str]


def load_csv(path: str | Path) -> pd.DataFrame:
    """Charge un fichier CSV (séparateur ';') et retourne un DataFrame."""
    return pd.read_csv(path, sep=";")


def _parse_annotations_cell(val: Any) -> list[Annotation]:
    """Normalise une cellule 'annotations' (str JSON | list | NaN) en list[Annotation]."""
    if isinstance(val, list):
        return val
    if isinstance(val, str) and val:
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return []


def extract_unique_labels(
    df: pd.DataFrame,
    annotations_column: str = "annotations",
) -> list[str]:
    """Extrait la liste triée des labels uniques présents dans le DataFrame."""
    unique_labels: set[str] = set()
    if annotations_column not in df.columns:
        return []
    for val in df[annotations_column]:
        if not pd.notna(val) or val == "":
            continue
        for annot in _parse_annotations_cell(val):
            if isinstance(annot, dict) and "label" in annot:
                unique_labels.add(annot["label"])
    return sorted(unique_labels)


_TOKEN_RE = re.compile(r"[\w']+|[.,!?;]")


def tokenize(text: str) -> list[str]:
    """Tokenisation simple par mots (avec apostrophe) et ponctuation."""
    return _TOKEN_RE.findall(text)


def align_tokens_with_annotations(
    text: str,
    annotations: list[Annotation],
) -> list[TaggedToken]:
    """Associe chaque token à un tag BIO (B-LABEL, I-LABEL, ou O).

    Note : approche simple par regex. Pour un système production avec gestion fine
    des tokens (multi-langue, sub-tokens), passer à spaCy ou un tokenizer dédié.
    """
    token_spans: list[tuple[str, int, int]] = [
        (m.group(), m.start(), m.end()) for m in _TOKEN_RE.finditer(text)
    ]
    sorted_annots = sorted(annotations, key=lambda a: a["start"])

    aligned: list[TaggedToken] = []
    for token, start, end in token_spans:
        tag = "O"
        for annot in sorted_annots:
            a_start, a_end, a_label = annot["start"], annot["end"], annot["label"]
            if start == a_start:
                tag = f"B-{a_label}"
                break
            if start > a_start and end <= a_end:
                tag = f"I-{a_label}"
                break
        aligned.append((token, tag))
    return aligned


def _split_tag(tag: str) -> tuple[str | None, str | None]:
    """Coupe un tag 'B-LABEL' / 'I-LABEL' en (prefix, label). (None, None) pour 'O'."""
    if tag == "O" or "-" not in tag:
        return None, None
    prefix, label = tag.split("-", 1)
    return prefix, label


def convert_to_bilou(aligned_data: list[TaggedToken]) -> list[TaggedToken]:
    """Convertit une séquence BIO en BILOU.

    Règles :
    - B-X suivi de I-X (même label) -> B-X
    - B-X seul ou suivi d'un non-I-X -> U-X
    - I-X suivi de I-X (même label) -> I-X
    - I-X suivi d'autre chose -> L-X
    """
    result: list[TaggedToken] = []
    count = len(aligned_data)

    for i in range(count):
        token, tag = aligned_data[i]

        if tag == "O":
            result.append((token, "O"))
            continue

        prefix, label = _split_tag(tag)
        next_tag = aligned_data[i + 1][1] if i + 1 < count else "O"
        next_prefix, next_label = _split_tag(next_tag)

        continues = next_prefix == "I" and next_label == label

        if prefix == "B":
            result.append((token, f"B-{label}" if continues else f"U-{label}"))
        elif prefix == "I":
            result.append((token, f"I-{label}" if continues else f"L-{label}"))
        else:
            result.append((token, tag))

    return result


def _row_text_and_annotations(row: pd.Series) -> tuple[str, list[Annotation]]:
    """Extrait le texte (1ʳᵉ colonne) et les annotations parsées d'une ligne."""
    text = str(row.iloc[0])
    annotations = _parse_annotations_cell(row.get("annotations", []))
    return text, annotations


def export_to_conll(df: pd.DataFrame, format_type: str = "IOB") -> str:
    """Sérialise le DataFrame en format CoNLL (un token par ligne, ligne vide entre phrases)."""
    output: list[str] = []
    for _, row in df.iterrows():
        text, annotations = _row_text_and_annotations(row)
        aligned = align_tokens_with_annotations(text, annotations)
        final_data = convert_to_bilou(aligned) if format_type == "BILOU" else aligned
        output.extend(f"{token} {tag}" for token, tag in final_data)
        output.append("")  # Séparateur de phrases
    return "\n".join(output)


def export_json_span(df: pd.DataFrame) -> str:
    """Sérialise le DataFrame en JSON (format span natif, un objet par ligne)."""
    results: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        text, annotations = _row_text_and_annotations(row)
        results.append({"text": text, "annotations": annotations})
    return json.dumps(results, indent=2, ensure_ascii=False)
