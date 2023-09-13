import openai
import os
from jinja2 import Template
from datetime import datetime
import numpy as np
from typing import Union

from dotenv import load_dotenv
import json
import faiss
import numpy as np
import pandas as pd
from data import gdf_ports

load_dotenv()


openai.api_key = os.environ.get("OPENAI_API_KEY")

action = np.load("./data/action.npy")
customers = np.load("./data/customers.npy", allow_pickle=True)
customer_index = faiss.read_index("./data/customer_names_faiss.bin")
ports_index = faiss.read_index("./data/port_names_faiss.bin")
action_index = faiss.read_index("./data/action_faiss.bin")


def extract_metadata_from_cmd(cmd_msg: str, previous_msg: str, metadata: dict):
    sys_msg = [
        dict(
            role="system",
            content=CMD_METADATA_SYS_MSG.render(
                current_date=datetime.now().strftime("%Y-%m-%d")
            ),
        )
    ]
    user_msgs = (
        [
            dict(role="user", content=previous_msg),
            dict(role="assistant", content=json.dumps(metadata, default=str)),
            dict(role="user", content=cmd_msg),
        ]
        if previous_msg
        else [dict(role="user", content=cmd_msg)]
    )

    response_txt = llm(messages=sys_msg + user_msgs, model="gpt-3.5-turbo")
    metadata = json.loads(response_txt)

    if "customer" in metadata:
        metadata["customer"] = [
            match_customer(customer) for customer in metadata["customer"]
        ]
    if "start_dest" in metadata:
        metadata["POL"] = [match_port(port) for port in metadata["start_dest"]]
        del metadata["start_dest"]

    if "end_dest" in metadata:
        metadata["POD"] = [match_port(port) for port in metadata["end_dest"]]
        del metadata["end_dest"]

    metadata["start_date"] = (
        str2date(metadata["start_date"]) if "start_date" in metadata else None
    )
    metadata["end_date"] = (
        str2date(metadata["end_date"]) if "end_date" in metadata else None
    )
    return metadata


def write_update(metadata: dict, st):
    sys_msg = [
        dict(role="system", content=UPDATE_METADATA_SYS_MSG),
    ]

    user_msg = [dict(role="user", content=json.dumps(metadata, default=str))]
    response_txt = llm(
        messages=sys_msg + UPDATE_EXAMPLES + user_msg,
        model="gpt-3.5-turbo",
        temperature=1,
        st=st,
    )
    return response_txt


def write_email(booking_email: str, email_content, st):
    sys_msg = [dict(role="system", content=EMAIL_SYS_MSG)]
    user_msg = [
        dict(
            role="user",
            content=EMAIL_USER_MSG.render(
                booking_email=booking_email, email_content=email_content
            ),
        )
    ]
    response_txt = llm(
        messages=sys_msg + user_msg,
        model="gpt-4",
        temperature=1,
        st=st,
    )
    return response_txt


def llm(
    messages,
    model="gpt-4",  # "gpt-3.5-turbo-0613",
    temperature=0,
    stop=None,
    st=None,
) -> str:
    stream = True if st else False
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=temperature,
        stop=stop,
        stream=stream,
    )

    if stream:
        with st.chat_message("assistant", avatar="👨🏻‍✈️"):
            message_placeholder = st.empty()
            full_response = ""
            for chunk in response:
                full_response += chunk.choices[0].delta.get("content", "")
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)

    else:
        full_response = response.choices[0].message.content

    return full_response


def embed(texts: Union[list[str], str]):
    if isinstance(texts, str):
        texts = [texts]
    texts = [text.replace("\n", " ") for text in texts]

    response = openai.Embedding.create(
        input=texts,
        model="text-embedding-ada-002",
    )
    embeddings = [data.get("embedding") for data in response.data]
    return embeddings


def match_port(port):
    query_embedding = embed([port])
    D, I = ports_index.search(np.array(query_embedding).astype("float32"), 1)
    return gdf_ports.iloc[I[0]]["name"].squeeze()


def match_customer(customer):
    query_embedding = embed([customer])
    D, I = customer_index.search(np.array(query_embedding).astype("float32"), 1)
    return customers[I[0]][0]


def match_action(msg):
    query_embedding = embed([msg])
    D, I = action_index.search(np.array(query_embedding).astype("float32"), 1)
    return action[I[0]][0]


def str2date(date_str):
    if date_str == "":
        return ""
    else:
        try:
            return pd.to_datetime(date_str).date()
        except:
            return ""


###   Prompts   ###
CMD_METADATA_SYS_MSG = Template(
    """You are a metadata extraction agent. You extract relevant metadata from questions and/or commands. You specifically extract start destinations, end destinations, start date, end date and customers from the command. The extracted metadata is used to filter in booking requests.
If a date is extracted write the date in 'yyyy-mm-dd'. The current date is {{ current_date }}.
 
You return the results on the following form:

{"start_dest": [], "end_dest": [], "start_date": "", "end_date": "", "customer": []}

If the command does not mention any start destinations then do not include the "start_dest" in the returned result. The same is true for all the other metadata variables. Hence, if the command does not mention any relevant metadata then return {}."""
)

UPDATE_METADATA_SYS_MSG = """You create a very short update statements of the action being taken in a dashboard showing an overview of shipping booking request from clients.

The updates should be in the form natural language.

the action will be on the form of:

filters: {"start_dest": [], "end_dest": [], "start_date": "", "end_date": "", "customer": []}"""

UPDATE_EXAMPLES = [
    dict(
        role="user",
        content="""{"start_date": "2023-09-11", "end_date": "2023-11-11", "POD": ["Fremantle"]}""",
    ),
    dict(
        role="assistant",
        content="""Showing bookings going to Fremantle with a pickup date within 11-09-2023 to 11-11-2023""",
    ),
]


EMAIL_SYS_MSG = """You are ShippingGPT a customer service agent that responds to clients booking request for getting cargo with one of your ships.

You respond to emails in the same manner of writing as the received booking email. Unless the booking email is rude then respond politely. 
Be concise in your answers.

When writing the response you are provided the following information:

Booking email: "Original booking email"

Email content: A natural language description of the highlevel content of the email. Is the booking confirmed, declined or is more information needed. Could also be a clarification such that the booking can be confirmed if the pickup date is moved to another date."""

EMAIL_USER_MSG = Template(
    """Booking email: "{{ booking_email }}
Email content: {{ email_content }}"""
)
