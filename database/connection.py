import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_URL, DATA_DIR


@st.cache_resource
def get_engine():
    os.makedirs(DATA_DIR, exist_ok=True)
    engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine


def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()
