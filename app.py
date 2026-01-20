import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ================== 1. CONFIGURATION & STYLE ==================
st.set_page_config(
    page_title="Rapport Financier - LVMH",
    page_icon="💼",
    layout="wide"
)

# CSS pour un look "Rapport Financier"
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    h1 { color: #0f172a; font-family: 'Helvetica', sans-serif; }
    h3 { color: #334155; }
    
    /* Style des cartes de métriques */
    div[data-testid="stMetric"] {
        background-color: white;
        border: 1px solid #e2e8f0;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
</style>
""", unsafe_allow_html=True)

# ================== 2. FONCTIONS DE CHARGEMENT ==================
@st.cache_data
def load_data():
    file_path = 'LVMH_2026-01-16.txt'
    try:
        # Lecture du fichier
        df = pd.read_csv(file_path, sep='\t')
        
        # Nettoyage et Renommage
        df = df.rename(columns={
            'date': 'Date', 'ouv': 'Open', 'haut': 'High', 
            'bas': 'Low', 'clot': 'Close', 'vol': 'Volume'
        })
        
        # Conversion Date
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
        df = df.sort_values(by='Date')
        
        # Calculs techniques (Moyennes Mobiles)
        df['SMA_20'] = df['Close'].rolling(window=20).mean() # Court terme
        df['SMA_50'] = df['Close'].rolling(window=50).mean() # Moyen terme
        
        return df
    except Exception as e:
        st.error(f"Erreur de lecture : {e}")
        return None

# ================== 3. INTERFACE UTILISATEUR ==================

df = load_data()

if df is not None:
    # --- EN-TÊTE ---
    col_logo, col_title = st.columns([1, 5])
    with col_title:
        st.title("💼 Analyse de Performance : Action LVMH")
        st.markdown("**Période analysée :** 12 derniers mois | **Devise :** EUR")

    st.divider()

    # --- CALCULS KPIs (Dernier jour vs Historique) ---
    last = df.iloc[-1]
    prev = df.iloc[-2]
    start = df.iloc[0]
    
    # Variations
    var_jour = ((last['Close'] - prev['Close']) / prev['Close']) * 100
    var_an = ((last['Close'] - start['Close']) / start['Close']) * 100
    volatilité = (df['High'] - df['Low']).mean()

    # --- LIGNE 1 : CHIFFRES CLÉS (KPIs) ---
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.metric("Prix Actuel", f"{last['Close']:.2f} €", f"{var_jour:.2f} %")
    with c2:
        st.metric("Performance 1 An", f"{var_an:.2f} %", delta_color="normal")
    with c3:
        st.metric("Plus Haut (52 sem)", f"{df['High'].max():.2f} €")
    with c4:
        st.metric("Volume Moyen", f"{int(df['Volume'].mean()):,}")

    st.markdown("---")

    # --- LIGNE 2 : GRAPHIQUE PRINCIPAL & ANALYSE ---
    col_main, col_info = st.columns([3, 1])

    with col_main:
        st.subheader("📈 Évolution du Cours & Tendances")
        
        # Onglets pour changer de vue
        tab_line, tab_candle = st.tabs(["Vue Simplifiée (Courbe)", "Vue Trader (Bougies)"])
        
        with tab_line:
            fig = go.Figure()
            # Cours
            fig.add_trace(go.Scatter(x=df['Date'], y=df['Close'], mode='lines', name='Prix Clôture', line=dict(color='#0f172a', width=2)))
            # Moyennes Mobiles
            fig.add_trace(go.Scatter(x=df['Date'], y=df['SMA_20'], mode='lines', name='Moyenne 20j (Court terme)', line=dict(color='#3b82f6', width=1)))
            fig.add_trace(go.Scatter(x=df['Date'], y=df['SMA_50'], mode='lines', name='Moyenne 50j (Tendance fond)', line=dict(color='#f97316', width=1)))
            
            fig.update_layout(template="plotly_white", height=450, hovermode="x unified", legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig, use_container_width=True)

        with tab_candle:
            fig_c = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
            fig_c.update_layout(template="plotly_white", height=450, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig_c, use_container_width=True)

    with col_info:
        st.subheader("💡 Analyse Rapide")
        st.info("""
        **Comment lire ce graphique ?**
        
        1. **La ligne noire** indique le prix réel.
        2. **La ligne bleue (20j)** réagit vite : si le prix est au-dessus, c'est une dynamique positive à court terme.
        3. **La ligne orange (50j)** indique la tendance de fond.
        """)
        
        st.write("---")
        st.metric("Volatilité Moyenne", f"{volatilité:.2f} €", help="Écart moyen entre le plus haut et le plus bas d'une journée.")

    # --- LIGNE 3 : VOLUMES ---
    st.subheader("📊 Volumes d'échanges")
    fig_vol = px.bar(df, x='Date', y='Volume', color='Volume', color_continuous_scale='Blues')
    fig_vol.update_layout(template="plotly_white", height=250, showlegend=False)
    st.plotly_chart(fig_vol, use_container_width=True)

    # --- PIED DE PAGE : DONNÉES ---
    with st.expander("📂 Voir l'historique complet des données"):
        st.dataframe(df.sort_values(by='Date', ascending=False), use_container_width=True)

else:
    st.warning("⚠️ Veuillez placer le fichier 'LVMH_2026-01-16.txt' dans le même dossier.")
