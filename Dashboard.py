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
@st.cache_data
def load_data():
    try:
        url = "https://baseecoleback.parcoursnum.net/api/candidats"
        response = requests.get(url, headers={"Cache-Control": "no-cache"})
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.error(f"Erreur lors du chargement des données : {e}")
        return pd.DataFrame()

        # 2) Conversion en DataFrame
        df = pd.DataFrame(data)

        # 3) Conversion de la colonne "created_at" en datetime
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")

        # 4) Suppression du fuseau horaire pour éviter les conflits
        df["created_at"] = df["created_at"].dt.tz_localize(None)

        # 5) Normalisation de la colonne `sexe`
        df["sexe"] = df["sexe"].astype(str).str.lower()
        df["sexe"] = df["sexe"].replace({
            "f": "Femme", "femme": "Femme",
            "female": "Femme",
            "m": "Homme", "homme": "Homme",
            "male": "Homme",
        })
        df.loc[~df["sexe"].isin(["Femme", "Homme"]), "sexe"] = "Inconnu"

        # 6) Normalisation de la colonne "ville"
        df["ville"] = df["ville"].fillna("Inconnue")

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

# 5.2 Filtre par ville
ville_options = ["Toutes"] + sorted(df["ville"].unique())
ville_selected = col_ville.selectbox("🏙️ Filtrer par Ville", ville_options)

# 5.3 Filtre par période (date range)
min_date = df["created_at"].min().date()
max_date = df["created_at"].max().date()
date_range = col_periode.date_input("📅 Filtrer par Période", [min_date, max_date])

# ---- 6) Application des filtres ----
filtered_df = df.copy()

# 6.1 Filtre sexe
if sexe_selected != "Tous":
    filtered_df = filtered_df[filtered_df["sexe"] == sexe_selected]

# 6.2 Filtre ville
if ville_selected != "Toutes":
    filtered_df = filtered_df[filtered_df["ville"] == ville_selected]

# 6.3 Filtre période
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
    st.markdown(f"""
    <div style="padding: 20px; border-radius: 10px; background-color: #F0F0F0; text-align: center;">
        <h4 style="color: #4A4A4A;">👥 Nombre Total de Contacts</h4>
        <h2 style="color: #6A5ACD;">{total_contacts}</h2>
    </div>
    """, unsafe_allow_html=True)

with kpi_col2:
    st.markdown(f"""
    <div style="padding: 20px; border-radius: 10px; background-color: #F0F0F0; text-align: center;">
        <h4 style="color: #4A4A4A;">♀️ Nombre de Femmes</h4>
        <h2 style="color: #E91E63;">{total_femmes}</h2>
    </div>
    """, unsafe_allow_html=True)

with kpi_col3:
    st.markdown(f"""
    <div style="padding: 20px; border-radius: 10px; background-color: #F0F0F0; text-align: center;">
        <h4 style="color: #4A4A4A;">♂️ Nombre d'Hommes</h4>
        <h2 style="color: #2196F3;">{total_hommes}</h2>
    </div>
    """, unsafe_allow_html=True)

# ---- 8) Graphiques: Pie & Bar ----
col_pie, col_bar = st.columns(2)

with col_pie:
    st.subheader("🧑‍🤝‍🧑 Répartition des Utilisateurs par Sexe")
    sexe_counts_filtered = filtered_df["sexe"].value_counts()
    fig_pie = go.Figure(
        go.Pie(
            labels=sexe_counts_filtered.index,
            values=sexe_counts_filtered.values,
            textinfo="percent+label",
            hole=0.4
        )
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with col_bar:
    st.subheader("🏙️ Répartition des Utilisateurs par Ville")
    ville_counts_filtered = filtered_df["ville"].value_counts()
    fig_bar = go.Figure(
        go.Bar(
            x=ville_counts_filtered.index,
            y=ville_counts_filtered.values
        )
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# ---- 9) Line Chart - Évolution des Inscriptions ----
st.subheader("📈 Évolution des Inscriptions")

if not filtered_df.empty:
    if "id" in filtered_df.columns:
        monthly_counts = (
            filtered_df
            .resample("M", on="created_at")["id"]
            .count()
            .rename("Nombre d’inscriptions")
        )
    else:
        monthly_counts = (
            filtered_df
            .resample("M", on="created_at")
            .size()
            .rename("Nombre d’inscriptions")
        )

    fig_line = go.Figure(
        go.Scatter(
            x=monthly_counts.index,
            y=monthly_counts.values,
            mode="lines+markers"
        )
    )
    fig_line.update_layout(
        xaxis_title="Date",
        yaxis_title="Nombre d’inscriptions"
    )
    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.info("Aucune donnée à afficher pour la période/les filtres sélectionnés.")

# ---- 10) Tableau final ----
st.subheader("📋 Liste des Utilisateurs Filtrés")
st.dataframe(filtered_df, use_container_width=True)
