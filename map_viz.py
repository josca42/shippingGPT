import folium
import pydeck as pdk
import streamlit as st
from streamlit_folium import st_folium
import pandas as pd
import numpy as np


def create_map(layers: dict, draw=False):
    if draw:
        map_data = create_folium_map(layers)
    else:
        map_data = None
        create_pydeck_map(layers)
    return map_data


def create_folium_map(layers: dict):
    m = folium.Map(location=[0, 0], zoom_start=2, tiles="cartodb positron")
    folium.plugins.Draw(export=True).add_to(m)

    fg = folium.FeatureGroup(name="Ports")
    for _, row in ports.iterrows():
        fg.add_child(
            folium.Marker(
                location=[row.geometry.y, row.geometry.x],
                tooltip=f"{row['name']}, {row['country']}",
                icon=folium.Icon(color="red" if PORT_COL == "POD_id" else "green"),
            )
        )

    map_data = st_folium(m, feature_group_to_add=fg, width=1200, height=600)
    return map_data


def create_pydeck_map(layers: dict):
    view = pdk.ViewState(latitude=0, longitude=0, pitch=0, zoom=2)

    pdk_layers = []
    # if "routes" in layers:
    #     pdk_layers.append(pipes_layer)

    if "POD" in layers:
        POD_layer = pdk_scatter_layer(gdf=layers["POD"], color=[200, 30, 0, 160])
        pdk_layers.append(POD_layer)
    if "POL" in layers:
        POL_layer = pdk_scatter_layer(gdf=layers["POL"], color=[34, 139, 34, 160])
        pdk_layers.append(POL_layer)
    if "routes" in layers:
        routes_layer = pdk.Layer(
            "PathLayer",
            data=layers["routes"],
            pickable=True,
            width_scale=0,
            get_color=[8, 232, 222],
            width_min_pixels=2,
            get_path="path",
            get_width=5,
        )
        pdk_layers.append(routes_layer)

    st.pydeck_chart(
        pdk.Deck(
            layers=pdk_layers,
            initial_view_state=view,
            map_style=None,
            tooltip={"text": "{name}"},
        )
    )


def pdk_scatter_layer(gdf, color):
    return pdk.Layer(
        "ScatterplotLayer",
        data=gdf[["name", "coords"]].copy(),
        stroked=True,
        filled=True,
        pickable=True,
        auto_highlight=True,
        get_position="coords",
        get_fill_color=color,
        get_line_color=[0, 0, 0],
        get_radius=500,
        radius_min_pixels=3,
        radius_max_pixels=20,
    )
