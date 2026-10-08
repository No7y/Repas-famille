import streamlit as st
import pandas as pd
import random

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Planning Repas Famille", page_icon="🍽️", layout="centered")
st.title("🍽️ Planning des Repas Famille")

# ID de ton fichier Google Sheets
SHEET_ID = "1cKJplaSqrLPk5sq8QjIOK53dAoDhSplvg0inEH7L94g"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

# --- CHARGEMENT DES DONNÉES SÉCURISÉ ---
@st.cache_data(ttl=300)
def load_data():
    # Timeout de 5s pour éviter que l'app ne tourne en boucle indéfiniment
    df = pd.read_csv(CSV_URL, timeout=5)
    df.columns = df.columns.str.strip()
    df["Temps_num"] = pd.to_numeric(df["Temps de préparation (min)"], errors='coerce').fillna(60)
    return df

try:
    df = load_data()
except Exception as e:
    st.error("Impossible de lire le Google Sheets. Vérifiez le partage public.")
    st.stop()

JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
REPAS_TYPES = ["Déjeuner", "Dîner"]

# --- DÉFINITION DES TEMPS DE PRÉPARATION PAR DÉFAUT ---
def get_default_max_time(jour, repas):
    if repas == "Dîner":
        if jour in ["Lundi", "Jeudi"]:
            return 5
        elif jour in ["Mardi", "Vendredi"]:
            return 30
    return 60

# --- INITIALISATION DE L'ÉTAT (SESSION STATE) ---
if 'planning' not in st.session_state:
    st.session_state.planning = {f"{j}_{r}": None for j in JOURS for r in REPAS_TYPES}

if 'used_items' not in st.session_state:
    st.session_state.used_items = []

# --- CONFIGURATION ET CONTRAINTES DES REPAS ---
st.subheader("⚙️ Configuration des Repas")

# Checkboxes pour choisir quels repas planifier (Lundi, Mardi, Jeudi, Vendredi midi décochés par défaut)
active_meals = {}
for j in JOURS:
    st.write(f"**{j}**")
    col_d, col_n = st.columns(2)
    with col_d:
        default_active = False if j in ["Lundi", "Mardi", "Jeudi", "Vendredi"] else True
        active_meals[f"{j}_Déjeuner"] = st.checkbox("Déjeuner", value=default_active, key=f"active_{j}_Déjeuner")
    with col_n:
        active_meals[f"{j}_Dîner"] = st.checkbox("Dîner", value=True, key=f"active_{j}_Dîner")

# Accordéon pour personnaliser les temps de préparation max
max_times = {}
with st.expander("⏱️ Ajuster les temps de préparation max (min)"):
    for j in JOURS:
        col1, col2 = st.columns(2)
        with col1:
            max_times[f"{j}_Déjeuner"] = st.number_input(
                f"{j} Déjeuner", min_value=5, max_value=120, 
                value=get_default_max_time(j, "Déjeuner"), step=5, key=f"time_{j}_Déjeuner"
            )
        with col2:
            max_times[f"{j}_Dîner"] = st.number_input(
                f"{j} Dîner", min_value=5, max_value=120, 
                value=get_default_max_time(j, "Dîner"), step=5, key=f"time_{j}_Dîner"
            )

# --- ALGORITHME DE TIRAGE ---
def get_available_items(role, max_time):
    """Filtre les éléments par rôle, disponibilité (non utilisés) et temps de préparation."""
    role_col = "Rôle (Protéine / Féculent / Légume / Plat complet)"
    mask = (
        (df[role_col] == role) & 
        (~df["Nom de l'élément"].isin(st.session_state.used_items)) & 
        (df["Temps_num"] <= max_time)
    )
    return df[mask]["Nom de l'élément"].tolist()

def generate_meal_for_slot(slot_key):
    """Génère un repas pour un créneau donné en respectant le temps max."""
    max_time = max_times.get(slot_key, 60)
    
    # 30% de chance d'avoir un plat complet si disponible
    type_repas = random.choices(["Complet", "Modulaire"], weights=[0.3, 0.7])[0]
    
    repas = []
    if type_repas == "Complet":
        complets = get_available_items("Plat complet", max_time)
        if complets:
            repas = [random.choice(complets)]
        else:
            type_repas = "Modulaire"
            
    if type_repas == "Modulaire":
        prots = get_available_items("Protéine", max_time)
        fecs = get_available_items("Féculent", max_time)
        legs = get_available_items("Légume", max_time)
        
        if prots and fecs and legs:
            repas = [random.choice(prots), random.choice(fecs), random.choice(legs)]
        else:
            repas = [f"⚠️ Pas assez d'ingrédients (≤ {max_time} min)"]
            
    for item in repas:
        if not item.startswith("⚠️"):
            st.session_state.used_items.append(item)
            
    return repas

def regenerate_slot(slot_key):
    """Libère les ingrédients d'un créneau et en tire un nouveau."""
    repas_actuel = st.session_state.planning.get(slot_key)
    if repas_actuel:
        for item in repas_actuel:
            if item in st.session_state.used_items:
                st.session_state.used_items.remove(item)
    st.session_state.planning[slot_key] = generate_meal_for_slot(slot_key)

st.divider()

# --- BOUTON DE GÉNÉRATION GLOBALE ---
if st.button("🎲 Générer le planning de la semaine", type="primary", use_container_width=True):
    st.session_state.used_items = []
    for j in JOURS:
        for r in REPAS_TYPES:
            slot_key = f"{j}_{r}"
            if active_meals.get(slot_key, True):
                st.session_state.planning[slot_key] = generate_meal_for_slot(slot_key)
            else:
                st.session_state.planning[slot_key] = None

# --- AFFICHAGE DU PLANNING ---
st.subheader("📅 Votre Planning")

for j in JOURS:
    with st.container(border=True):
        st.markdown(f"### {j}")
        col_dej, col_din = st.columns(2)
        
        for col, r in zip([col_dej, col_din], REPAS_TYPES):
            slot_key = f"{j}_{r}"
            is_active = active_meals.get(slot_key, True)
            
            with col:
                st.caption(f"**{r}** (Max: {max_times.get(slot_key, 60)} min)")
                if not is_active:
                    st.write("❌ *Non planifié*")
                else:
                    repas = st.session_state.planning.get(slot_key)
                    if repas:
                        st.write("• " + "<br>• ".join(repas), unsafe_allow_html=True)
                        if st.button("🔄", key=f"btn_{slot_key}", help=f"Changer le {r} du {j}"):
                            regenerate_slot(slot_key)
                            st.rerun()
                    else:
                        st.write("—")
