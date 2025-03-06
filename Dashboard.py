import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import timedelta  

# ---- 1) Configuration de la page ----
st.set_page_config(
    page_title="Dashboard Utilisateurs",
    layout="wide"
)

# ---- 2) Chargement des données via API ----
@st.cache_data(ttl=60)  # Cache avec mise à jour toutes les 60 secondes
def load_data():
    try:
        url = "https://baseecoleback.parcoursnum.net/api/candidats"
        response = requests.get(url, headers={"Cache-Control": "no-cache"})
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data)

        if df.empty:
            return df  # Retourne un DataFrame vide pour éviter les erreurs

        # 1) Conversion de la colonne "created_at" en datetime
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        df["created_at"] = df["created_at"].dt.tz_localize(None)  # Suppression du fuseau horaire

        # 2) Normalisation de la colonne `sexe`
        df["sexe"] = df["sexe"].astype(str).str.lower().replace({
            "f": "Femme", "femme": "Femme", "female": "Femme",
            "m": "Homme", "homme": "Homme", "male": "Homme"
        })
        df.loc[~df["sexe"].isin(["Femme", "Homme"]), "sexe"] = "Inconnu"

        # 3) Normalisation de la colonne "ville"
        df["ville"] = df["ville"].fillna("Inconnue")  # Remplace NaN par "Inconnue"

        return df

    except Exception as e:
        st.error(f"Erreur lors du chargement des données : {e}")
        return pd.DataFrame()

# ---- 3) Lecture des données ----
df = load_data()

# ---- 4) Vérification des données ----
if df.empty:
    st.warning("⚠️ Aucune donnée trouvée via l’API ou données invalides.")
    st.stop()

# ---- 5) Filtres ----
st.sidebar.header("📊 Filtres")

# 5.1 Filtre par sexe
sexe_options = ["Tous"] + sorted(df["sexe"].unique())
sexe_selected = st.sidebar.selectbox("🧑‍🤝‍🧑 Filtrer par Sexe", sexe_options)

# 5.2 Filtre par ville (gestion des valeurs NaN et vérification si la colonne existe)
if "ville" in df.columns and not df["ville"].empty:
    ville_options = ["Toutes"] + sorted(df["ville"].dropna().unique())
else:
    ville_options = ["Toutes"]
ville_selected = st.sidebar.selectbox("🏙️ Filtrer par Ville", ville_options)

# 5.3 Filtre par période (date range)
min_date = df["created_at"].min().date()
max_date = df["created_at"].max().date()
date_range = st.sidebar.date_input("📅 Filtrer par Période", [min_date, max_date])

# ---- 6) Application des filtres ----
filtered_df = df.copy()

if sexe_selected != "Tous":
    filtered_df = filtered_df[filtered_df["sexe"] == sexe_selected]

if ville_selected != "Toutes":
    filtered_df = filtered_df[filtered_df["ville"] == ville_selected]

start_date = pd.to_datetime(date_range[0])
end_date = pd.to_datetime(date_range[1]) + timedelta(hours=23, minutes=59, seconds=59)

filtered_df = filtered_df[
    (filtered_df["created_at"] >= start_date) & 
    (filtered_df["created_at"] <= end_date)
]

# ---- 7) KPIs ----
st.markdown("### 📌 Indicateurs Clés (KPIs)")
kpi_col1, kpi_col2, kpi_col3 = st.columns(3)

total_contacts = len(filtered_df)
total_femmes = (filtered_df["sexe"] == "Femme").sum()
total_hommes = (filtered_df["sexe"] == "Homme").sum()

with kpi_col1:
    st.metric(label="👥 Nombre Total de Contacts", value=total_contacts)

with kpi_col2:
    st.metric(label="♀️ Nombre de Femmes", value=total_femmes)

with kpi_col3:
    st.metric(label="♂️ Nombre d'Hommes", value=total_hommes)

# ---- 8) Graphiques: Pie & Bar ----
st.markdown("### 📊 Répartition des Utilisateurs")

col_pie, col_bar = st.columns(2)

with col_pie:
    st.subheader("🧑‍🤝‍🧑 Répartition par Sexe")
    sexe_counts_filtered = filtered_df["sexe"].value_counts()
    fig_pie = go.Figure(go.Pie(labels=sexe_counts_filtered.index, values=sexe_counts_filtered.values))
    st.plotly_chart(fig_pie, use_container_width=True)

with col_bar:
    st.subheader("🏙️ Répartition par Ville")
    ville_counts_filtered = filtered_df["ville"].value_counts()
    fig_bar = go.Figure(go.Bar(x=ville_counts_filtered.index, y=ville_counts_filtered.values))
    st.plotly_chart(fig_bar, use_container_width=True)

# ---- 9) Évolution des Inscriptions ----
st.markdown("### 📈 Évolution des Inscriptions")
if not filtered_df.empty:
    if "id" in filtered_df.columns:
        monthly_counts = filtered_df.resample("M", on="created_at")["id"].count()
    else:
        monthly_counts = filtered_df.resample("M", on="created_at").size()

    fig_line = go.Figure(go.Scatter(x=monthly_counts.index, y=monthly_counts.values, mode="lines+markers"))
    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.info("Aucune donnée à afficher pour la période/les filtres sélectionnés.")

# ---- 10) Tableau final ----
st.markdown("### 📋 Liste des Utilisateurs Filtrés")
st.dataframe(filtered_df, use_container_width=True)
