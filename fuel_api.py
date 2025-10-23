import requests
import pandas as pd 
from uuid import uuid4
from datetime import datetime
import streamlit as st
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="NSW Fuel Prices", layout="wide")
st_autorefresh(interval=600_000, key="fuel_refresh")

url = "https://api.onegov.nsw.gov.au/oauth/client_credential/accesstoken"

# Use the correct grant type
querystring = {"grant_type": "client_credentials"}

headers = {
    'content-type': "application/json",
    'authorization': "Basic Qk93VzYwR3FwT29Qa3VxR0RyTTY5WWV0b1BHSnVENkY6Z0F4c1g4dEI4ODdhU0VaRw=="
}
client_id = 'BOwW60GqpOoPkuqGDrM69YetoPGJuD6F'

# Use POST instead of GET
response = requests.request("GET", url, headers=headers, params=querystring)

token_data = response.json()

df_token = pd.DataFrame([token_data])

token = token_data['access_token']

fuel_url = "https://api.onegov.nsw.gov.au/FuelPriceCheck/v1/fuel/prices"

headers = {
    "Authorization": f"Bearer {token}",
    "apikey": client_id,
    "content-type": "application/json",
    "transactionid": str(uuid4()),
    "requesttimestamp": datetime.utcnow().isoformat() + "Z"
}

response = requests.request("GET", fuel_url, headers= headers)

# Headers
headers = {
    "content-type": "application/json",
    "authorization": f"Bearer {token}",  # your OAuth token
    "apikey": client_id,
    "transactionid": str(uuid4()),
    "requesttimestamp": datetime.utcnow().isoformat() + "Z"
}

# Payload to get all fuel types
payload = {
    "fueltype": "",      # empty = all fuel types
    "brand": [],         # all brands
    "namedlocation": "", # all locations
    "referencepoint": {"latitude": "", "longitude": ""},
    "sortby": "",
    "sortascending": ""
}

response = requests.request("GET", "https://api.onegov.nsw.gov.au/FuelPriceCheck/v1/fuel/prices",
                         headers=headers, json=payload)
data = response.json()

df_stations = pd.DataFrame(data['stations'])
df_prices = pd.DataFrame(data['prices'])

df_stations['stationid'] = df_stations['stationid'].str.split('-').str[0]

df_merged = pd.merge(
    df_stations,
    df_prices,
    left_on = 'stationid',
    right_on = 'stationcode',
    how = 'left'
)

df_merged.dropna()
df_merged.drop(['brandid', 'stationcode'], axis = 1)

df_merged['lastupdated'] = pd.to_datetime(df_merged['lastupdated'], errors='coerce')

df_merged['lastupdateddate'] = df_merged['lastupdated'].dt.date
df_merged['lastupdatedtime'] = df_merged['lastupdated'].dt.time

df_merged.drop('lastupdated', axis= 1)

df_merged['stationname'] = df_merged['name'].str.split('Speedway').str[-1]
df_merged.drop('name', axis= 1)

#'location' is a dict with keys 'latitude' and 'longitude'
df_merged['latitude'] = df_merged['location'].apply(lambda x: x['latitude'] if isinstance(x, dict) else None)
df_merged['longitude'] = df_merged['location'].apply(lambda x: x['longitude'] if isinstance(x, dict) else None)

# Combined DataFrame

combined_latest_per_station = df_merged.loc[df_merged.groupby(['brand', 'stationname','fueltype'])
['lastupdated'].idxmax()]

combined_latest_prices = combined_latest_per_station.pivot_table(
    index = ['brand', 'stationname', 'latitude', 'longitude', 'lastupdated'],
    columns = 'fueltype',
    values = 'price'
).reset_index()

combined_latest_prices = combined_latest_prices.fillna(0)

# --- Data preparation ---
# Ensure lastupdated_str exists for hover
combined_latest_prices['lastupdated_str'] = combined_latest_prices['lastupdated'].dt.strftime('%Y-%m-%d %H:%M:%S')

st.title("NSW Latest Fuel Prices ⛽")

# --- Fuel type selection ---
fuel_type = st.selectbox(
    "Select Fuel Type",
    ['U91', 'DL', 'E10', 'LPG', 'P95', 'P98', 'PDL'],
    index=0
)

# --- Build hover data dict dynamically ---
hover_data_dict = {
    fuel_type: True,
    'lastupdated_str': True,
    'latitude': False,
    'longitude': False,
    'brand': False
}

# --- Plot Map ---
fig = px.scatter_mapbox(
    combined_latest_prices,
    lat='latitude',
    lon='longitude',
    color='brand',            # color by brand
    size=fuel_type,           # marker size by selected fuel
    hover_name='stationname',
    hover_data=hover_data_dict,
    color_discrete_sequence=px.colors.qualitative.D3,
    size_max=10,
    zoom=11
)

fig.update_layout(
    mapbox_style="carto-positron",  # dark map
    mapbox_center=dict(lat=-33.8688, lon=151.2093),
    width=1200,
    height=1200,
    title=f'NSW Latest Fuel Prices ({fuel_type})',
    title_font=dict(color='white')    # white title for dark background
)

# --- Display Plotly map in Streamlit ---
st.plotly_chart(fig, use_container_width=True)
