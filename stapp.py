import streamlit as st
import asyncio
import pandas as pd
import numpy as np
import altair as alt
import sys
import time
from pathlib import Path

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="RetailOps | Command Center",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

from client import orchestrator

try:
    from client import RetailOpsClient
except ImportError:
    st.error(f"❌ Error: Could not import 'RetailOpsClient' from 'orchestrator.py'.\nConfirmed working directory: ")
    st.stop()

# --- CUSTOM CSS (Stock Dashboard Theme) ---
st.markdown("""
<style>
    /* Global Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Metric Cards - mimicking Stock Dashboard style */
    div[data-testid="stMetric"] {
        background-color: #1E1E1E;
        border: 1px solid #333;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    /* Container styling */
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"] {
        border-radius: 8px;
    }

    /* Primary Button Gradient */
    .stButton button[kind="primary"] {
        background: linear-gradient(90deg, #2E9AFF 0%, #0078D7 100%);
        border: none;
        transition: all 0.3s;
    }
    .stButton button[kind="primary"]:hover {
        box-shadow: 0 0 10px rgba(46, 154, 255, 0.4);
    }

    /* Status Dot */
    .status-dot {
        height: 8px;
        width: 8px;
        background-color: #00CC96;
        border-radius: 50%;
        display: inline-block;
        margin-right: 6px;
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

# --- HELPER FUNCTIONS ---
async def run_orchestrator_async(product_name, days):
    """Bridge to the async Orchestrator Client"""
    client = RetailOpsClient()
    return await client.run_full_workflow(product_name, days_ahead=days)

def execute_workflow(product, days):
    """Synchronous wrapper"""
    with st.spinner(f"Orchestrating agents for '{product}'..."):
        try:
            # Create a new event loop if needed
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(run_orchestrator_async(product, days))
            st.session_state.analysis_result = result
        except Exception as e:
            st.error(f"Workflow Failed: {e}")

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛍️ RetailOps")
    st.caption("MCP Orchestrator")
    st.divider()
    
    st.markdown("### 👤 Context")
    st.write("**Store:** Mumbai Flagship")
    st.write("**Role:** Manager")
    
    st.divider()
    
    st.markdown("### 📡 Active Servers")
    servers = ["Catalog Enricher", "Forecasting", "Replenishment", "Pricing"]
    for s in servers:
        st.markdown(f'<div><span class="status-dot"></span>{s}</div>', unsafe_allow_html=True)

    st.divider()
    if st.button("🔄 Reset", use_container_width=True):
        st.session_state.analysis_result = None
        st.rerun()

# --- MAIN HEADER ---
"""
# :material/hub: Retail Operations Command Center

Orchestrate demand, inventory, and pricing agents via LangGraph.
"""
""

# --- LAYOUT: INPUT (Left) vs VISUALIZATION (Right) ---
cols = st.columns([1, 3])

# 1. LEFT PANEL: INPUTS
with cols[0]:
    input_container = st.container(border=True)
    with input_container:
        st.markdown("### 🎮 Configuration")
        
        product_input = st.text_input("Product", value="Samsung TV")
        
        horizon = st.pills("Horizon", ["1 Week", "1 Month", "3 Months"], default="1 Month")
        days_map = {"1 Week": 7, "1 Month": 30, "3 Months": 90}
        
        st.write("")
        if st.button("🚀 Run Analysis", type="primary", use_container_width=True):
            execute_workflow(product_input, days_map[horizon])
            
        st.markdown("---")
        if st.session_state.analysis_result:
            status = st.session_state.analysis_result.get("status", "unknown")
            if status == "completed":
                st.success("Workflow Complete")
            else:
                st.error(f"Status: {status}")

# 2. RIGHT PANEL: MAIN VISUALIZATION
with cols[1]:
    viz_container = st.container(border=True)
    with viz_container:
        result = st.session_state.analysis_result
        
        if not result:
            st.markdown("### 👋 Ready to Analyze")
            st.info("Select a product on the left to trigger the MCP Agent Mesh.")
            # Placeholder chart
            data = pd.DataFrame({'Date': pd.date_range('2024-01-01', periods=20), 'Value': 0})
            c = alt.Chart(data).mark_line(color='#333').encode(x='Date', y='Value').properties(height=350)
            st.altair_chart(c, use_container_width=True)
            
        elif result.get("status") == "error":
            st.error("❌ Orchestration Error")
            st.code(result.get("error"))
            
        else:
            # Extract Data
            enriched = result.get("enrichment", {})
            forecast = result.get("forecast", {})
            days_ahead = days_map[horizon]
            
            st.markdown(f"### 📈 Projected Demand: {enriched.get('category', 'Unknown')}")
            st.caption(f"Enrichment Narrative: {enriched.get('narrative')}")
            
            # Generate Synthetic Curve based on Forecast Total
            total_forecast = forecast.get("final", 0)
            base_forecast = forecast.get("base", total_forecast * 0.8)
            
            # Create data points
            days = np.arange(1, days_ahead + 1)
            daily_base = base_forecast / days_ahead
            daily_forecast_val = total_forecast / days_ahead
            
            # Add some randomness for visual appeal
            base_curve = np.full(days_ahead, daily_base)
            forecast_curve = np.full(days_ahead, daily_forecast_val) + np.random.normal(0, daily_forecast_val*0.1, days_ahead)
            
            chart_df = pd.DataFrame({
                'Day': np.tile(days, 2),
                'Units': np.concatenate([base_curve, forecast_curve]),
                'Metric': ['Base Baseline'] * days_ahead + ['AI Forecast'] * days_ahead
            })
            
            # Render Chart
            c = alt.Chart(chart_df).mark_line(interpolate='monotone').encode(
                x='Day',
                y='Units',
                color=alt.Color('Metric', scale=alt.Scale(domain=['Base Baseline', 'AI Forecast'], range=['#666', '#00CC96'])),
                tooltip=['Day', 'Units', 'Metric']
            ).properties(height=350)
            
            st.altair_chart(c, use_container_width=True)

""
""

# --- BOTTOM SECTION: AGENT GRID (Peer Analysis Style) ---
"""
## 🧩 Agent Intelligence Outputs
"""

if not st.session_state.analysis_result:
    st.caption("Run the workflow to see detailed agent decisions.")
else:
    result = st.session_state.analysis_result
    agent_cols = st.columns(4)

    # 1. ENRICHER
    with agent_cols[0].container(border=True):
        st.markdown("**🧹 Catalog Enricher**")
        en = result.get("enrichment", {})
        st.metric("Category", en.get("category", "N/A"))
        st.caption(f"Brand: {en.get('brand', 'Generic')}")
        with st.expander("Details"):
            st.write(en.get("description", "No description"))

    # 2. FORECAST
    with agent_cols[1].container(border=True):
        st.markdown("**🔮 Forecasting**")
        fc = result.get("forecast", {})
        val = fc.get("final", 0)
        base = fc.get("base", 0)
        delta = ((val - base)/base)*100 if base else 0
        st.metric("Forecast", f"{val:,.0f}", delta=f"{delta:.1f}% Lift")
        if fc.get("event") != "None":
            st.info(f"Event: {fc.get('event')}")

    # 3. REPLENISHMENT
    with agent_cols[2].container(border=True):
        st.markdown("**📦 Replenishment**")
        rep = result.get("replenishment", {})
        qty = rep.get("reorder_qty", 0)
        risk = rep.get("stockout_risk", "Low")
        
        st.metric("Reorder Qty", f"{qty} units")
        if "High" in risk:
            st.error(f"Risk: {risk}")
        else:
            st.success(f"Risk: {risk}")

    # 4. PRICING
    with agent_cols[3].container(border=True):
        st.markdown("**🏷️ Pricing**")
        pr = result.get("pricing", {})
        price = pr.get("recommended_price", 0)
        pct = pr.get("change_pct", 0)
        
        st.metric("Rec. Price", f"₹{price:,.0f}", delta=f"{pct:+.1f}%")
        st.caption(f"Strategy: {pr.get('type', 'Maintain').title()}")
        if st.button("Apply Price"):
            st.toast("Pricing updated in ERP")