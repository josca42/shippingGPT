import streamlit as st
import pandas as pd
from table import create_aggrid
from map_viz import create_map
import geopandas as gpd
from gpt import extract_metadata_from_cmd, match_action, write_update, write_email
from data import df_requests, gdf_ports
import searoute as sr


def filter_metadata(df_requests, filters):
    if filters:
        df = df_requests.copy()
        start_date = filters["start_date"] if "start_date" in filters else None
        end_date = filters["end_date"] if "end_date" in filters else None
        if start_date or end_date:
            true_bool = pd.Series([True] * len(df))
            start_filter = (
                (df["start_date"] >= pd.Timestamp(start_date))
                if start_date
                else true_bool
            )
            end_filter = (
                (df["end_date"] <= pd.Timestamp(end_date)) if end_date else true_bool
            )
            df = df[start_filter & end_filter]
        for col, values in filters.items():
            if col not in ["start_date", "end_date"]:
                df = df[df[col].isin(values)]
        return df.copy()
    else:
        return df_requests


def filter_coords():
    # Create table with the orders in the rectangle drawn
    if map_data["all_drawings"]:
        coords = map_data["all_drawings"][0]["geometry"]["coordinates"][0]
        x = [c[0] for c in coords]
        y = [c[1] for c in coords]
        gdf_s = gdf_ports.cx[min(x) : max(x), min(y) : max(y)]
        df_s = df_requests[df_requests["POD_id"].isin(gdf_s.index)]

        table = create_aggrid(df_s)


st.set_page_config(layout="wide")
st.markdown(
    """
        <style>
               .block-container {
                    padding-top: 1rem;
                    padding-bottom: 0rem;
                    padding-left: 5rem;
                    padding-right: 5rem;
                }
        </style>
        """,
    unsafe_allow_html=True,
)


# Add initial state variables
if "metadata" not in st.session_state:
    st.session_state.metadata = {}
if "previous_prompt" not in st.session_state:
    st.session_state.previous_prompt = None
if "messages" not in st.session_state:
    st.session_state.messages = [
        dict(role="assistant", content="Let's get those bookings sorted!")
    ]


# Add chat input in main app
if prompt := st.chat_input("Your wish is my command"):
    action = match_action(prompt)

    if action == 0:
        metadata = extract_metadata_from_cmd(
            prompt, st.session_state.previous_prompt, st.session_state.metadata
        )
        st.session_state.metadata = metadata
        st.session_state.previous_prompt = prompt
        email = False
    elif action == 1:
        email = True
        metadata = st.session_state.metadata
    else:
        pass

else:
    metadata = st.session_state.metadata
    # Add chat messages in sidebar


df = filter_metadata(df_requests, filters=metadata)
table_data = create_aggrid(df_requests=df)

if table_data.selected_rows:
    df = df.iloc[
        [
            row["_selectedRowNodeInfo"]["nodeRowIndex"]
            for row in table_data.selected_rows
        ]
    ]


col1, col2 = st.columns([0.85, 0.15])

with col2:
    st.caption("Map settings")
    layers = []
    POD = st.checkbox(
        "POD",
        value=True,
        key="POD_id",
    )
    POL = st.checkbox(
        "POL",
        value=False,
        key="POL_id",
    )
    routes = st.checkbox(
        "Routes",
        value=False,
        key="routes",
    )
    draw = st.toggle("Draw", value=False)

with col1:
    layers = {}
    if POD:
        layers["POD"] = POD
    if POL:
        layers["POL"] = POL

    for col, _ in layers.items():
        ports = gdf_ports.loc[df[f"{col}_id"].unique()].copy()
        layers[col] = ports

    if routes:
        routes = []
        for i, row in df.iterrows():
            orig = gdf_ports.loc[row["POL_id"], "coords"]
            dest = gdf_ports.loc[row["POD_id"], "coords"]
            route = sr.searoute(orig, dest)
            routes.append(
                dict(
                    orig=row["POL"],
                    dest=row["POD"],
                    path=route["geometry"]["coordinates"],
                )
            )

        routes = pd.DataFrame(routes)
        layers["routes"] = routes

    map_data = create_map(layers=layers, draw=draw)


with st.sidebar:
    msgs = []
    if prompt:
        if email:
            for email in df["email"]:
                response_txt = write_email(
                    booking_email=email, email_content=prompt, st=st
                )
                msgs.append(dict(role="assistant", content=response_txt))
        else:
            response_txt = write_update(metadata=metadata, st=st)
            msgs.append(dict({"role": "assistant", "content": response_txt}))

    for message in reversed(st.session_state.messages):
        with st.chat_message("assistant", avatar="👨🏻‍✈️"):
            st.markdown(message["content"])

    if msgs:
        st.session_state.messages.extend(msgs)
