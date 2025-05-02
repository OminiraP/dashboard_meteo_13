# DASHBOARD POUR RAILWAY (lecture depuis URL publique Google Drive)

import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import folium
import base64
from dash.dependencies import Input, Output, State
import os

# --- Load Data ---
def load_and_preprocess_data(url):
    chunksize = 10000
    all_daily_avgs = []
    for chunk in pd.read_csv(url, delimiter=';', chunksize=chunksize, on_bad_lines='skip'):
        chunk['AAAAMMJJHH'] = pd.to_datetime(chunk['AAAAMMJJHH'], format='%Y%m%d%H', errors='coerce')
        chunk.rename(columns={'AAAAMMJJHH': 'DATE'}, inplace=True)
        chunk['YEAR'] = chunk['DATE'].dt.year
        chunk['MONTH'] = chunk['DATE'].dt.month
        chunk['DAY'] = chunk['DATE'].dt.day
        daily_avg_chunk = chunk.groupby(['NUM_POSTE', 'NOM_USUEL', 'LAT', 'LON', 'ALTI', 'YEAR', 'MONTH', 'DAY'])[['U', 'T', 'RR1']].mean().reset_index()
        all_daily_avgs.append(daily_avg_chunk)
    daily_avg = pd.concat(all_daily_avgs, ignore_index=True)
    daily_avg['DATE'] = pd.to_datetime(daily_avg[['YEAR', 'MONTH', 'DAY']].astype(str).agg('-'.join, axis=1))
    return daily_avg

# ✅ Lecture depuis Google Drive (climat)
daily_avg = load_and_preprocess_data("https://drive.google.com/uc?export=download&id=1N8dl2e1HM3FF429QjH9HbJ2RmKqQCxNE")

def load_and_preprocess_fire_data(url):
    df = pd.read_csv(url, sep=';', engine='python', on_bad_lines='skip')
    df['AAAAMMJJHH'] = pd.to_datetime(df['AAAAMMJJHH'], format='%Y%m%d%H', errors='coerce')
    df['Year'] = df['AAAAMMJJHH'].dt.year
    df['Month'] = df['AAAAMMJJHH'].dt.month
    df = df[df['Year'] >= 2010]
    return df

# ✅ Lecture depuis Google Drive (feux)
fire_df = load_and_preprocess_fire_data("https://drive.google.com/uc?export=download&id=1WyzURgAHqX8YNLL15N5NkeGMNjhUXqbc")

# --- Dash App Setup ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUX])
server = app.server

# Load logos
with open("logo_meteofrance_dashboard.png", "rb") as image_file:
    encoded_logo_meteo = base64.b64encode(image_file.read()).decode('ascii')
with open("logo_amu_dashboard.png", "rb") as image_file:
    encoded_logo_univ = base64.b64encode(image_file.read()).decode('ascii')

# --- Layout ---
# (le layout complet est déjà intégré dans le canevas ci-dessus)

if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))
