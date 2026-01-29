from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
import unidecode

# ================== CONFIGURATION & STYLE ==================
st.set_page_config(
    page_title="Portfolio & Dashboard Transport — Aziz Djerbi",
    page_icon="🚇",
    layout="wide",
)

# CSS "Premium" pour un rendu magnifique (Cartes, Ombres, Couleurs)
st.markdown("""
<style>
    /* Fond global */
    .stApp { background-color: #f4f6f9; }
    
    /* Typographie */
    h1, h2, h3 { color: #2c3e50 !important; font-family: 'Segoe UI', sans-serif; }
    
    /* Conteneurs (Cartes blanches) */
    .css-1r6slb0, .stDataFrame, .stPlotlyChart {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e1e4e8;
    }
    
    /* KPIs (Métriques) */
    div[data-testid="stMetric"] {
        background-color: white;
        border-left: 5px solid #0099DD;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# ================== CONSTANTES ==================
MODE_COLOR_MAP = {
    "Métro": "#0099DD", "RER": "#009854", "Train": "#8A4B8F",
    "Tram": "#FF7900", "VAL": "#F7E300", "Autre": "#A9A9A9"
}

BASE_DIR = Path(__file__).resolve().parent

def locate_case_insensitive(name: str) -> Path:
    p = BASE_DIR / name
    if p.exists(): return p
    lname = name.lower()
    for child in BASE_DIR.iterdir():
        if child.name.lower() == lname: return child
    return p

PDF_PATH = locate_case_insensitive("CV_Aziz_Djerbi.pdf")
VALIDATIONS_PATH = locate_case_insensitive("validations-reseau-ferre-profils-horaires-par-jour-type-1er-trimestre.csv")
GARES_PATH = locate_case_insensitive("emplacement-des-gares-idf-data-generalisee.csv")

# ================== FONCTIONS DATA ==================
def clean_name(name):
    if not isinstance(name, str): return ""
    name = name.lower().strip()
    name = unidecode.unidecode(name)
    name = name.replace("(", "").replace(")", "").replace("-", " ")
    return " ".join(name.split())

@st.cache_data
def load_validations_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";")
    df = df.rename(columns={
        "libelle_arret": "gare", "cat_jour": "type_jour",
        "trnc_horr_60": "tranche_horaire", "pourcentage_validations": "pct_validations"
    })
    df["pct_validations"] = pd.to_numeric(df["pct_validations"], errors="coerce")
    
    def parse_heure(tranche):
        if not isinstance(tranche, str): return None
        try: return int(tranche.split("-")[0].replace("H", ""))
        except: return None

    df["heure"] = df["tranche_horaire"].apply(parse_heure)
    df = df.dropna(subset=["gare", "type_jour", "tranche_horaire", "pct_validations", "heure"])
    df["heure"] = df["heure"].astype(int)
    df["gare"] = df["gare"].apply(clean_name)
    return df

@st.cache_data
def load_gares_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";")
    if "nom_long" in df.columns: df = df.rename(columns={"nom_long": "gare"})
    
    if "geo_point_2d" in df.columns:
        def split_geo(s):
            if isinstance(s, str) and "," in s:
                p = s.split(",")
                return p[0].strip(), p[1].strip()
            return None, None
        df[["lat_str", "lon_str"]] = df["geo_point_2d"].apply(lambda x: pd.Series(split_geo(x)))
        df["lat"] = pd.to_numeric(df["lat_str"], errors="coerce")
        df["lon"] = pd.to_numeric(df["lon_str"], errors="coerce")

    for col in ["termetro", "terrer", "tertrain", "tertram", "terval"]:
        if col not in df.columns: df[col] = 0

    if "mode" not in df.columns:
        def infer_mode(row):
            if row.get("termetro") == 1: return "Métro"
            if row.get("terrer") == 1: return "RER"
            if row.get("tertrain") == 1: return "Train"
            if row.get("tertram") == 1: return "Tram"
            if row.get("terval") == 1: return "VAL"
            return "Autre"
        df["mode"] = df.apply(infer_mode, axis=1)

    df = df.dropna(subset=["gare"])
    df["gare"] = df["gare"].apply(clean_name)
    return df

@st.cache_data
def merge_validations_gares(df_val, df_gares):
    return df_val.merge(df_gares, on="gare", how="left")

# ================== FONCTIONS GRAPHIQUES ==================
def plot_profil_horaire(df):
    if df.empty: return
    fig = px.line(
        df.sort_values(["gare", "heure"]), x="heure", y="pct_validations", color="gare",
        markers=True, title="Profil horaire des validations", template="plotly_white",
        labels={"pct_validations": "% Validations"}
    )
    st.plotly_chart(fig, use_container_width=True)

def plot_boxplot(df):
    df_plot = df.dropna(subset=["mode"])
    if df_plot.empty: return
    fig = px.box(
        df_plot, x="mode", y="pct_validations", color="mode", color_discrete_map=MODE_COLOR_MAP,
        title="Distribution par Mode", template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)

def plot_heatmap(df):
    if df.empty: return
    pivot = df.groupby(["type_jour", "heure"])["pct_validations"].mean().reset_index().pivot(index="type_jour", columns="heure", values="pct_validations")
    fig = px.imshow(pivot, aspect="auto", title="Heatmap: Heure x Jour", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

def show_map(df):
    df_map = df.dropna(subset=["lat", "lon"])
    if df_map.empty: return
    df_agg = df_map.groupby(["gare", "lat", "lon", "mode"], as_index=False)["pct_validations"].sum()
    fig = px.scatter_mapbox(
        df_agg, lat="lat", lon="lon", color="mode", size="pct_validations",
        color_discrete_map=MODE_COLOR_MAP, zoom=9, mapbox_style="carto-positron",
        title="Carte des Gares (Taille = Trafic)"
    )
    fig.update_layout(margin={"r":0,"t":30,"l":0,"b":0})
    st.plotly_chart(fig, use_container_width=True)

# ================== UI DASHBOARD ==================
def show_transport_dashboard():
    st.title("🚇 Dashboard Transport Île-de-France")
    st.markdown("Analyse des profils horaires et géographiques du réseau ferré.")

    if not VALIDATIONS_PATH.exists() or not GARES_PATH.exists():
        st.error("Fichiers CSV manquants.")
        return

    df_val = load_validations_data(VALIDATIONS_PATH)
    df_gares = load_gares_data(GARES_PATH)
    df_merged = merge_validations_gares(df_val, df_gares)

    # Filtres Sidebar
    st.sidebar.header("Filtres")
    days = ["Tous"] + sorted(df_val["type_jour"].unique())
    s_day = st.sidebar.selectbox("Type de jour", days)
    
    modes_dispo = sorted(df_merged.dropna(subset=['mode'])["mode"].unique())
    s_modes = st.sidebar.multiselect("Modes", modes_dispo, default=["Métro", "RER"])
    
    # Filtrage Gares dynamique
    df_pre_filt = df_merged[df_merged["mode"].isin(s_modes)] if s_modes else df_merged
    gares_dispo = sorted(df_pre_filt["gare"].unique())
    s_gares = st.sidebar.multiselect("Gares", gares_dispo, default=gares_dispo[:5] if gares_dispo else None)

    # Application filtres
    df_filt = df_val.copy()
    if s_day != "Tous": df_filt = df_filt[df_filt["type_jour"] == s_day]
    if s_gares: df_filt = df_filt[df_filt["gare"].isin(s_gares)]
    
    df_merged_filt = df_merged.merge(df_filt[["gare", "type_jour", "heure", "pct_validations"]], on=["gare", "type_jour", "heure", "pct_validations"])

    # KPIs
    c1, c2, c3 = st.columns(3)
    c1.metric("Gares affichées", len(s_gares) if s_gares else "Toutes")
    c2.metric("Points de données", len(df_filt))
    c3.metric("Modes analysés", len(s_modes) if s_modes else "Tous")

    st.markdown("---")

    # Graphiques Ligne 1
    c_left, c_right = st.columns(2)
    with c_left: plot_profil_horaire(df_filt)
    with c_right: plot_boxplot(df_merged_filt)

    st.markdown("---")

    # Graphiques Ligne 2
    plot_heatmap(df_filt)
    
    st.markdown("---")
    
    # Carte
    show_map(df_merged_filt)

# ================== UI CV (SANS PHOTO) ==================
def show_cv():
    st.title("AZIZ DJERBI")
    st.markdown("### 🎓 Étudiant Data Analyst en recherche d'alternance")
    st.write("📍 Pierrefitte-sur-Seine • 🚗 Permis B • 📞 07 78 16 05 47")

    if PDF_PATH.exists():
        st.download_button("📄 Télécharger CV (PDF)", PDF_PATH.read_bytes(), file_name="CV_Aziz.pdf")
    
    st.markdown("---")
    
    t1, t2, t3, t4, t5 = st.tabs(["Profil", "Expériences", "Formation", "Projets", "Compétences"])
    
    with t1:
        st.write("Passionné par la Data, je cherche une alternance pour mettre en pratique mes compétences en Python, SQL et BI.")
    
    with t2:
        st.info("**Stagiaire Data Analyst - Laevitas (Tunis)** (Juin-Août 2025)\n\nMonitoring Cloud (AWS/Azure), Pipelines Data, Dashboards.")
        
    with t3:
        st.write("**BUT Science des Données** (2023-2026) - IUT Paris Rives de Seine")
        st.write("**Bac Général** (2023) - Lycée La Salle Saint-Rosaire")
        
    with t4:
        c1, c2 = st.columns(2)
        c1.success("**Enquête IA**\n\nAnalyse statistique et présentation.")
        c2.success("**Reporting SQL**\n\nAnalyse ventes type Netflix.")
        
    with t5:
        st.progress(85, "Python / Pandas / Plotly")
        st.progress(80, "SQL")
        st.progress(75, "Power BI / Excel")

# ================== MAIN ==================
def main():
    st.sidebar.title("Menu")
    page = st.sidebar.radio("Navigation", ["Dashboard Transport", "CV / Portfolio"], label_visibility="collapsed")
    
    if page == "Dashboard Transport": show_transport_dashboard()
    else: show_cv()

if __name__ == "__main__":
    main()
