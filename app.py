
import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import folium
import base64
from dash.dependencies import Input, Output, State
from pyngrok import ngrok
from google.colab import drive

# Mount Drive
drive.mount('/content/drive')

# --- Load Data ---
def load_and_preprocess_data(filepath):
    chunksize = 10000
    all_daily_avgs = []
    for chunk in pd.read_csv(filepath, delimiter=';', chunksize=chunksize, encoding='utf-8', on_bad_lines='skip'):
        chunk.columns = chunk.columns.str.strip()
        if 'AAAAMMJJHH' not in chunk.columns:
            raise ValueError(f"Colonne 'AAAAMMJJHH' introuvable. Colonnes disponibles : {chunk.columns.tolist()}")
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

def load_and_preprocess_fire_data(filepath):
    df = pd.read_csv(filepath, sep=';', engine='python', encoding='utf-8', on_bad_lines='skip')
    df.columns = df.columns.str.strip()
    if 'AAAAMMJJHH' not in df.columns:
        raise ValueError(f"Colonne 'AAAAMMJJHH' introuvable. Colonnes disponibles : {df.columns.tolist()}")
    df['AAAAMMJJHH'] = pd.to_datetime(df['AAAAMMJJHH'], format='%Y%m%d%H', errors='coerce')
    df['Year'] = df['AAAAMMJJHH'].dt.year
    df['Month'] = df['AAAAMMJJHH'].dt.month
    df = df[df['Year'] >= 2010]
    return df

daily_avg = load_and_preprocess_data('/content/drive/My Drive/conditions_meteos_horaire_13_2010_2020.csv')
fire_df = load_and_preprocess_fire_data('/content/drive/My Drive/incendies_bdiff_13.csv')

# --- Dash App Setup ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUX])

# Load logos
logo_path_meteo = '/content/drive/My Drive/logo_meteofrance_dashboard.png'
encoded_logo_meteo = base64.b64encode(open(logo_path_meteo, 'rb').read()).decode('ascii')

logo_path_univ = '/content/drive/My Drive/logo_amu_dashboard.png'
encoded_logo_univ = base64.b64encode(open(logo_path_univ, 'rb').read()).decode('ascii')

# --- Layout ---
app.layout = dbc.Container([
    # Titre
    dbc.Row(
        dbc.Col(
            html.H1("Conditions météorologiques des stations des Bouches du Rhône entre 2010 et 2020",
                    style={'text-align': 'center'}),
            width=12
        ),
        style={'margin-bottom': '10px'}
    ),

    # Alerte info
    dbc.Row(
        dbc.Col(
            dbc.Alert("Sélectionnez une station et une période pour actualiser les données.",
                      color="info", dismissable=True),
            width=12
        )
    ),

    # Bloc identité + carte + filtres
    dbc.Row([
        # Bloc identité
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.Img(src='data:image/png;base64,{}'.format(encoded_logo_univ), style={'width': '180px'}),
                    html.Br(),
                    html.P("Emilien Princic", style={'font-weight': 'bold', 'font-family': 'Times New Roman', 'font-size': '18px'}),
                    html.P("M1 Géomatique et modélisation spatiale", style={'font-family': 'Times New Roman', 'font-size': '18px'}),
                    html.P("amU Aix-en-Provence", style={'font-family': 'Times New Roman', 'font-size': '18px'}),
                    html.P("Mai 2025", style={'font-family': 'Times New Roman', 'font-size': '18px'}),
                    html.P("Données : Data.Gouv - Météo-France", style={'font-family': 'Times New Roman', 'font-size': '18px'}),
                    html.Img(src='data:image/png;base64,{}'.format(encoded_logo_meteo), style={'width': '180px', 'margin-top': '10px'}),
                ]),
                style={'padding': '10px'}
            ),
            width=4
        ),

        # Filtres + carte
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col(
                            dcc.DatePickerRange(
                                id="date-picker-range",
                                start_date=daily_avg['DATE'].min().date(),
                                end_date=daily_avg['DATE'].max().date(),
                            ),
                            width=4,
                        ),
                        dbc.Col(
                            dcc.Dropdown(
                                id="station-dropdown",
                                options=[{"label": station, "value": station} for station in daily_avg['NOM_USUEL'].unique()],
                                value=daily_avg['NOM_USUEL'].iloc[0],
                            ),
                            width=5,
                        ),
                        dbc.Col(
                            dbc.Button("Rafraîchir", id='refresh-button', n_clicks=0, color='secondary'),
                            width=3,
                            style={'display': 'flex', 'align-items': 'center', 'justify-content': 'center'}
                        ),
                    ], style={'margin-bottom': '10px'}),
                    html.Iframe(id='map', style={'border': 'none', 'width': '100%', 'height': '400px'}),
                ])
            ])
        ], width=8),
    ], style={'margin-bottom': '30px'}),

    # KPI Section
    dbc.Row(
        dbc.Col(
            [
                html.H5("Indicateurs clés (période sélectionnée)", style={'text-align': 'center', 'margin-bottom': '20px'}),
                dbc.Row(
                    [
                        dbc.Col([
                            html.H6("Température moyenne (°C)", className='text-center'),
                            html.Div(id='kpi-temp', className='text-center', style={'font-size': '20px', 'font-weight': 'bold'}),
                        ], width=4),
                        dbc.Col([
                            html.H6("Humidité moyenne (%)", className='text-center'),
                            html.Div(id='kpi-humidity', className='text-center', style={'font-size': '20px', 'font-weight': 'bold'}),
                        ], width=4),
                        dbc.Col([
                            html.H6("Précipitations totales (mm)", className='text-center'),
                            html.Div(id='kpi-precip', className='text-center', style={'font-size': '20px', 'font-weight': 'bold'}),
                        ], width=4),
                    ],
                    justify='center'
                )
            ],
            width=12
        ),
        style={'margin-bottom': '30px'}
    ),

    # Graphique météo interactif
    dbc.Row(
        dbc.Col(
            [
                html.Div("Sélectionnez le type de graphique :", style={'text-align': 'center', 'margin-bottom': '10px'}),
                dbc.ButtonGroup(
                    [
                        dbc.Button("Humidité", id='btn-humidity', color='primary', outline=True, n_clicks=0),
                        dbc.Button("Température", id='btn-temperature', color='primary', outline=True, n_clicks=0),
                        dbc.Button("Précipitations", id='btn-precipitation', color='primary', outline=True, n_clicks=0),
                    ],
                    className="d-flex justify-content-center mb-3"
                ),
                dcc.Graph(id='interactive-weather-graph'),
            ],
            width=10,
            className="offset-md-1"
        ),
        style={'margin-bottom': '40px'}
    ),

    # Graphiques incendies
    dbc.Row([
        dbc.Col(dcc.Graph(id="fire-per-year-graph"), width=6),
        dbc.Col(dcc.Graph(id="fire-per-month-graph"), width=6),
    ], style={'margin-bottom': '30px'}),

    # Footer
    html.Footer(
        "© 2025 Emilien Princic – M1 Géomatique AMU | Données : Météo-France, Data.gouv.fr",
        style={'text-align': 'center', 'margin-top': '40px', 'font-size': '13px', 'color': 'gray'}
    )
], fluid=True)

# --- Callbacks ---
@app.callback(
    [
        Output('map', 'srcDoc'),
        Output('interactive-weather-graph', 'figure'),
        Output('kpi-temp', 'children'),
        Output('kpi-humidity', 'children'),
        Output('kpi-precip', 'children'),
    ],
    [
        Input('date-picker-range', 'start_date'),
        Input('date-picker-range', 'end_date'),
        Input('station-dropdown', 'value'),
        Input('refresh-button', 'n_clicks'),
        Input('btn-humidity', 'n_clicks'),
        Input('btn-temperature', 'n_clicks'),
        Input('btn-precipitation', 'n_clicks')
    ]
)
def update_dashboard(start_date, end_date, station_name, n_clicks, n1, n2, n3):
    filtered_df = daily_avg[
        (daily_avg['NOM_USUEL'] == station_name) &
        (daily_avg['DATE'] >= start_date) &
        (daily_avg['DATE'] <= end_date)
    ]

    map_center = [filtered_df['LAT'].mean(), filtered_df['LON'].mean()]
    m = folium.Map(location=map_center, zoom_start=10)
    folium.Marker(
        location=[filtered_df['LAT'].iloc[0], filtered_df['LON'].iloc[0]],
        popup=station_name,
        tooltip=station_name
    ).add_to(m)
    map_html = m.get_root().render()

    # Détermination du bouton actif
    ctx = dash.callback_context
    if not ctx.triggered:
        button_id = 'btn-humidity'
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'btn-temperature':
        fig = px.line(filtered_df, x='DATE', y='T', title='Température', labels={'T': 'Température (°C)'})
        fig.update_traces(line_color='red')
    elif button_id == 'btn-precipitation':
        fig = px.line(filtered_df, x='DATE', y='RR1', title='Précipitations', labels={'RR1': 'Précipitations (mm)'})
        fig.update_traces(line_color='purple')
    else:
        fig = px.line(filtered_df, x='DATE', y='U', title='Humidité', labels={'U': 'Humidité (%)'})
        fig.update_traces(line_color='blue')

    fig.update_layout(autosize=True, margin=dict(l=20, r=20, t=40, b=20))

    avg_temp = round(filtered_df['T'].mean(), 1)
    avg_humidity = round(filtered_df['U'].mean(), 1)
    total_precip = round(filtered_df['RR1'].sum(), 1)

    return map_html, fig, f"{avg_temp} °C", f"{avg_humidity} %", f"{total_precip} mm"

@app.callback(
    Output('fire-per-year-graph', 'figure'),
    Output('fire-per-month-graph', 'figure'),
    Input('refresh-button', 'n_clicks')
)
def update_fire_charts(n_clicks):
    filtered_fire_df = fire_df[fire_df['Year'] >= 2010]

    # Graphique : Incendies par année
    fires_per_year = filtered_fire_df.groupby('Year').size().reset_index(name='Nombre d\'incendies')
    fires_per_year['Moyenne mobile (3 ans)'] = fires_per_year['Nombre d\'incendies'].rolling(window=3, center=True).mean()

    fig_year = px.bar(
        fires_per_year,
        x='Year',
        y='Nombre d\'incendies',
        title="Nombre d’incendies par an (2010–2020)",
        labels={'Year': 'Année', 'Nombre d\'incendies': 'Nombre d\'incendies'},
        color_discrete_sequence=["indianred"]
    )
    fig_year.add_scatter(
        x=fires_per_year['Year'],
        y=fires_per_year['Moyenne mobile (3 ans)'],
        mode='lines',
        name='Moyenne mobile (3 ans)',
        line=dict(color='orange', dash='dash')
    )
    fig_year.update_layout(
        xaxis=dict(dtick=1),
        yaxis_title="Nombre d'incendies",
        legend_title="Légende",
        margin=dict(l=40, r=20, t=60, b=40)
    )

    # Graphique : Incendies par mois
    fires_per_month = filtered_fire_df.groupby('Month').size().reset_index(name='Nombre d\'incendies')
    month_names = ['Janv', 'Févr', 'Mars', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sept', 'Oct', 'Nov', 'Déc']
    fires_per_month['Mois'] = fires_per_month['Month'].apply(lambda x: month_names[x - 1])

    fig_month = px.bar(
        fires_per_month,
        x='Mois',
        y='Nombre d\'incendies',
        title="Répartition moyenne des incendies par mois (2010–2020)",
        labels={'Mois': 'Mois', 'Nombre d\'incendies': 'Nombre moyen d\'incendies'},
        color_discrete_sequence=["darkred"]
    )
    fig_month.update_layout(
        yaxis_title="Nombre moyen d'incendies",
        xaxis_title="Mois",
        legend_title="",
        margin=dict(l=40, r=20, t=60, b=40)
    )

    return fig_year, fig_month