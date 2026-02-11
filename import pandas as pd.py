import streamlit as st
import pandas as pd
from io import BytesIO
from gender_guesser.detector import Detector
from unidecode import unidecode

# ===============================
# Configuration de la page
# ===============================
st.set_page_config(page_title="SF Genre Cleaner", layout="wide")

st.title("🧹 Salesforce Genre Cleaner")
st.write(
    "Cette application identifie le genre (Male / Female uniquement) "
    "à partir de la colonne **Nom_complet**."
)

# ===============================
# Upload du fichier
# ===============================
uploaded_file = st.file_uploader(
    "📤 Upload ton fichier CSV Salesforce",
    type=["csv"]
)

if uploaded_file is None:
    st.info("Ajoute un fichier CSV pour commencer.")
    st.stop()

# ===============================
# Lecture du fichier
# ===============================
try:
    df = pd.read_csv(uploaded_file)
except:
    df = pd.read_csv(uploaded_file, sep=";")

st.subheader("Aperçu des données")
st.dataframe(df.head(20), use_container_width=True)

# ===============================
# Sélection des colonnes
# ===============================
st.subheader("Sélection des colonnes")

col_id = st.selectbox("Colonne ID (Id constituant)", df.columns)
col_nom_complet = st.selectbox("Colonne Nom_complet", df.columns)

default_gender = st.radio(
    "Valeur par défaut si prénom inconnu",
    options=["Male", "Female"],
    index=0,
    horizontal=True
)

# ===============================
# Fonction de détection
# ===============================
detector = Detector(case_sensitive=False)

def detect_gender_from_nom_complet(nom_complet):

    if pd.isna(nom_complet) or str(nom_complet).strip() == "":
        return default_gender

    # Extraction du premier mot (prénom supposé)
    prenom = str(nom_complet).strip().split()[0]

    # Suppression des accents
    prenom = unidecode(prenom)

    result = detector.get_gender(prenom)

    if result in ["female", "mostly_female"]:
        return "Female"
    else:
        return "Male"

# ===============================
# Lancer le pipeline
# ===============================
if st.button("🚀 Lancer l'identification du genre"):

    # Création du dataframe final (3 colonnes uniquement)
    df_final = df[[col_id, col_nom_complet]].copy()
    df_final.rename(columns={col_id: "Id constituant",
                             col_nom_complet: "Nom_complet"}, inplace=True)

    # Application détection
    df_final["Genre"] = df_final["Nom_complet"].apply(detect_gender_from_nom_complet)

    # Suppression lignes sans ID
    df_final = df_final[df_final["Id constituant"].notna()].copy()

    st.success("✅ Traitement terminé.")

    st.subheader("Résultat")
    st.dataframe(df_final.head(50), use_container_width=True)

    st.subheader("Statistiques Genre")
    st.write(df_final["Genre"].value_counts())

    # Export CSV
    output = BytesIO()
    df_final.to_csv(output, index=False, encoding="utf-8-sig")

    st.download_button(
        label="⬇️ Télécharger le fichier prêt Salesforce",
        data=output.getvalue(),
        file_name="SF_update_genre.csv",
        mime="text/csv"
    )
