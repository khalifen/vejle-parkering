import streamlit as st
import pandas as pd
import folium, requests, locale, json
from folium.plugins import MarkerCluster
from babel.dates import format_datetime
from datetime import datetime
from streamlit_folium import folium_static
from geopy.distance import geodesic
import numpy as np


def hent_vejr(api_key, lat, lon):
    url = f"https://api.weatherapi.com/v1/current.json?key={api_key}&q={lat},{lon}"
    response = requests.get(url)
    data = response.json()

    location = data['location']['name']
    temperature_c = data['current']['temp_c']
    condition = data['current']['condition']['text']
    icon = "https:" + data['current']['condition']['icon']
    precip_mm = data['current']['precip_mm']
    last_updated = datetime.strptime(data['current']['last_updated'], "%Y-%m-%d %H:%M")

    return {
        "location": location,
        "temperature_c": temperature_c,
        "condition": condition,
        "icon": icon,
        "precip_mm": precip_mm,
        "last_updated": last_updated
    }

# Parametre
api_key = "api_key"
lat = 55.7093
lon = 9.5356

vejr = hent_vejr(api_key, lat, lon)

locale.setlocale(locale.LC_ALL, 'da_DK.UTF-8')
today_date = datetime.today().strftime('%d. %B %Y')

# ---- DATA ----
st.set_page_config(layout="wide")

def load_css(path):
    with open(path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# CSS-style
load_css("style.css")

# To kolonner
col1, col2, col3 = st.columns([3, 1, 1])  # Giver lidt mere plads til vejrdata

with st.container():  # Indpakker hele layoutet i en container
    with col1:
        st.markdown('<div class="kort-wrapper">', unsafe_allow_html=True)
        st.title("Parkering i Vejle")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="kort-wrapper">', unsafe_allow_html=True)
        st.markdown(
            f"""
            **Temperaturen** lige nu i {vejr['location']} er **{vejr['temperature_c']:.0f} °C**  
            **Regnmængden** i dag er {vejr['precip_mm']:.0f} mm.<br> 
            **Dato**: {today_date}
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="kort-wrapper">', unsafe_allow_html=True)
        st.markdown(
        f"""
        <div style="text-align: center;">
            <img src="{vejr['icon']}" width="60">
        </div>
        """,
        unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


# Indlæs data
df = pd.read_csv("df_matchet.csv", encoding="utf-8")

vigtige_steder = {
    'Vejle Station': (55.7093, 9.5356),
    'Bryggen': (55.7088, 9.5343),
    'Spinderihallerne': (55.7099, 9.5279),
    'Vejle Campus': (55.7090, 9.5378),
    'Vejle Rådhus': (55.7107, 9.5371)
}

# ---- FILTER ----

def load_local_svg(file_path):
    with open(file_path, "r") as file:
        return file.read()

large_logo_svg = load_local_svg("vejlek.svg")

st.sidebar.markdown(large_logo_svg, unsafe_allow_html=True)
st.sidebar.markdown("---")

st.sidebar.header("🔎 Filtrér data")

valgt_sted = st.sidebar.selectbox("Vælg et sted", list(vigtige_steder.keys()))

valgt_sted_coords = vigtige_steder[valgt_sted]

# ---- METRICS ----
df['afstand_til_valgt_sted'] = df.apply(
    lambda row: int(np.ceil(geodesic((row['latitude'], row['longitude']), valgt_sted_coords).meters / 50)) * 50,
    axis=1
)

filtered_df = df[df['afstand_til_valgt_sted'] <= 500]  # Kan justeres

best_parkering = filtered_df.loc[filtered_df['ledige_pladser'].idxmax()]

# ---- KORT ----
def vis_kort(data, valgt_sted_coords, valgt_sted):
    m = folium.Map(location=[data['latitude'].mean(), data['longitude'].mean()], zoom_start=15)
    cluster = MarkerCluster().add_to(m)

    # Tilføj markør for det valgte sted
    folium.Marker(
        location=valgt_sted_coords,
        popup=f"<strong>{valgt_sted}</strong>",
        icon=folium.Icon(color="blue", icon="map-marker")
    ).add_to(m)

    # Tilføj parkeringspladser
    for _, row in data.iterrows():
        popup_html = f"""
        <div style="width: 250px; min-width: 200px; font-size: 14px;">
            <b>{row['navn']}</b><br>
            🟢 Ledige: {row['ledige_pladser']} / {row['antal_pladser']}<br>
            🚗 ÅDT: {row['trafik_ÅDT']} (år: {row['trafik_år']})<br>
            📏 Afstand til trafikpunkt: {row['trafik_afstand_meter']} m<br>
            🧭 Afstand til {valgt_sted}: {row['afstand_til_valgt_sted']} m
        </div>
        """
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=popup_html,
            icon=folium.Icon(color="green" if row['ledige_pladser'] > 10 else "red")
        ).add_to(cluster)

    return m

col1a, col1b, col1c = st.columns(3)

with col1a:
    st.markdown('<div class="kort-wrapper">', unsafe_allow_html=True)
    st.metric("🅿️ Nærmeste parkeringsplads", best_parkering['navn'])

with col1b:
    st.markdown('<div class="kort-wrapper">', unsafe_allow_html=True)
    st.metric("📍 Afstand til valgt sted", f"{best_parkering['afstand_til_valgt_sted']} m")

with col1c:
    st.markdown('<div class="kort-wrapper">', unsafe_allow_html=True)
    st.metric("🟢 Ledige pladser", best_parkering['ledige_pladser'])
    st.markdown('</div>', unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])  

with col1:
    st.markdown('<div class="kort-wrapper">', unsafe_allow_html=True)
    folium_static(vis_kort(filtered_df, valgt_sted_coords, valgt_sted), width=1200, height=400)
    st.markdown('</div>', unsafe_allow_html=True)


# ---- RESTEN AF METRICS ----
with col2:
    st.markdown('<div class="kort-wrapper">', unsafe_allow_html=True)    
    gennemsnit_afstand = filtered_df['afstand_til_valgt_sted'].mean()
    col2.metric("📏 Gennemsnitlig afstand", f"{gennemsnit_afstand:.0f} m")

    max_pladser = filtered_df['antal_pladser'].max()
    col2.metric("🔢 Max antal pladser", max_pladser)

    max_AADT = filtered_df['trafik_ÅDT'].max()
    col2.metric("🚗 Max ÅDT", f"{max_AADT:,}")

    antal_lokationer = len(filtered_df)
    col2.metric("📍 Antal lokationer", antal_lokationer)
    st.markdown('</div>', unsafe_allow_html=True)


st.sidebar.markdown("---")
# Indlæs JSON-fil
with open("event.json", "r", encoding="utf-8") as f:
    events = json.load(f)

def parse_event_date(e):
    return e["dates"]

sorted_events = sorted(events, key=parse_event_date)

with st.sidebar:
    st.subheader("Kommende begivenheder")
    
    for event in sorted_events[:10]:
        with st.expander(event["title"]):  
            st.write(f"📍 **Sted**: {event['venue']} — {event['address']}")
            st.write(f"📅 **Dato**: {event['dates']}")
            st.write(f"💰 **Pris**: {event['price']}")
            if 'description' in event:
                st.write(f"📝 **Beskrivelse**: {event['description']}")