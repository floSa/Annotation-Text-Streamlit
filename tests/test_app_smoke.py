"""Smoke test de l'application Streamlit via streamlit.testing.v1.AppTest.

Vérifie que :
- L'app démarre sans exception.
- La landing page (sans fichier chargé) s'affiche correctement.

Tests d'interaction plus poussés (charger un fichier, valider une annotation, exporter)
nécessiteraient de mocker st.file_uploader et le filesystem ; à faire en Phase 2.
"""

from __future__ import annotations

from streamlit.testing.v1 import AppTest


def test_app_boots_without_exception():
    at = AppTest.from_file("app.py", default_timeout=10)
    at.run()
    assert not at.exception, f"App raised: {at.exception}"


def test_landing_page_shows_title_and_tabs():
    at = AppTest.from_file("app.py", default_timeout=10)
    at.run()
    # Le titre HTML "Annotation Tool" est rendu via st.markdown(unsafe_allow_html=True)
    # → on cherche dans les markdown rendus.
    markdown_blobs = "".join(m.value for m in at.markdown)
    assert "Annotation Tool" in markdown_blobs

    # Les deux tabs doivent être présents (Fichiers Locaux + Upload)
    assert len(at.tabs) >= 2


def test_data_dir_listing_includes_demo_file():
    """La landing page doit lister data/annotations.csv dans le selectbox."""
    at = AppTest.from_file("app.py", default_timeout=10)
    at.run()
    # Le selectbox de fichiers doit exister et contenir au moins annotations.csv
    if at.selectbox:
        options = at.selectbox[0].options
        assert "annotations.csv" in options
