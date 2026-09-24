"""ARHPP Streamlit dashboard — alternative to FastAPI UI.

Run: streamlit run api/streamlit_app.py
"""

import time
from datetime import datetime

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from api.state import STATE

st.set_page_config(page_title="ARHPP", layout="wide")
st.title("ARHPP - Real-Time Dashboard")

placeholder = st.empty()
chart_slot = st.empty()
alert_slot = st.empty()

for _ in range(10000):
    snap = STATE.latest
    if snap:
        with placeholder.container():
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.metric("BHP (psi)", f"{snap.get('bhp', 0):.1f}")
            c2.metric("ECD (ppg)", f"{snap.get('ecd', 0):.3f}")
            c3.metric("ESD (ppg)", f"{snap.get('esd', 0):.3f}")
            c4.metric("PP (ppg)", f"{snap.get('pp', 0):.2f}")
            c5.metric("FG (ppg)", f"{snap.get('fg', 0):.2f}")
            c6.metric("Confidence",
                       f"{snap.get('confidence', 0)*100:.0f}%")

            q1, q2, q3, q4 = st.columns(4)
            q1.metric("Q in (gpm)", f"{snap.get('q_in', 0):.0f}")
            q2.metric("Q out (gpm)", f"{snap.get('q_out', 0):.0f}")
            q3.metric("Q utube (gpm)", f"{snap.get('q_utube', 0):+.2f}")
            q4.metric("Q loss (gpm)", f"{snap.get('q_loss', 0):.2f}")

        hist = STATE.get_history(180)
        if hist:
            df = pd.DataFrame(hist)
            fig = go.Figure()
            if "bhp" in df.columns:
                fig.add_trace(go.Scatter(y=df["bhp"], name="BHP",
                                          line=dict(color="#38bdf8")))
            fig.update_layout(height=320,
                                margin=dict(l=20, r=20, t=20, b=20),
                                paper_bgcolor="#0f172a",
                                plot_bgcolor="#0f172a",
                                font=dict(color="#e2e8f0"))
            chart_slot.plotly_chart(fig, use_container_width=True)

        if snap.get("alerts"):
            alert_slot.error(" | ".join(snap["alerts"]))
        else:
            alert_slot.success("No active alerts")

    time.sleep(1.0)
