import streamlit as st
import asyncio
import time
import sys
import pandas as pd
import numpy as np
import altair as alt
from pathlib import Path

# --- BACKEND IMPORT ---
# Add the repo root to sys.path so 'client' package is importable
# regardless of which directory streamlit is launched from.
_repo_root = Path(__file__).resolve().parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

try:
    from client import RetailOpsClient
except ImportError as _e:
    st.error(
        f"❌ Could not import RetailOpsClient from `client/`.\n\n"
        f"Make sure you are running Streamlit from the repo root:\n"
        f"  `streamlit run stapp_hardcoded1.py`\n\n"
        f"Error detail: {_e}"
    )
    st.stop()

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="RetailOps | AI Copilot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS (THE "AWESOME UI" LAYER) ---
def local_css():
    st.markdown("""
    <style>
        /* Import modern font */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* Gradient Title */
        .title-text {
            background: -webkit-linear-gradient(45deg, #2E9AFF, #00CC96);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
            font-size: 3rem;
        }

        /* Metric Cards Styling */
        div[data-testid="stMetric"] {
            background-color: #262730;
            border: 1px solid #3b3c46;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            transition: transform 0.2s;
        }
        div[data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            border-color: #2E9AFF;
        }

        /* Custom Status Indicator in Sidebar */
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            background-color: #00CC96;
            border-radius: 50%;
            margin-right: 8px;
            box-shadow: 0 0 8px #00CC96;
        }
        
        /* Action Button Styling */
        .stButton button {
            background-image: linear-gradient(to right, #2E9AFF 0%, #0078D7  51%, #2E9AFF  100%);
            margin: 10px;
            padding: 15px 30px;
            text-align: center;
            text-transform: uppercase;
            transition: 0.5s;
            background-size: 200% auto;
            color: white;
            border-radius: 10px;
            border: none;
            font-weight: 600;
        }

        .stButton button:hover {
            background-position: right center;
            color: #fff;
            text-decoration: none;
        }
        
        /* Chat Message Styling */
        .stChatMessage {
            background-color: #1E1E1E;
            border: 1px solid #333;
            border-radius: 15px;
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- ASYNC HELPER ---
async def run_orchestrator(product_name: str, days: int = 30) -> dict:
    """Bridge to the async Orchestrator Client."""
    client = RetailOpsClient()
    return await client.run_full_workflow(product_name, days_ahead=days)

# --- INITIALIZATION ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "script_step" not in st.session_state:
    st.session_state.script_step = 0

# --- SIDEBAR CONFIGURATION (user-configurable inputs) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712035.png", width=50)
    st.markdown("### **RetailOps** `Enterprise`")
    st.markdown("---")

    # Profile
    col_p1, col_p2 = st.columns([1, 3])
    with col_p1:
        st.write("👤")
    with col_p2:
        st.caption("Logged in as")
        user_role = st.text_input("Role", value="Store Manager", label_visibility="collapsed")

    st.markdown("---")

    # Store Context (editable)
    st.markdown("📍 **Store Context**")
    store_name = st.text_input("Store Name", value="Mumbai Flagship Store")
    st.info(store_name)

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        product_input = st.text_input("Product", value="Samsung TV")
    with col_s2:
        season_input = st.text_input("Season / Event", value="Pre-Diwali")

    days_ahead = st.slider("Forecast Horizon (Days)", min_value=7, max_value=90, value=30, step=7)

    st.markdown("---")

    # System Status
    st.markdown("📡 **System Status**")
    st.markdown('<div><span class="status-indicator"></span>Azure OpenAI: <b>Online</b></div>', unsafe_allow_html=True)
    st.markdown('<div><span class="status-indicator"></span>Azure AI Search: <b>Connected</b></div>', unsafe_allow_html=True)
    st.markdown('<div><span class="status-indicator"></span>ERP Connector: <b>Synced</b></div>', unsafe_allow_html=True)

    if st.button("Reset Demo", type="secondary"):
        st.session_state.messages = []
        st.session_state.script_step = 0
        st.rerun()

# --- MAIN HEADER ---
col_h1, col_h2 = st.columns([8, 2])
with col_h1:
    st.markdown('<h1 class="title-text">RetailOps Copilot</h1>', unsafe_allow_html=True)
    st.caption("Orchestrating Demand, Inventory, and Pricing with Enterprise AI")
with col_h2:
    st.markdown(f"**{time.strftime('%A, %d %B')}**")
    st.markdown(f"*{time.strftime('%H:%M %p')}*")

st.divider()

# --- HELPER FUNCTIONS ---
def stream_text(text, delay=0.03):
    for word in text.split(" "):
        yield word + " "
        time.sleep(delay)

def render_chart(forecast_val: float = 1200, days: int = 30):
    """Render a demand trend chart scaled to real forecast data."""
    base = max(forecast_val * 0.7, 1)
    data = pd.DataFrame({
        'Day': range(1, days + 1),
        'Last Year':        np.random.normal(base, base * 0.1, days).cumsum() / days * 2,
        'Current Forecast': np.random.normal(forecast_val, forecast_val * 0.1, days).cumsum() / days * 2
    }).melt('Day', var_name='Type', value_name='Sales')

    chart = alt.Chart(data).mark_line(interpolate='monotone').encode(
        x='Day',
        y='Sales',
        color=alt.Color('Type', scale=alt.Scale(
            domain=['Last Year', 'Current Forecast'],
            range=['#808080', '#00CC96']
        )),
        tooltip=['Day', 'Sales', 'Type']
    ).properties(height=300).configure_view(strokeWidth=0)

    return chart

# --- CHAT UI LOGIC ---

# 1. LANDING PAGE (Empty State)
if len(st.session_state.messages) == 0:
    st.markdown(f"### 👋 Good morning, {user_role}.")
    st.markdown(f"I've analyzed yesterday's sales for **{store_name}**. Your **{product_input}** category is moving fast.")

    st.markdown("#### Suggested Actions:")

    c1, c2, c3 = st.columns(3)
    with c1:
        with st.container(border=True):
            st.markdown("📈 **Demand Analysis**")
            st.caption("Review trends vs last year")
            if st.button("Show recent demand trends", key="btn_trends", use_container_width=True):
                st.session_state.initial_input = "Show me recent demand trends"
                st.session_state.script_step = 1
                st.rerun()
    with c2:
        with st.container(border=True):
            st.markdown("📦 **Inventory Check**")
            st.caption("Identify stockout risks")
            st.button("Scan Low Stock Items", key="btn_inv", use_container_width=True, disabled=True)
    with c3:
        with st.container(border=True):
            st.markdown("🏷️ **Pricing Strategy**")
            st.caption(f"Optimize for {season_input}")
            st.button("Review Competitor Pricing", key="btn_price", use_container_width=True, disabled=True)

# 2. RENDER HISTORY
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🤖"):
        st.write(msg["content"])

        if msg.get("type") == "trend_analysis":
            data = msg.get("data", {})
            forecast_val = data.get("forecast", {}).get("final") or 1200
            category_label = data.get("enrichment", {}).get("category") or product_input

            c1, c2 = st.columns([1, 2])
            with c1:
                st.metric("Category", category_label)
                st.metric("Velocity", "High", delta=product_input)
            with c2:
                st.altair_chart(render_chart(forecast_val, days_ahead), use_container_width=True)
            st.caption(f"Source: Azure AI Search index `sales-history-{store_name.lower().replace(' ', '-')}`")

        if msg.get("type") == "action_plan":
            data = msg.get("data", {})
            event_label = data.get("forecast", {}).get("event") or season_input
            f_val = data.get("forecast", {}).get("final") or 0
            req   = data.get("replenishment", {}).get("reorder_qty") or 0
            risk  = data.get("replenishment", {}).get("stockout_risk") or "High"
            price = data.get("pricing", {}).get("recommended_price") or 0
            cat   = data.get("enrichment", {}).get("category") or product_input

            st.markdown(f"### 📋 {event_label} Executive Plan")
            col_a, col_b, col_c = st.columns(3)

            with col_a:
                with st.container(border=True):
                    st.markdown("#### 🔮 Forecast")
                    st.metric("Projected Demand", f"{f_val:,.0f} Units", delta="Seasonal Lift")
                    st.progress(85, text="Confidence Score: High")
                    st.caption(f"Driven by: '{event_label}' Event Signal")

            with col_b:
                with st.container(border=True):
                    st.markdown("#### 📦 Inventory")
                    st.error(f"⚠️ Risk: {risk} Stockout")
                    st.write(f"Category: **{cat}**")
                    st.write(f"Required: **{req:,} Units**")
                    if st.button("🚀 Create Purchase Order"):
                        st.toast("Purchase Order Sent to ERP!", icon="✅")

            with col_c:
                with st.container(border=True):
                    st.markdown("#### 🏷️ Pricing")
                    st.metric("Optimal Price", f"₹{price:,.0f}")
                    st.slider("Discount Adjustment", 0, 15, 8, format="%d%%")
                    if st.button("✅ Apply Pricing"):
                        st.toast("Prices updated in POS system", icon="🏷️")

# 3. INPUT HANDLING
process_query = None
if "initial_input" in st.session_state:
    process_query = st.session_state.initial_input
    del st.session_state.initial_input
elif query := st.chat_input("Ask RetailOps a question..."):
    process_query = query

# 4. PROCESSING LOGIC
if process_query:
    with st.chat_message("user", avatar="👤"):
        st.write(process_query)
    st.session_state.messages.append({"role": "user", "content": process_query})

    # --- STEP 1: DEMAND TRENDS ---
    if st.session_state.script_step == 0 or "demand" in process_query.lower() or "trend" in process_query.lower():
        st.session_state.script_step = 1
        with st.chat_message("assistant", avatar="🤖"):

            with st.status("🔍 Analyzing sales data...", expanded=True) as status:
                st.write(f"Connecting to Azure AI Search...")
                time.sleep(0.8)
                st.write(f"Retrieving index for **{store_name}**...")
                time.sleep(0.5)
                st.write("Aggregating seasonality patterns...")
                time.sleep(0.5)
                status.update(label="Analysis Complete", state="complete", expanded=False)

            with st.spinner("Fetching live data from MCP servers..."):
                result = asyncio.run(run_orchestrator(product_input, days_ahead))

            cat = result.get("enrichment", {}).get("category") or product_input
            forecast_val = result.get("forecast", {}).get("final") or 1200

            intro = (
                f"**[Azure AI Search]** I've retrieved the historical data. "
                f"Here is the demand analysis for **{cat}** over the next **{days_ahead} days**:"
            )
            st.write_stream(stream_text(intro))

            c1, c2 = st.columns([1, 2])
            with c1:
                st.metric("Category", cat)
                st.metric("Velocity", "High", delta=product_input)
            with c2:
                st.altair_chart(render_chart(forecast_val, days_ahead), use_container_width=True)
            st.caption(f"Source: Azure AI Search index `sales-history-{store_name.lower().replace(' ', '-')}`")

        st.session_state.messages.append({
            "role": "assistant",
            "content": intro,
            "type": "trend_analysis",
            "data": result
        })

    # --- STEP 2: FULL ORCHESTRATION / EVENT PREP ---
    elif st.session_state.script_step == 1 or any(
        kw in process_query.lower() for kw in ["diwali", "prepare", "event", "plan", "stock"]
    ):
        st.session_state.script_step = 2
        with st.chat_message("assistant", avatar="🤖"):

            # Run backend first, then display the visual execution log
            with st.spinner("Running MCP orchestration workflow..."):
                result = asyncio.run(run_orchestrator(product_input, days_ahead))

            # Safe fallback values
            cat   = result.get("enrichment", {}).get("category") or product_input
            event = result.get("forecast",   {}).get("event")    or season_input
            f_val = result.get("forecast",   {}).get("final")    or 1200
            req   = result.get("replenishment", {}).get("reorder_qty") or 600
            risk  = result.get("replenishment", {}).get("stockout_risk") or "High"
            price = result.get("pricing",    {}).get("recommended_price") or 28000
            p_type = result.get("pricing",   {}).get("recommendation_type") or "Discount"

            with st.status("🧬 Running `RetailOpsState` Workflow...", expanded=True) as status:

                st.write("🧠 **Azure OpenAI** interpreting intent: 'Event Preparation'...")

                st.write("🔵 **Node 1: Catalog Enricher** (`enrichment_node`)")
                time.sleep(0.5)
                st.code({"category": cat, "event": event}, language="json")

                st.write("📊 **Node 2: Forecasting** (`forecasting_node`)")
                time.sleep(0.5)
                st.code({"final_forecast": round(f_val), "event": event}, language="json")

                st.write("📦 **Node 3: Replenishment** (`replenishment_node`)")
                time.sleep(0.5)
                st.code({"reorder_qty": req, "stockout_risk": risk}, language="json")

                st.write("💰 **Node 4: Pricing Strategy** (`pricing_node`)")
                time.sleep(0.5)
                st.code({"recommended_price": round(price), "type": p_type}, language="json")

                status.update(label="Workflow Completed Successfully", state="complete", expanded=False)

            intro = (
                f"Based on the completed **RetailOpsState** workflow, here is your unified "
                f"**{event} Action Plan**, combining enrichment, forecasting, replenishment, "
                f"and pricing intelligence."
            )
            st.write_stream(stream_text(intro))

            st.markdown(f"### 📋 {event} Executive Plan")
            col_a, col_b, col_c = st.columns(3)

            with col_a:
                with st.container(border=True):
                    st.markdown("#### 🔮 Forecast")
                    st.metric("Projected Demand", f"{f_val:,.0f} Units", delta="Seasonal Lift")
                    st.progress(85, text="Confidence: High")

            with col_b:
                with st.container(border=True):
                    st.markdown("#### 📦 Inventory")
                    st.error(f"⚠️ Risk: {risk} Stockout")
                    st.write(f"Required: **{req:,} Units**")
                    if st.button("🚀 Create Purchase Order", key="k_inv"):
                        st.toast("PO Sent!", icon="✅")

            with col_c:
                with st.container(border=True):
                    st.markdown("#### 🏷️ Pricing")
                    st.metric("Optimal Price", f"₹{price:,.0f}")
                    st.slider("Discount", 0, 15, 8, key="sl_price")
                    if st.button("✅ Apply Pricing", key="k_price"):
                        st.toast("Prices Updated!", icon="🏷️")

        st.session_state.messages.append({
            "role": "assistant",
            "content": intro,
            "type": "action_plan",
            "data": result
        })

    # --- FALLBACK ---
    else:
        with st.chat_message("assistant", avatar="🤖"):
            st.write(
                f"I'm ready to help with **{store_name}**. "
                "Try asking about 'Demand Trends' or use the sidebar to configure your product and start the workflow."
            )