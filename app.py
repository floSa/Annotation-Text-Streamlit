import streamlit as st
import pandas as pd
import json
import os
from annotated_text import annotated_text
from io import StringIO

# Configuration
st.set_page_config(
    page_title="Service d'annotation de texte",
    page_icon="📝",
    layout="wide"
)

PREDEFINED_COLORS = [
    "blue", "orange", "green", "red", "yellow",
    "purple", "cyan", "brown", "grey", "pink", "olive"
]

def init_session_state():
    if 'df' not in st.session_state:
        st.session_state.df = None
    if 'current_index' not in st.session_state:
        st.session_state.current_index = 0
    if 'labels' not in st.session_state:
        st.session_state.labels = {}
    if 'annotations' not in st.session_state:
        st.session_state.annotations = {}
    if 'label_color_index' not in st.session_state:
        st.session_state.label_color_index = 0

def get_next_color():
    color = PREDEFINED_COLORS[st.session_state.label_color_index % len(PREDEFINED_COLORS)]
    st.session_state.label_color_index += 1
    return color

def save_annotations_to_csv():
    if st.session_state.df is not None:
        annotations_column = []
        for idx in range(len(st.session_state.df)):
            annots = st.session_state.annotations.get(idx, [])
            annotations_column.append(json.dumps(annots) if annots else "")
        st.session_state.df['annotations'] = annotations_column
        os.makedirs('data', exist_ok=True)
        st.session_state.df.to_csv('data/annotations.csv', index=False)

def generate_csv_download():
    save_annotations_to_csv()
    csv_buffer = StringIO()
    st.session_state.df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue()

def load_annotations_from_csv():
    if 'annotations' in st.session_state.df.columns:
        for idx, row in st.session_state.df.iterrows():
            try:
                st.session_state.annotations[idx] = json.loads(row['annotations']) if pd.notna(row['annotations']) else []
            except json.JSONDecodeError:
                st.session_state.annotations[idx] = []

def create_annotated_text(text, annotations):
    if not annotations:
        return [text]
    sorted_annotations = sorted(annotations, key=lambda x: x['start'])
    result = []
    current_pos = 0
    for annotation in sorted_annotations:
        start, end, label = annotation['start'], annotation['end'], annotation['label']
        color = st.session_state.labels.get(label, "#CCCCCC")
        if current_pos < start:
            result.append(text[current_pos:start])
        result.append((text[start:end], label, color))
        current_pos = end
    result.append(text[current_pos:])
    return result

def apply_annotation_globally(substring, label):
    """Ajoute l'annotation à toutes les lignes contenant le substring (non chevauchante)"""
    for idx, row in st.session_state.df.iterrows():
        text = row.iloc[0]
        if substring in text:
            start = text.find(substring)
            end = start + len(substring)
            annotation = {
                'start': start,
                'end': end,
                'label': label,
                'text': substring
            }
            annots = st.session_state.annotations.get(idx, [])
            if not any(a['start'] == start and a['end'] == end and a['label'] == label for a in annots):
                annots.append(annotation)
                st.session_state.annotations[idx] = annots

def main():
    init_session_state()

    st.title("📝 Service d'annotation de texte")

    # Sidebar : Labels et Export
    with st.sidebar:
        st.header("🏷️ Gestion des labels")
        new_label = st.text_input("Nouveau label :")
        if st.button("Ajouter label"):
            if new_label and new_label not in st.session_state.labels:
                st.session_state.labels[new_label] = get_next_color()
                st.success(f"Label '{new_label}' ajouté")
                st.rerun()

        if st.session_state.labels:
            st.subheader("Labels :")
            for label, color in st.session_state.labels.items():
                st.markdown(
                    f"<div style='background-color: {color}; padding: 5px; border-radius: 4px; "
                    f"color: white; text-align: center; margin: 2px;'>{label}</div>",
                    unsafe_allow_html=True
                )

        st.markdown("---")
        if st.session_state.df is not None:
            csv_data = generate_csv_download()
            st.download_button("📥 Télécharger le CSV annoté", data=csv_data,
                               file_name="annotations.csv", mime="text/csv")

    # Zone fichier
    col1, col2 = st.columns([3, 1])
    with col2:
        st.header("📁 Fichier")
        uploaded_file = st.file_uploader("Téléverser un CSV", type="csv")
        if uploaded_file is not None:
            st.session_state.df = pd.read_csv(uploaded_file)
            st.success(f"{len(st.session_state.df)} lignes chargées.")
            if 'annotations' not in st.session_state.df.columns:
                st.session_state.df['annotations'] = ""
            load_annotations_from_csv()

        st.subheader("Ou sélectionner dans ./data")
        data_dir = "data"
        os.makedirs(data_dir, exist_ok=True)
        files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]
        if files:
            selected_file = st.selectbox("Fichiers disponibles :", files)
            if st.button("📂 Charger le fichier"):
                try:
                    st.session_state.df = pd.read_csv(os.path.join(data_dir, selected_file))
                    st.success(f"Fichier {selected_file} chargé.")
                    if 'annotations' not in st.session_state.df.columns:
                        st.session_state.df['annotations'] = ""
                    load_annotations_from_csv()
                except Exception as e:
                    st.error(f"Erreur : {e}")
        else:
            st.info("Aucun fichier CSV trouvé dans ./data")

    # Zone annotation
    with col1:
        if st.session_state.df is not None:

            col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
            with col_nav1:
                if st.button("⬅️ Précédent"):
                    if st.session_state.current_index > 0:
                        save_annotations_to_csv()
                        st.session_state.current_index -= 1
                        st.rerun()
            with col_nav2:
                st.write(f"Ligne {st.session_state.current_index + 1} / {len(st.session_state.df)}")
            with col_nav3:
                if st.button("Suivant ➡️"):
                    if st.session_state.current_index < len(st.session_state.df) - 1:
                        save_annotations_to_csv()
                        st.session_state.current_index += 1
                        st.rerun()

            current_text = st.session_state.df.iloc[st.session_state.current_index].iloc[0]
            current_annotations = st.session_state.annotations.get(st.session_state.current_index, [])

            st.subheader("Texte annoté :")
            annotated_text(*create_annotated_text(current_text, current_annotations))

            st.subheader("Nouvelle annotation :")
            col_a, col_b, col_c = st.columns([2, 1, 1])
            with col_a:
                selected_text = st.text_input("Texte à annoter :")
            with col_b:
                if st.session_state.labels:
                    selected_label = st.selectbox("Label :", list(st.session_state.labels.keys()))
                else:
                    selected_label = None
            with col_c:
                if st.button("Valider annotation"):
                    if selected_text and selected_label and selected_text in current_text:
                        apply_annotation_globally(selected_text, selected_label)
                        save_annotations_to_csv()
                        st.success("Annotation ajoutée à tous les documents contenant ce texte.")
                        st.rerun()
                    else:
                        st.error("Texte non trouvé dans cette ligne ou label manquant.")

            if current_annotations:
                st.subheader("Annotations existantes :")
                for i, annotation in enumerate(current_annotations):
                    col_d1, col_d2 = st.columns([4, 1])
                    with col_d1:
                        st.write(f"'{annotation['text']}' → {annotation['label']}")
                    with col_d2:
                        if st.button("🗑️", key=f"del_{i}"):
                            st.session_state.annotations[st.session_state.current_index].pop(i)
                            save_annotations_to_csv()
                            st.rerun()

if __name__ == "__main__":
    main()
