import streamlit as st
import pandas as pd
import json
import os
from annotated_text import annotated_text
from io import StringIO
import utils # Notre nouveau module

# Configuration
st.set_page_config(
    page_title="App Annotation",
    page_icon="✏️",
    layout="wide"
)

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
    if 'current_file_path' not in st.session_state:
        st.session_state.current_file_path = None

def get_next_color():
    color = utils.PREDEFINED_COLORS[st.session_state.label_color_index % len(utils.PREDEFINED_COLORS)]
    st.session_state.label_color_index += 1
    return color

def save_current_state():
    """Sauvegarde l'état actuel sur disque via utils logic si besoin, ou direct."""
    if st.session_state.df is not None:
        annotations_column = []
        for idx in range(len(st.session_state.df)):
            annots = st.session_state.annotations.get(idx, [])
            annotations_column.append(json.dumps(annots) if annots else "")
        st.session_state.df['annotations'] = annotations_column
        
        if st.session_state.current_file_path:
            try:
                os.makedirs(os.path.dirname(st.session_state.current_file_path), exist_ok=True)
                st.session_state.df.to_csv(st.session_state.current_file_path, index=False, sep=';')
            except Exception as e:
                st.error(f"Erreur sauvegarde: {e}")

def load_file_logic(df, path=None):
    """Logique commune après chargement d'un fichier."""
    st.session_state.df = df
    st.session_state.current_file_path = path
    st.session_state.current_index = 0
    if 'annotations' not in st.session_state.df.columns:
        st.session_state.df['annotations'] = ""

    # Charger les annotations en session
    st.session_state.annotations = {}
    for idx, row in st.session_state.df.iterrows():
        try:
            val = row['annotations']
            if pd.notna(val) and val != "":
                if isinstance(val, str):
                    st.session_state.annotations[idx] = json.loads(val)
                else:
                    st.session_state.annotations[idx] = val
            else:
                st.session_state.annotations[idx] = []
        except:
             st.session_state.annotations[idx] = []
    
    # Extraction AUTO des labels
    extracted = utils.extract_unique_labels(st.session_state.df)
    for label in extracted:
        if label not in st.session_state.labels:
            st.session_state.labels[label] = get_next_color()

def create_annotated_text_view(text, annotations):
    if not annotations:
        return [text]
    valid_annotations = [a for a in annotations if a['end'] <= len(text)]
    sorted_annotations = sorted(valid_annotations, key=lambda x: x['start'])
    
    result = []
    current_pos = 0
    for annotation in sorted_annotations:
        start, end, label = annotation['start'], annotation['end'], annotation['label']
        if start < current_pos: continue
        color = st.session_state.labels.get(label, "#CCCCCC")
        if current_pos < start:
            result.append(text[current_pos:start])
        result.append((text[start:end], label, color))
        current_pos = end
    if current_pos < len(text):
        result.append(text[current_pos:])
    return result

def main():
    init_session_state()

    # --- LANDING PAGE (Si aucun dossier chargé) ---
    if st.session_state.df is None:
        st.markdown("<h1 style='text-align: center;'>Annotation Tool 🚀</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Charger un fichier pour commencer.</p>", unsafe_allow_html=True)
        
        col_c1, col_c2, col_c3 = st.columns([1, 2, 1])
        with col_c2:
             # Tabs pour choisir la méthode de chargement (Landing)
            tab1, tab2 = st.tabs(["📂 Fichiers Locaux (data/)", "📤 Upload"])
            
            with tab1:
                data_dir = "data"
                os.makedirs(data_dir, exist_ok=True)
                files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]
                if files:
                    selected_file = st.selectbox("Choisir un fichier", files, label_visibility="collapsed")
                    if st.button("Charger ce fichier", use_container_width=True):
                         path = os.path.join(data_dir, selected_file)
                         df = utils.load_csv(path)
                         load_file_logic(df, path)
                         st.rerun()
                else:
                    st.info("Aucun fichier CSV dans ./data")

            with tab2:
                upl = st.file_uploader("Glisser un fichier CSV", type="csv")
                if upl:
                    if st.button("Charger l'upload", use_container_width=True):
                        df = pd.read_csv(upl, sep=';')
                        load_file_logic(df, None) # Pas de path pour upload
                        st.rerun()
        return # STOP ici si pas de fichier

    # --- MAIN APP (Si fichier chargé) ---
    
    # SIDEBAR : Gestion Fichier & Exports
    with st.sidebar:
        st.markdown(f"### 📄 {os.path.basename(st.session_state.current_file_path) if st.session_state.current_file_path else 'Fichier temporaire'}")
        
        if st.button("🔄 Changer de fichier"):
            st.session_state.df = None
            st.rerun()
            
        st.markdown("---")
        st.subheader("Extrat")
        export_format = st.selectbox("Format", ["Span (JSON)", "IOB (CoNLL)", "BILOU (CoNLL)"])
        
        if st.button("Générer l'export"):
            if "Span" in export_format:
                data_str = utils.export_json_span(st.session_state.df)
                file_name = "export_span.json"
                mime = "application/json"
            elif "IOB" in export_format:
                data_str = utils.export_to_conll(st.session_state.df, "IOB")
                file_name = "export_iob.txt"
                mime = "text/plain"
            elif "BILOU" in export_format:
                data_str = utils.export_to_conll(st.session_state.df, "BILOU")
                file_name = "export_bilou.txt"
                mime = "text/plain"
            
            st.download_button("⬇️ Télécharger", data_str, file_name=file_name, mime=mime)


    # LAYOUT : Colonne Gauche (Annotation) | Colonne Droite (Labels)
    col_main, col_labels = st.columns([3, 1])

    # --- COLONNE DROITE : LABELS ---
    with col_labels:
        st.subheader("🏷️ Labels")
        
        # Liste des labels
        for label, color in st.session_state.labels.items():
            st.markdown(
                f"<div style='background-color: {color}; padding: 5px; border-radius: 4px; "
                f"color: white; text-align: center; margin-bottom: 5px; font-size: 0.9em;'>{label}</div>",
                unsafe_allow_html=True
            )
            
        st.write("---")
        new_label = st.text_input("Nouveau label", label_visibility="collapsed", placeholder="Nouveau label...")
        if st.button("Ajouter", use_container_width=True):
            if new_label and new_label not in st.session_state.labels:
                st.session_state.labels[new_label] = get_next_color()
                st.rerun()

    # --- COLONNE PRINCIPALE : TEXTE & WORKSPACE ---
    with col_main:
        total_lines = len(st.session_state.df)
        
        # Navigation
        c1, c2, c3 = st.columns([1, 4, 1])
        if c1.button("⬅️", use_container_width=True):
             if st.session_state.current_index > 0:
                 save_current_state()
                 st.session_state.current_index -= 1
                 st.rerun()
        
        c2.markdown(f"<div style='text-align: center; padding-top: 5px;'>Ligne <b>{st.session_state.current_index + 1}</b> / {total_lines}</div>", unsafe_allow_html=True)
        
        if c3.button("➡️", use_container_width=True):
             if st.session_state.current_index < total_lines - 1:
                 save_current_state()
                 st.session_state.current_index += 1
                 st.rerun()

        # Affichage Texte
        try:
            current_row = st.session_state.df.iloc[st.session_state.current_index]
            text_col = "text" if "text" in st.session_state.df.columns else st.session_state.df.columns[0]
            current_text = str(current_row[text_col])
        except:
            current_text = ""

        current_annotations = st.session_state.annotations.get(st.session_state.current_index, [])

        # Zone Interaction (INPUT) - MOVED UP
        st.write("")
        with st.container(border=True):
            st.caption("Sélectionner du texte et un label")
            c_sel_text, c_sel_lbl, c_act = st.columns([3, 2, 1])
            
            sel_text = c_sel_text.text_input("Selection", placeholder="Copier-coller le texte...", label_visibility="collapsed")
            
            opts = list(st.session_state.labels.keys())
            sel_lbl = c_sel_lbl.selectbox("Label", opts if opts else [], label_visibility="collapsed", disabled=not opts)
            
            if c_act.button("Valider", type="primary", use_container_width=True, disabled=not opts):
                 if sel_text and sel_lbl and sel_text in current_text:
                     # Logique globale rapide (dupliquée un peu de utils ou intégrée ici)
                     count = 0 
                     for idx, row in st.session_state.df.iterrows():
                        txt_val = str(row.iloc[0])
                        if sel_text in txt_val:
                            start = txt_val.find(sel_text)
                            while start != -1:
                                end = start + len(sel_text)
                                annot = {'start': start, 'end': end, 'label': sel_lbl, 'text': sel_text}
                                l_annots = st.session_state.annotations.get(idx, [])
                                if not any(a['start'] == start and a['end'] == end and a['label'] == sel_lbl for a in l_annots):
                                    l_annots.append(annot)
                                    st.session_state.annotations[idx] = l_annots
                                    count += 1
                                start = txt_val.find(sel_text, end)
                     save_current_state()
                     st.toast(f"Ajouté : {count} occurrences")
                     st.rerun()
                 else:
                     st.error("Erreur sélection")

        st.markdown("### Texte")
        with st.container(border=True):
             annotated_text(*create_annotated_text_view(current_text, current_annotations))

        # Liste Annotations current (GRID 2 COLUMNS)
        if current_annotations:
            st.markdown("#### Annotations actives")
            
            cols_grid = st.columns(2)
            for i, annot in enumerate(current_annotations):
                 with cols_grid[i % 2].container(border=True):
                     c_pill, c_del = st.columns([8, 1])
                     with c_pill:
                         # Utilisation de annotated_text pour le style pillule
                         color = st.session_state.labels.get(annot['label'], "#CCCCCC")
                         annotated_text((annot['text'], annot['label'], color))
                     
                     with c_del:
                         if st.button("❌", key=f"del_{i}", help="Supprimer"):
                             st.session_state.annotations[st.session_state.current_index].pop(i)
                             save_current_state()
                             st.rerun()

if __name__ == "__main__":
    main()
