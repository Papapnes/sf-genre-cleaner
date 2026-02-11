import pandas as pd
import streamlit as st
from io import BytesIO

# --- Optional imports for gender guessing ---
try:
    from gender_guesser.detector import Detector
    from unidecode import unidecode
except Exception:
    Detector = None
    unidecode = None


st.set_page_config(page_title="SF Genre Cleaner", layout="wide")

st.title("🧹 Nettoyage Genre (Salesforce) — Nom complet → Male/Female")
st.write(
    "Upload ton CSV, on construit **Nom_complet**, puis on infère **Genre** (Male/Female seulement), "
    "et on te sort un fichier prêt à importer dans Salesforce."
)

# ---------- Helpers ----------
def auto_pick_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols_lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols_lower:
            return cols_lower[cand.lower()]
    return None

def ensure_dependencies():
    if Detector is None or unidecode is None:
        st.error(
            "Dépendances manquantes. Installe: gender-guesser et unidecode.\n\n"
            "Ex: `pip install gender-guesser unidecode`"
        )
        st.stop()

def detect_gender_binary(nom_complet: str, detector, default_gender: str) -> str:
    # Only returns Male/Female
    if pd.isna(nom_complet) or str(nom_complet).strip() == "":
        return default_gender

    prenom = str(nom_complet).strip().split()[0]
    prenom = unidecode(prenom)
    g = detector.get_gender(prenom)

    if g in ["female", "mostly_female"]:
        return "Female"
    return "Male"


# ---------- Upload ----------
uploaded = st.file_uploader("📤 Upload ton fichier CSV (export Salesforce)", type=["csv"])

if uploaded is None:
    st.info("Ajoute un fichier CSV pour commencer.")
    st.stop()

# Read CSV
try:
    df = pd.read_csv(uploaded)
except Exception:
    # fallback for separators
    df = pd.read_csv(uploaded, sep=";")

st.subheader("1) Aperçu du fichier")
st.dataframe(df.head(20), use_container_width=True)

# ---------- Column mapping ----------
st.subheader("2) Sélection des colonnes")

# Auto-detect (French + English common variants)
id_auto = auto_pick_col(df, ["Id constituant", "Constituent Id", "Constituent ID", "ConstituentId", "ID"])
prenom_auto = auto_pick_col(df, ["Prénom", "Prenom", "First Name", "Donor_First_Name", "FirstName"])
nom_auto = auto_pick_col(df, ["Nom", "Last Name", "Donor_Last_Name", "LastName"])

col1, col2, col3 = st.columns(3)

with col1:
    col_id = st.selectbox(
        "Colonne ID (Id constituant)",
        options=df.columns.tolist(),
        index=df.columns.tolist().index(id_auto) if id_auto in df.columns else 0
    )
with col2:
    col_prenom = st.selectbox(
        "Colonne Prénom",
        options=df.columns.tolist(),
        index=df.columns.tolist().index(prenom_auto) if prenom_auto in df.columns else 0
    )
with col3:
    col_nom = st.selectbox(
        "Colonne Nom",
        options=df.columns.tolist(),
        index=df.columns.tolist().index(nom_auto) if nom_auto in df.columns else 0
    )

default_gender = st.radio(
    "Valeur par défaut si prénom inconnu / vide",
    options=["Male", "Female"],
    index=0,
    horizontal=True
)

st.caption("💡 L’app ne garde que 3 colonnes au final: ID, Nom_complet, Genre.")

# ---------- Run pipeline ----------
st.subheader("3) Générer Nom_complet + Genre")

run_btn = st.button("🚀 Lancer le pipeline", type="primary")

if run_btn:
    ensure_dependencies()

    detector = Detector(case_sensitive=False)

    # Create Nom_complet
    temp = df.copy()
    temp["Nom_complet"] = (
        temp[col_prenom].fillna("").astype(str).str.strip()
        + " "
        + temp[col_nom].fillna("").astype(str).str.strip()
    )
    temp["Nom_complet"] = temp["Nom_complet"].str.replace(r"\s+", " ", regex=True).str.strip()

    # Final table: ONLY 3 columns
    df_final = temp[[col_id, "Nom_complet"]].copy()
    df_final.rename(columns={col_id: "Id constituant"}, inplace=True)

    df_final["Genre"] = df_final["Nom_complet"].apply(
        lambda x: detect_gender_binary(x, detector, default_gender)
    )

    # Optional: drop empty IDs
    df_final = df_final[df_final["Id constituant"].notna()].copy()

    st.success("✅ Pipeline terminé.")
    st.subheader("Résultat (3 colonnes)")
    st.dataframe(df_final.head(50), use_container_width=True)

    st.subheader("Stats Genre")
    st.write(df_final["Genre"].value_counts(dropna=False))

    # Download CSV
    out = BytesIO()
    df_final.to_csv(out, index=False, encoding="utf-8-sig")
    st.download_button(
        "⬇️ Télécharger le CSV prêt Salesforce",
        data=out.getvalue(),
        file_name="SF_update_genre.csv",
        mime="text/csv"
    )
