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
@st.cache_data(ttl=60)  # Mise en cache pour éviter les anciens résultats
def load_data():
    try:
        url = "https://baseecoleback.parcoursnum.net/api/candidats"  
        response = requests.get(url, headers={"Cache-Control": "no-cache"})
        response.raise_for_status()
        data = response.json()

        # 1) Conversion en DataFrame
        df = pd.DataFrame(data)

        if df.empty:
            return df  # Retourne un DataFrame vide si l'API ne retourne rien

        # 2) Normalisation des données
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        df["created_at"] = df["created_at"].dt.tz_localize(None)  # Suppression du fuseau horaire

        df["sexe"] = df["sexe"].astype(str).str.lower().replace({
            "f": "Femme", "femme": "Femme", "female": "Femme",
            "m": "Homme", "homme": "Homme", "male": "Homme"
        })
        df.loc[~df["sexe"].isin(["Femme", "Homme"]), "sexe"] = "Inconnu"

        df["ville"] = df["ville"].fillna("Inconnue")  # Remplace NaN par "Inconnue"

        return df

    except Exception as e:
        st.error(f"Erreur de chargement des données : {e}")
        return pd.DataFrame()

# ---- 3) Lecture des données ----
df = load_data()

# ---- 4) Vérification des données ----
if df.empty:
    st.warning("⚠️ Aucune donnée trouvée via l’API ou données invalides.")
    st.stop()

# ---- 5) Filtres ----
col_sexe, col_ville, col_periode = st.columns(3)

# 5.1 Filtre par sexe
sexe_options = ["Tous"] + sorted(df["sexe"].unique())
sexe_selected = col_sexe.selectbox("🧑‍🤝‍🧑 Filtrer par Sexe", sexe_options)

# 5.2 Filtre par ville (gestion des NaN et colonnes inexistantes)
if "ville" in df.columns and not df["ville"].empty:
    ville_options = ["Toutes"] + sorted(df["ville"].dropna().unique())
else:
    ville_options = ["Toutes"]
ville_selected = col_ville.selectbox("🏙️ Filtrer par Ville", ville_options)

# 5.3 Filtre par période (date range)
if not df["created_at"].isna().all():  # Vérifie si "created_at" contient des valeurs valides
    min_date = df["created_at"].min().date()
    max_date = df["created_at"].max().date()
    date_range = col_periode.date_input("📅 Filtrer par Période", [min_date, max_date])
else:
    st.warning("⚠️ Les dates sont manquantes ou invalides.")
    date_range = [None, None]

# ---- 6) Application des filtres ----
filtered_df = df.copy()

# 6.1 Filtre sexe
if sexe_selected != "Tous":
    filtered_df = filtered_df[filtered_df["sexe"] == sexe_selected]

# 6.2 Filtre ville
if ville_selected != "Toutes":
    filtered_df = filtered_df[filtered_df["ville"] == ville_selected]

# 6.3 Filtre période (si valide)
if date_range[0] is not None and date_range[1] is not None:
    start_date = pd.to_datetime(date_range[0])
    end_date = pd.to_datetime(date_range[1]) + timedelta(hours=23, minutes=59, seconds=59)
    filtered_df = filtered_df[
        (filtered_df["created_at"] >= start_date) & 
        (filtered_df["created_at"] <= end_date)
    ]

# ---- 7) KPIs ----
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
col_pie, col_bar = st.columns(2)

with col_pie:
    st.subheader("🧑‍🤝‍🧑 Répartition des Utilisateurs par Sexe")
    sexe_counts_filtered = filtered_df["sexe"].value_counts()
    fig_pie = go.Figure(go.Pie(labels=sexe_counts_filtered.index, values=sexe_counts_filtered.values))
    st.plotly_chart(fig_pie, use_container_width=True)

with col_bar:
    st.subheader("🏙️ Répartition des Utilisateurs par Ville")
    ville_counts_filtered = filtered_df["ville"].value_counts()
    fig_bar = go.Figure(go.Bar(x=ville_counts_filtered.index, y=ville_counts_filtered.values))
    st.plotly_chart(fig_bar, use_container_width=True)

# ---- 9) Évolution des Inscriptions ----
st.subheader("📈 Évolution des Inscriptions")

if not filtered_df.empty and "created_at" in filtered_df.columns:
    monthly_counts = (
        filtered_df.resample("M", on="created_at").size().rename("Nombre d’inscriptions")
    )

    fig_line = go.Figure(go.Scatter(x=monthly_counts.index, y=monthly_counts.values, mode="lines+markers"))
    fig_line.update_layout(xaxis_title="Date", yaxis_title="Nombre d’inscriptions")
    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.info("Aucune donnée à afficher pour la période/les filtres sélectionnés.")

# ---- 10) Tableau final ----
st.subheader("📋 Liste des Utilisateurs Filtrés")
st.dataframe(filtered_df, use_container_width=True)
