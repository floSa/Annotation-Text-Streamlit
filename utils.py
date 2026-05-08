import json
import pandas as pd
import os
import re

PREDEFINED_COLORS = [
    "blue", "orange", "green", "red", "yellow",
    "purple", "cyan", "brown", "grey", "pink", "olive"
]

def load_csv(path):
    """Charge un fichier CSV (séparateur ';') et retourne un DataFrame."""
    return pd.read_csv(path, sep=';')

def extract_unique_labels(df, annotations_column='annotations'):
    """Extrait la liste unique des labels présents dans le DataFrame."""
    unique_labels = set()
    if annotations_column in df.columns:
        for val in df[annotations_column]:
            if pd.notna(val) and val != "":
                try:
                    # Gérer le cas où c'est une string JSON ou déjà une liste
                    annots = json.loads(val) if isinstance(val, str) else val
                    if isinstance(annots, list):
                        for annot in annots:
                            if 'label' in annot:
                                unique_labels.add(annot['label'])
                except (json.JSONDecodeError, TypeError):
                    continue
    return sorted(list(unique_labels))

def tokenize(text):
    """Tokenisation simple par espace et ponctuation."""
    # Split tout en gardant les délimiteurs, puis filtrer les espaces vides
    tokens = re.findall(r"[\w']+|[.,!?;]", text)
    return tokens

def align_tokens_with_annotations(text, annotations):
    """
    Associe chaque token à un label BIO/BILOU.
    Retourne une liste de tuples (token, tag).
    """
    tokens = []
    # On reconstruit les tokens avec leur span pour vérifier l'alignement
    # C'est une simplification, pour un vrai système pro, utiliser Spacy
    
    current_pos = 0
    # Stratégie simple : on itère sur les tokens "logiques" et on regarde si leur position 
    # tombe dans une annotation.
    # Pour faire ça correctement sans librairie lourde, on va scanner le texte.
    
    # 1. Identification des spans de tokens
    token_spans = []
    for match in re.finditer(r"[\w']+|[.,!?;]", text):
        token_spans.append((match.group(), match.start(), match.end()))
        
    aligned_data = []
    
    # Trier les annotations par départ
    sorted_annots = sorted(annotations, key=lambda x: x['start'])
    
    for token, start, end in token_spans:
        label = "O"
        # Vérifier si ce token est dans une annotation
        for annot in sorted_annots:
            a_start, a_end, a_label = annot['start'], annot['end'], annot['label']
            
            # Cas 1: Le token est EXACTEMENT l'annotation (ou le début)
            if start == a_start:
                label = f"B-{a_label}" # Begin
                break
            # Cas 2: Le token est DANS l'annotation (mais pas au début)
            elif start > a_start and end <= a_end:
                label = f"I-{a_label}" # Inside
                break
        
        aligned_data.append((token, label))
        
    return aligned_data

def _split_tag(tag):
    """Coupe un tag 'B-LABEL' / 'I-LABEL' en (prefix, label). Retourne (None, None) si tag = 'O'."""
    if tag == "O" or "-" not in tag:
        return None, None
    prefix, label = tag.split("-", 1)
    return prefix, label


def convert_to_bilou(aligned_data):
    """
    Convertit IOB vers BILOU (Begin, Inside, Last, Outside, Unit).
    B-X seul ou suivi d'un non-I-X     -> U-X
    B-X suivi de I-X (avec même label) -> B-X
    I-X suivi de I-X (même label)      -> I-X
    I-X suivi d'autre chose            -> L-X
    """
    bilou_data = []
    count = len(aligned_data)

    for i in range(count):
        token, tag = aligned_data[i]

        if tag == "O":
            bilou_data.append((token, "O"))
            continue

        prefix, label = _split_tag(tag)
        next_tag = aligned_data[i + 1][1] if i + 1 < count else "O"
        next_prefix, next_label = _split_tag(next_tag)

        # On ne continue une entité que si le prochain token est I- du MÊME label
        continues = next_prefix == "I" and next_label == label

        if prefix == "B":
            bilou_data.append((token, f"B-{label}" if continues else f"U-{label}"))
        elif prefix == "I":
            bilou_data.append((token, f"I-{label}" if continues else f"L-{label}"))
        else:
            bilou_data.append((token, tag))

    return bilou_data

def export_to_conll(df, format_type="IOB"):
    """Génère une string format CoNLL (un token par ligne)."""
    output = []
    
    for idx, row in df.iterrows():
        text = str(row.iloc[0]) # Supposons 1ere colonne = texte
        annotations = []
        
        # Récup annotations
        val = row.get('annotations', [])
        if isinstance(val, str):
            try:
                annotations = json.loads(val)
            except json.JSONDecodeError:
                annotations = []
        elif isinstance(val, list):
            annotations = val

        aligned = align_tokens_with_annotations(text, annotations)

        if format_type == "BILOU":
            final_data = convert_to_bilou(aligned)
        else:
            final_data = aligned  # Default IOB
            
        for token, tag in final_data:
            output.append(f"{token} {tag}")
        output.append("") # Ligne vide entre les phrases
        
    return "\n".join(output)

def export_json_span(df):
    """Export simple JSON (format natif)."""
    results = []
    for idx, row in df.iterrows():
        text = str(row.iloc[0])
        val = row.get('annotations', [])
        if isinstance(val, str):
            try:
                annotations = json.loads(val)
            except json.JSONDecodeError:
                annotations = []
        else:
            annotations = val

        results.append({
            "text": text,
            "annotations": annotations
        })
    return json.dumps(results, indent=2, ensure_ascii=False)
