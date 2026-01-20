from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
import unidecode

# ================== CONFIG & STYLE CSS "PREMIUM" ==================
st.set_page_config(
    page_title="Transport Analytics — Aziz Djerbi",
    page_icon="🚇",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS AMÉLIORÉ : Fond Dégradé & Cartes Flottantes
st.markdown(
    """
    <style>
    /* 1. LE FOND (BACKGROUND) */
    .stApp {
        /* Dégradé subtil gris-bleu vers blanc : effet pro et moderne */
        background: linear-gradient(180deg, #eef2f6 0%, #ffffff 100%);
        background-attachment: fixed;
    }

    /* 2. LA BARRE LATÉRALE (SIDEBAR) */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        box-shadow: 2px 0 10px rgba(0,0,0,0.05); /* Ombre légère à droite */
        border-right: 1px solid #e0e0e0;
    }

    /* 3. TEXTES */
    .stMarkdown, .stText, h1, h2, h3, h4, h5, h6, p, li, span, div {
        color: #2c3e50 !important;
        font-family: 'Segoe UI', sans-serif;
    }

    /* 4. CARTES GRAPHIQUES (Conteneurs Blancs) */
    .graph-container {
        background-color: #ffffff;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.05); /* Ombre plus douce et diffuse */
        border: 1px solid #f0f0f0;
        margin-bottom: 25px;
        transition: transform 0.2s; /* Petit effet si on voulait animer */
    }

    /* 5. KPIs (INDICATEURS) */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border-left: 5px solid #0099DD;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.03);
        width: 100%;
    }

    /* 6. TITRES DE SECTION */
    .custom-header {
        font-size: 1.6rem;
        font-weight: 700;
        color: #1a202c;
        margin-top: 30px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    /* 7. ENCARTS D'EXPLICATION */
    .insight-box {
        background: linear-gradient(to right, #f8f9fa, #ffffff);
        border-left: 4px solid #0099DD;
        padding: 15px;
        border-radius: 0 10px 10px 0;
        font-size: 0.95rem;
        margin-top: 15px;
        color: #4a5568;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02);
    }
    .insight-title {
        font-weight: 700;
        color: #0073a8;
        display: block;
        margin-bottom: 5px;
        text-transform: uppercase;
        font-size: 0.8rem;
        letter-spacing: 1px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ================== COULEURS INSTITUTIONNELLES ==================
MODE_COLOR_MAP = {
    "Métro": "#0099DD",
    "RER": "#E3051C",
    "Train": "#8A4B8F",
    "Tram": "#FF7900",
    "VAL": "#009854",
    "Autre": "#95a5a6",
    "Inconnu": "#bdc3c7"
}

# ================== LOCALISATION FICHIERS ==================
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

# ================== NETTOYAGE & DATA ==================
def clean_name(name):
    if not isinstance(name, str): return ""
    name = name.lower().strip()
    name = unidecode.unidecode(name)
    name = name.replace("-", " ").replace("'", " ").replace(".", "")
    name = name.replace("gare de ", "").replace("gare d ", "")
    return " ".join(name.split())

@st.cache_data
def load_data():
    # 1. Validations
    if not VALIDATIONS_PATH.exists(): return None, None, None
    df_v = pd.read_csv(VALIDATIONS_PATH, sep=";")
    df_v = df_v.rename(columns={
        "libelle_arret": "gare", "cat_jour": "type_jour", 
        "trnc_horr_60": "tranche_horaire", "pourcentage_validations": "pct_validations"
    })
    df_v["pct_validations"] = pd.to_numeric(df_v["pct_validations"], errors="coerce")
    
    def parse_heure(t):
        if not isinstance(t, str): return None
        try: return int(t.split("-")[0].replace("H", "").strip())
        except: return None
            
    df_v["heure"] = df_v["tranche_horaire"].apply(parse_heure)
    df_v = df_v.dropna(subset=["gare", "pct_validations", "heure"])
    df_v["heure"] = df_v["heure"].astype(int)
    df_v["gare_clean"] = df_v["gare"].apply(clean_name)

    # 2. Gares
    if not GARES_PATH.exists():
        df_v["mode"] = "Inconnu"
        df_v["lat"], df_v["lon"] = None, None
        return df_v, None, df_v

    df_g = pd.read_csv(GARES_PATH, sep=";")
    if "nom_long" in df_g.columns: df_g = df_g.rename(columns={"nom_long": "gare"})
    
    if "geo_point_2d" in df_g.columns:
        def split_geo(s):
            if isinstance(s, str) and "," in s:
                p = s.split(",")
                return float(p[0]), float(p[1])
            return None, None
        coords = df_g["geo_point_2d"].apply(split_geo)
        df_g["lat"] = coords.apply(lambda x: x[0] if x else None)
        df_g["lon"] = coords.apply(lambda x: x[1] if x else None)
    
    if "mode" not in df_g.columns:
        def get_mode(row):
            if row.get("termetro") == 1: return "Métro"
            if row.get("terrer") == 1: return "RER"
            if row.get("tertram") == 1: return "Tram"
            if row.get("tertrain") == 1: return "Train"
            return "Autre"
        df_g["mode"] = df_g.apply(get_mode, axis=1)

    df_g["gare_clean"] = df_g["gare"].apply(clean_name)
    df_g_unique = df_g.groupby("gare_clean").first().reset_index()

    # 3. Fusion
    df_m = df_v.merge(df_g_unique[["gare_clean", "lat", "lon", "mode"]], on="gare_clean", how="left")
    df_m["mode"] = df_m["mode"].fillna("Inconnu")
    
    return df_v, df_g, df_m

# ================== FONCTIONS GRAPHIQUES ==================
def add_insight(text):
    html = f"<div class='insight-box'><span class='insight-title'>💡 L'info Business</span>{text}</div>"
    st.markdown(html, unsafe_allow_html=True)

def plot_donut_mode(df):
    if df.empty: return
    df_agg = df.groupby("mode")["pct_validations"].sum().reset_index()
    fig = px.pie(df_agg, values="pct_validations", names="mode", hole=0.6, color="mode", color_discrete_map=MODE_COLOR_MAP)
    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=250, showlegend=True, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

def plot_bar_day_comparison(df):
    if df.empty: return
    df_agg = df.groupby("type_jour")["pct_validations"].mean().reset_index()
    fig = px.bar(df_agg, x="type_jour", y="pct_validations", color="type_jour", text_auto='.1f',
                 labels={"pct_validations": "Intensité Moyenne"}, template="plotly_white")
    fig.update_layout(showlegend=False, height=250, margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    fig.update_traces(textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

def plot_area_profile(df):
    if df.empty: return
    top_gares = df.groupby("gare")["pct_validations"].sum().nlargest(5).index.tolist()
    df_sub = df[df["gare"].isin(top_gares)]
    df_agg = df_sub.groupby(["gare", "heure"])["pct_validations"].mean().reset_index()
    fig = px.area(df_agg, x="heure", y="pct_validations", color="gare", line_shape="spline",
                  labels={"pct_validations": "% Valid."}, template="plotly_white")
    fig.update_layout(height=350, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=1.1), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

def plot_map_density(df):
    df_map = df.dropna(subset=["lat", "lon"])
    if df_map.empty:
        st.warning("Pas de données géographiques.")
        return
    df_agg = df_map.groupby(["gare", "lat", "lon", "mode"])["pct_validations"].sum().reset_index()
    fig = px.scatter_mapbox(df_agg, lat="lat", lon="lon", color="mode", size="pct_validations",
                            color_discrete_map=MODE_COLOR_MAP, mapbox_style="carto-positron",
                            zoom=9, center={"lat": 48.86, "lon": 2.35}, opacity=0.8, size_max=25, hover_name="gare")
    fig.update_layout(height=500, margin=dict(r=0, t=0, l=0, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

def plot_boxplot_distribution(df):
    if df.empty: return
    fig = px.box(df, x="mode", y="pct_validations", color="mode", color_discrete_map=MODE_COLOR_MAP, template="plotly_white")
    fig.update_layout(height=350, margin=dict(t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

# ================== DASHBOARD UI ==================
def show_transport_dashboard():
    st.markdown("<h1 style='text-align: center; color: #0099DD;'>🚇 Transport Analytics Île-de-France</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 1.2rem; color: #555; margin-bottom: 40px;'>Analyse des flux voyageurs et performance du réseau ferré.</p>", unsafe_allow_html=True)
    
    df_v, df_g, df_m = load_data()
    if df_m is None or df_m.empty:
        st.error("Erreur : Données introuvables.")
        return

    with st.sidebar:
        st.markdown("### 🎛️ Filtres")
        days = ["Tous"] + sorted(df_m["type_jour"].dropna().unique().tolist())
        s_day = st.selectbox("Type de jour", days)
        
        avail_modes = sorted(df_m["mode"].unique().tolist())
        default_modes = [m for m in ["Métro", "RER"] if m in avail_modes]
        s_modes = st.multiselect("Modes", avail_modes, default=default_modes)
        
        df_pre = df_m.copy()
        if s_modes: df_pre = df_pre[df_pre["mode"].isin(s_modes)]
        gares_list = sorted(df_pre["gare"].unique().tolist())
        s_gares = st.multiselect("Gares", gares_list[:100])
        
        st.markdown("---")
        st.info(f"📊 **Base de données :** {len(df_m):,} lignes.")

    df_filt = df_m.copy()
    if s_day != "Tous": df_filt = df_filt[df_filt["type_jour"] == s_day]
    if s_modes: df_filt = df_filt[df_filt["mode"].isin(s_modes)]
    if s_gares: df_filt = df_filt[df_filt["gare"].isin(s_gares)]

    if df_filt.empty:
        st.warning("Aucune donnée.")
        return

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gares", df_filt["gare"].nunique())
    c2.metric("Mode Dominant", df_filt["mode"].mode()[0] if not df_filt.empty else "-")
    peak = df_filt.groupby("heure")["pct_validations"].mean().idxmax()
    c3.metric("Pic Horaire", f"{peak}h00")
    c4.metric("Lignes Analysées", f"{len(df_filt):,}")
    
    # Ligne 1
    st.markdown("<div class='custom-header'>📍 Géographie & Répartition</div>", unsafe_allow_html=True)
    c_map, c_charts = st.columns([2, 1])
    with c_map:
        with st.container():
            st.markdown("<div class='graph-container'>", unsafe_allow_html=True)
            st.markdown("##### Carte de Densité")
            plot_map_density(df_filt)
            add_insight("Identifie les nœuds majeurs et la couverture territoriale.")
            st.markdown("</div>", unsafe_allow_html=True)
            
    with c_charts:
        with st.container():
            st.markdown("<div class='graph-container'>", unsafe_allow_html=True)
            st.markdown("##### Parts de Marché")
            plot_donut_mode(df_filt)
            st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("")
        with st.container():
            st.markdown("<div class='graph-container'>", unsafe_allow_html=True)
            st.markdown("##### Intensité : Semaine vs WE")
            plot_bar_day_comparison(df_filt)
            add_insight("Permet de distinguer gares de travail vs résidentielles.")
            st.markdown("</div>", unsafe_allow_html=True)

    # Ligne 2
    st.markdown("<div class='custom-header'>⏰ Dynamique Temporelle</div>", unsafe_allow_html=True)
    c_line, c_box = st.columns([2, 1])
    with c_line:
        with st.container():
            st.markdown("<div class='graph-container'>", unsafe_allow_html=True)
            st.markdown("##### Profils Horaires (Top 5)")
            plot_area_profile(df_filt)
            add_insight("Essentiel pour le dimensionnement de l'offre aux heures de pointe.")
            st.markdown("</div>", unsafe_allow_html=True)
            
    with c_box:
        with st.container():
            st.markdown("<div class='graph-container'>", unsafe_allow_html=True)
            st.markdown("##### Variabilité (Boxplot)")
            plot_boxplot_distribution(df_filt)
            st.markdown("</div>", unsafe_allow_html=True)

# ================== CV UI (SANS PHOTO) ==================
def show_cv():
    st.markdown("<h1 style='color:#2c3e50; text-align:left;'>AZIZ DJERBI</h1>", unsafe_allow_html=True)
    st.markdown("### 🎓 Étudiant Data Analyst en recherche d'alternance")
    st.write("📍 Pierrefitte-sur-Seine • 🚗 Permis B • 📞 07 78 16 05 47")

    if PDF_PATH.exists():
        with open(PDF_PATH, "rb") as f:
            st.download_button("📄 Télécharger mon CV (PDF)", f, file_name="CV_Aziz_Djerbi.pdf")

    st.divider()
    tab_profil, tab_exp, tab_form, tab_proj, tab_comp = st.tabs(["Profil", "Expériences", "Formations", "Projets", "Compétences"])

    with tab_profil:
        st.write("Passionné par la Data, je cherche une alternance pour mettre mes compétences à profit.")
        c1, c2 = st.columns(2)
        c1.metric("Data Stack", "Python, SQL, Power BI")
        c2.metric("Langues", "Anglais B2, Allemand B1")

    with tab_exp:
        st.markdown("**Stagiaire Data Analyst — Laevitas (Tunis)** (Juin-Août 2025)")
        st.write("- Pipeline Data, Cost Monitoring, Dashboards Plotly/Dash.")

    with tab_form:
        st.write("**BUT Science des Données** (2023-2026) - IUT Paris Rives de Seine")
        st.write("**Bac Général** (2023) - Lycée La Salle Saint-Rosaire")

    with tab_proj:
        c1, c2 = st.columns(2)
        c1.info("**Enquête IA** : Analyse statistique et présentation.")
        c2.info("**Reporting SQL** : Analyse ventes DVD type Netflix.")

    with tab_comp:
        st.progress(85, "Python (Pandas, Plotly)")
        st.progress(80, "SQL")
        st.progress(75, "Power BI / Excel")

# ================== MAIN ==================
def main():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("", ["Dashboard Transport", "CV / Portfolio"], label_visibility="collapsed")
    if page == "Dashboard Transport":
        show_transport_dashboard()
    else:
        show_cv()
    st.sidebar.markdown("---")
    st.sidebar.caption("© 2025 Aziz Djerbi")

if __name__ == "__main__":
    main()
