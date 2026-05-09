"""Tests des fonctions pures de utils.py."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from utils import (
    PREDEFINED_COLORS,
    align_tokens_with_annotations,
    convert_to_bilou,
    export_json_span,
    export_to_conll,
    extract_unique_labels,
    load_csv,
    tokenize,
)

# ---------------------------------------------------------------------------
# load_csv
# ---------------------------------------------------------------------------


def test_load_csv_demo_file():
    df = load_csv("data/annotations.csv")
    assert "text" in df.columns
    assert "annotations" in df.columns
    assert len(df) > 0


def test_load_csv_missing_file():
    with pytest.raises(FileNotFoundError):
        load_csv("does_not_exist.csv")


# ---------------------------------------------------------------------------
# tokenize
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hello world", ["Hello", "world"]),
        ("It's working.", ["It's", "working", "."]),
        ("a, b, c", ["a", ",", "b", ",", "c"]),
        ("", []),
        ("   ", []),
    ],
)
def test_tokenize(text, expected):
    assert tokenize(text) == expected


# ---------------------------------------------------------------------------
# extract_unique_labels
# ---------------------------------------------------------------------------


def test_extract_unique_labels_returns_sorted():
    df = pd.DataFrame(
        {
            "text": ["t1", "t2"],
            "annotations": [
                json.dumps([{"start": 0, "end": 3, "label": "PER", "text": "Foo"}]),
                json.dumps([{"start": 0, "end": 3, "label": "ORG", "text": "Bar"}]),
            ],
        }
    )
    assert extract_unique_labels(df) == ["ORG", "PER"]


def test_extract_unique_labels_handles_empty_and_invalid_cells():
    df = pd.DataFrame(
        {
            "text": ["a", "b", "c", "d"],
            "annotations": [
                "",
                None,
                "not-json",
                json.dumps([{"start": 0, "end": 1, "label": "LOC", "text": "X"}]),
            ],
        }
    )
    assert extract_unique_labels(df) == ["LOC"]


def test_extract_unique_labels_no_column():
    df = pd.DataFrame({"text": ["a"]})
    assert extract_unique_labels(df) == []


# ---------------------------------------------------------------------------
# align_tokens_with_annotations
# ---------------------------------------------------------------------------


def test_align_tokens_no_annotations():
    aligned = align_tokens_with_annotations("Hello world", [])
    assert aligned == [("Hello", "O"), ("world", "O")]


def test_align_tokens_single_token_annotation():
    text = "Hello world"
    annots = [{"start": 0, "end": 5, "label": "GREETING", "text": "Hello"}]
    aligned = align_tokens_with_annotations(text, annots)
    assert aligned == [("Hello", "B-GREETING"), ("world", "O")]


def test_align_tokens_multi_token_annotation():
    text = "Barack Obama est né"
    # "Barack Obama" couvre indices 0..12
    annots = [{"start": 0, "end": 12, "label": "PER", "text": "Barack Obama"}]
    aligned = align_tokens_with_annotations(text, annots)
    tags = [t for _, t in aligned]
    assert tags[0] == "B-PER"
    assert tags[1] == "I-PER"
    assert all(t == "O" for t in tags[2:])


# ---------------------------------------------------------------------------
# convert_to_bilou
# ---------------------------------------------------------------------------


def test_convert_to_bilou_unit_for_lone_b():
    bio = [("Paris", "B-LOC"), ("est", "O")]
    assert convert_to_bilou(bio) == [("Paris", "U-LOC"), ("est", "O")]


def test_convert_to_bilou_begin_inside_last():
    bio = [
        ("Barack", "B-PER"),
        ("Hussein", "I-PER"),
        ("Obama", "I-PER"),
        ("est", "O"),
    ]
    expected = [
        ("Barack", "B-PER"),
        ("Hussein", "I-PER"),
        ("Obama", "L-PER"),
        ("est", "O"),
    ]
    assert convert_to_bilou(bio) == expected


def test_convert_to_bilou_distinguishes_labels_with_shared_suffix():
    """Régression du bug `endswith(label)` : LOC vs PERS_LOC ne doivent pas s'agréger."""
    bio = [
        ("a", "B-LOC"),
        ("b", "I-PERS_LOC"),  # label différent → l'entité LOC s'arrête à 'a'
    ]
    result = convert_to_bilou(bio)
    # 'a' doit être U-LOC (entité solo, pas continuée)
    assert result[0] == ("a", "U-LOC")


def test_convert_to_bilou_empty():
    assert convert_to_bilou([]) == []


def test_convert_to_bilou_only_o():
    bio = [("a", "O"), ("b", "O")]
    assert convert_to_bilou(bio) == [("a", "O"), ("b", "O")]


# ---------------------------------------------------------------------------
# export_json_span
# ---------------------------------------------------------------------------


def test_export_json_span_roundtrip():
    df = pd.DataFrame(
        {
            "text": ["Hello world"],
            "annotations": [json.dumps([{"start": 0, "end": 5, "label": "G", "text": "Hello"}])],
        }
    )
    out = export_json_span(df)
    parsed = json.loads(out)
    assert parsed == [
        {
            "text": "Hello world",
            "annotations": [{"start": 0, "end": 5, "label": "G", "text": "Hello"}],
        }
    ]


def test_export_json_span_handles_invalid_annotations():
    df = pd.DataFrame({"text": ["t"], "annotations": ["not-json"]})
    parsed = json.loads(export_json_span(df))
    assert parsed[0]["annotations"] == []


def test_export_json_span_unicode():
    df = pd.DataFrame({"text": ["café"], "annotations": [""]})
    out = export_json_span(df)
    assert "café" in out  # ensure_ascii=False préserve l'unicode


# ---------------------------------------------------------------------------
# export_to_conll
# ---------------------------------------------------------------------------


def test_export_to_conll_iob_default():
    df = pd.DataFrame(
        {
            "text": ["Paris est belle"],
            "annotations": [json.dumps([{"start": 0, "end": 5, "label": "LOC", "text": "Paris"}])],
        }
    )
    out = export_to_conll(df)
    lines = out.split("\n")
    assert lines[0] == "Paris B-LOC"
    assert lines[1] == "est O"
    assert lines[2] == "belle O"


def test_export_to_conll_bilou():
    df = pd.DataFrame(
        {
            "text": ["Paris est belle"],
            "annotations": [json.dumps([{"start": 0, "end": 5, "label": "LOC", "text": "Paris"}])],
        }
    )
    out = export_to_conll(df, format_type="BILOU")
    lines = out.split("\n")
    # 'Paris' est seul → U-LOC en BILOU
    assert lines[0] == "Paris U-LOC"


def test_export_to_conll_multiple_rows_separated_by_blank_line():
    df = pd.DataFrame(
        {
            "text": ["a", "b"],
            "annotations": ["", ""],
        }
    )
    out = export_to_conll(df)
    # Chaque ligne CoNLL est séparée d'une ligne vide
    assert "\n\n" in out


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------


def test_predefined_colors_non_empty():
    assert len(PREDEFINED_COLORS) > 0
    assert all(isinstance(c, str) for c in PREDEFINED_COLORS)
