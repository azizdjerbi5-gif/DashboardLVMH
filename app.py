import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

# ================== 1. CONFIGURATION & STYLE ==================
st.set_page_config(
    page_title="Rapport Financier Avancé - LVMH",
    page_icon="💎",
    layout="wide"
)

# CSS AMÉLIORÉ : Fond moderne & Cartes élégantes
st.markdown("""
    /* ===== FORCER TEXTE KPI EN NOIR ===== */
    div[data-testid="stMetricLabel"] * {
        color: #000000 !important;
        font-weight: 600 !important;
    }

    div[data-testid="stMetricValue"] * {
        color: #000000 !important;
        font-weight: 800 !important;
    }

    div[data-testid="stMetricDelta"] * {
        color: #000000 !important;
        font-weight: 700 !important;
    }

<style>
    /* FOND GLOBAL : Dégradé subtil gris-bleu très clair */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* TITRES : Police moderne et couleur sombre */
    h1, h2, h3 {
        color: #1e293b !important;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        font-weight: 700;
    }
    
    /* CARTES (Métriques & Graphiques) : Fond blanc pur avec ombre douce */
    div[data-testid="stMetric"], .stPlotlyChart, .highlight-box {
        background-color: rgba(255, 255, 255, 0.95); /* Blanc légèrement transparent */
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05); /* Ombre portée douce */
        border: 1px solid rgba(255, 255, 255, 0.3);
    }
    
    /* Bordure colorée pour les KPIs */
    div[data-testid="stMetric"] {
        border-left: 5px solid #0099DD;
    }

    /* Boîte de mise en avant (RSI) */
    .highlight-box {
        border-left: 5px solid #0284c7;
        background-color: #f0f9ff;
    }
</style>
""", unsafe_allow_html=True)

# ================== 2. CHARGEMENT & CALCULS AVANCÉS ==================
@st.cache_data
def load_data():
    file_path = 'LVMH_2026-01-16.txt'
    try:
        df = pd.read_csv(file_path, sep='\t')
        df = df.rename(columns={
            'date': 'Date', 'ouv': 'Open', 'haut': 'High', 
            'bas': 'Low', 'clot': 'Close', 'vol': 'Volume'
        })
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
        df = df.sort_values(by='Date')
        
        # --- CALCULS TECHNIQUES ---
        # 1. Moyennes Mobiles
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        
        # 2. Bandes de Bollinger
        df['BB_High'] = df['SMA_20'] + (df['Close'].rolling(20).std() * 2)
        df['BB_Low'] = df['SMA_20'] - (df['Close'].rolling(20).std() * 2)
        
        # 3. RSI (Relative Strength Index) - 14 jours
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # 4. MACD
        exp12 = df['Close'].ewm(span=12, adjust=False).mean()
        exp26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp12 - exp26
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        return df
    except Exception as e:
        st.error(f"Erreur critique : {e}")
        return None

# ================== 3. INTERFACE DASHBOARD ==================

df = load_data()

if df is not None:
    # --- HEADER EXÉCUTIF ---
    st.markdown("<h1>💎 Analyse Stratégique : Action LVMH</h1>", unsafe_allow_html=True)
    st.markdown("**Rapport de Performance & Analyse Technique** | Période : 12 derniers mois")
    
    st.divider()

    # --- KPI BOARD ---
    last = df.iloc[-1]
    prev = df.iloc[-2]
    start = df.iloc[0]
    
    # Variations
    var_jour = ((last['Close'] - prev['Close']) / prev['Close']) * 100
    var_an = ((last['Close'] - start['Close']) / start['Close']) * 100
    volatilité_hebdo = df['Close'].pct_change().rolling(5).std().iloc[-1] * 100 # Volatilité sur 5 jours

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Dernier Cours", f"{last['Close']:.2f} €", f"{var_jour:.2f} %")
    col2.metric("Perf. YTD (1 an)", f"{var_an:.2f} %", delta_color="normal")
    col3.metric("Plus Haut (An)", f"{df['High'].max():.2f} €")
    col4.metric("Volatilité (5j)", f"{volatilité_hebdo:.2f} %", help="Écart-type des rendements sur 5 jours")
    col5.metric("Volume (Moyen)", f"{int(df['Volume'].mean()/1000):,} K", help="Volume quotidien moyen en milliers")

    st.markdown("---")

    # --- SECTION 1 : ANALYSE DES PRIX & TENDANCES ---
    col_chart, col_tech = st.columns([3, 1])
    
    with col_chart:
        st.subheader("📈 Dynamique des Prix & Bandes de Bollinger")
        
        fig = go.Figure()
        
        # Bandes de Bollinger (Zone grise)
        fig.add_trace(go.Scatter(
            x=df['Date'], y=df['BB_High'], mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=df['Date'], y=df['BB_Low'], mode='lines', line=dict(width=0), fill='tonexty', 
            fillcolor='rgba(200, 200, 200, 0.2)', name='Bandes Bollinger'
        ))
        
        # Cours & Moyennes
        fig.add_trace(go.Scatter(x=df['Date'], y=df['Close'], mode='lines', name='Cours Clôture', line=dict(color='#0f172a', width=2)))
        fig.add_trace(go.Scatter(x=df['Date'], y=df['SMA_50'], mode='lines', name='MM 50j (Tendance)', line=dict(color='#f59e0b', width=1.5)))
        
        fig.update_layout(
            template="plotly_white", height=500, hovermode="x unified",
            legend=dict(orientation="h", y=1.02, x=0),
            margin=dict(l=0, r=0, t=0, b=0),
            plot_bgcolor='rgba(0,0,0,0)', # Fond du graphique transparent pour voir le dégradé
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_tech:
        st.subheader("📋 Synthèse Technique")
        
        # Signal RSI
        last_rsi = last['RSI']
        if last_rsi > 70:
            rsi_signal = "🔴 SURACHAT (Vente?)"
            rsi_color = "red"
        elif last_rsi < 30:
            rsi_signal = "🟢 SURVENTE (Achat?)"
            rsi_color = "green"
        else:
            rsi_signal = "⚪ NEUTRE"
            rsi_color = "gray"
            
        st.markdown(f"""
        <div class="highlight-box">
            <b>Indicateur RSI (14j) :</b> {last_rsi:.1f}<br>
            <span style="color:{rsi_color}; font-weight:bold;">{rsi_signal}</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("**Niveaux Clés :**")
        st.write(f"Resistance (Haut): **{df['High'].max():.2f} €**")
        st.write(f"Support (Bas): **{df['Low'].min():.2f} €**")
        
        st.info("Les Bandes de Bollinger (zone grise) indiquent la volatilité. Un resserrement annonce souvent un mouvement violent à venir.")

    # --- SECTION 2 : OSCILLATEURS (MACD & RSI) ---
    st.subheader("⚡ Indicateurs de Momentum (MACD & RSI)")
    
    tab_macd, tab_rsi = st.tabs(["MACD (Tendance)", "RSI (Force Relative)"])
    
    with tab_macd:
        fig_macd = go.Figure()
        fig_macd.add_trace(go.Scatter(x=df['Date'], y=df['MACD'], name='MACD', line=dict(color='#2563eb')))
        fig_macd.add_trace(go.Scatter(x=df['Date'], y=df['Signal_Line'], name='Signal', line=dict(color='#dc2626')))
        
        # Histogramme
        colors = np.where(df['MACD'] - df['Signal_Line'] > 0, '#4ade80', '#f87171')
        fig_macd.add_trace(go.Bar(x=df['Date'], y=df['MACD'] - df['Signal_Line'], name='Histogramme', marker_color=colors))
        
        fig_macd.update_layout(
            template="plotly_white", height=300, margin=dict(t=10, b=10),
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_macd, use_container_width=True)
        
    with tab_rsi:
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(x=df['Date'], y=df['RSI'], name='RSI', line=dict(color='#7c3aed')))
        
        # Zones 30/70
        fig_rsi.add_shape(type="line", x0=df['Date'].min(), x1=df['Date'].max(), y0=70, y1=70, line=dict(color="red", dash="dash"))
        fig_rsi.add_shape(type="line", x0=df['Date'].min(), x1=df['Date'].max(), y0=30, y1=30, line=dict(color="green", dash="dash"))
        
        fig_rsi.update_layout(
            template="plotly_white", height=300, yaxis=dict(range=[0, 100]), margin=dict(t=10, b=10),
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_rsi, use_container_width=True)

    # --- SECTION 3 : SAISONNALITÉ (HEATMAP) ---
    st.subheader("📅 Performance Mensuelle (Saisonnalité)")
    
    # Préparation des données pour la heatmap
    df['Year'] = df['Date'].dt.year
    df['Month'] = df['Date'].dt.month_name()
    df['Month_Num'] = df['Date'].dt.month
    
    # Calcul rendement mensuel
    monthly_perf = df.groupby(['Year', 'Month', 'Month_Num'])['Close'].apply(lambda x: (x.iloc[-1] - x.iloc[0]) / x.iloc[0] * 100).reset_index()
    monthly_perf = monthly_perf.sort_values('Month_Num')
    
    fig_heat = px.bar(
        monthly_perf, x='Month', y='Close', color='Close',
        color_continuous_scale='RdYlGn', 
        labels={'Close': 'Performance (%)'},
        text_auto='.1f'
    )
    fig_heat.update_layout(
        template="plotly_white", height=350,
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    # --- FOOTER ---
    with st.expander("📂 Télécharger les données brutes (Excel/CSV)"):
        st.dataframe(df, use_container_width=True)

else:
    st.error("Fichier de données introuvable.")

