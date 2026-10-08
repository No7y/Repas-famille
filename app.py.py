import streamlit as st
import pandas as pd
import random

# --- CONFIGURATION ---
st.set_page_config(page_title="Repas Famille", page_icon="🍽️", layout="centered")
st.title("🍽️ Planning des Repas")

# ID de ton fichier Google Sheets
SHEET_ID = "1cKJplaSqrLPk5sq8QjIOK53dAoDhSplvg0inEH7L94g"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

# --- CHARGEMENT DES DONNÉES ---
@st.cache_data(ttl=600) # Met en cache pour 10 min pour éviter de surcharger GSheets
def load_data():
    df = pd.read_csv(CSV_URL)
    # Nettoyage basique des espaces
    df.columns = df.columns.str.strip()
    return df

try:
    df = load_data()
except Exception as e:
    st.error("Impossible de lire le Google Sheets. Vérifie qu'il est bien partagé en mode public.")
    st.stop()

# --- INITIALISATION DE L'ÉTAT (SESSION) ---
JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

if 'planning' not in st.session_state:
    st.session_state.planning = {jour: None for jour in JOURS}
if 'used_items' not in st.session_state:
    st.session_state.used_items = []

# --- LOGIQUE DE L'ALGORITHME ---
def get_available_items(role):
    """Retourne la liste des éléments d'un rôle donné qui n'ont pas encore été utilisés."""
    mask = (df["Rôle (Protéine / Féculent / Légume / Plat complet)"] == role) & (~df["Nom de l'élément"].isin(st.session_state.used_items))
    return df[mask]["Nom de l'élément"].tolist()

def generate_meal_for_day(jour):
    """Génère un repas selon le scénario (Modulaire ou Complet)."""
    
    # Pour illustrer tes contraintes : le week-end, on force souvent des plats complets ou plus longs
    is_weekend = jour in ["Samedi", "Dimanche"]
    prob_complet = 0.6 if is_weekend else 0.2 
    
    type_repas = random.choices(["Complet", "Modulaire"], weights=[prob_complet, 1 - prob_complet])[0]
    
    repas = []
    if type_repas == "Complet":
        complets = get_available_items("Plat complet")
        if complets:
            repas = [random.choice(complets)]
        else:
            type_repas = "Modulaire" # Fallback si plus de plats complets dispo
            
    if type_repas == "Modulaire":
        prots = get_available_items("Protéine")
        fecs = get_available_items("Féculent")
        legs = get_available_items("Légume")
        
        # On vérifie qu'on a au moins un élément de chaque
        if prots and fecs and legs:
            repas = [random.choice(prots), random.choice(fecs), random.choice(legs)]
        else:
            repas = ["⚠️ Pas assez d'ingrédients variés dispo, ajoutez-en !"]
            
    # Ajouter les éléments au registre des items utilisés (sauf les messages d'erreur)
    for item in repas:
        if not item.startswith("⚠️"):
            st.session_state.used_items.append(item)
            
    return repas

def regenerate_day(jour):
    """Libère les ingrédients d'un jour précis, puis tire un nouveau repas."""
    repas_actuel = st.session_state.planning[jour]
    if repas_actuel:
        for item in repas_actuel:
            if item in st.session_state.used_items:
                st.session_state.used_items.remove(item)
    st.session_state.planning[jour] = generate_meal_for_day(jour)

# --- INTERFACE UTILISATEUR ---

# Bouton de génération globale
if st.button("🎲 Générer toute la semaine", type="primary", use_container_width=True):
    st.session_state.used_items = [] # On réinitialise l'historique
    for jour in JOURS:
        st.session_state.planning[jour] = generate_meal_for_day(jour)

st.divider()

# Affichage du planning jour par jour
for jour in JOURS:
    with st.container(border=True):
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.markdown(f"**{jour}**")
            repas = st.session_state.planning[jour]
            if repas:
                # Affiche joliment le repas (ex: Steak + Frites + Petits pois)
                st.write(" • " + " <br> • ".join(repas), unsafe_allow_html=True)
            else:
                st.caption("Aucun repas planifié.")
                
        with col2:
            # Bouton pour regénérer uniquement ce jour
            if st.button("🔄", key=f"btn_{jour}", help=f"Changer le repas du {jour}"):
                regenerate_day(jour)
                st.rerun() # Rafraîchit l'interface