"""
RetailOps Copilot — MCP-Powered Retail Intelligence
Orchestrates Demand, Inventory, and Pricing via the RetailOps MCP server mesh.
"""

import os
import json
import time
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ─── PAGE CONFIG ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RetailOps | AI Copilot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #0E1117; color: #FAFAFA; }
.title-text {
    background: -webkit-linear-gradient(45deg, #2E9AFF, #00CC96);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    font-weight: 800; font-size: 3rem; letter-spacing: -1px;
}
div[data-testid="stMetric"] {
    background-color: #1E1E1E; border: 1px solid #333; padding: 20px;
    border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); transition: all 0.3s ease;
}
div[data-testid="stMetric"]:hover {
    transform: translateY(-5px); border-color: #2E9AFF;
    box-shadow: 0 10px 20px rgba(46,154,255,0.2);
}
.status-indicator {
    display: inline-block; width: 10px; height: 10px;
    background-color: #00CC96; border-radius: 50%;
    margin-right: 8px; box-shadow: 0 0 8px #00CC96;
}
.stButton button {
    background: linear-gradient(90deg, #2E9AFF 0%, #0078D7 100%);
    border: none; padding: 0.6rem 1.2rem; color: white;
    border-radius: 10px; font-weight: 600; transition: all 0.3s;
    text-transform: uppercase; letter-spacing: 0.5px; width: 100%; margin-top: 10px;
}
.stButton button:hover { box-shadow: 0 0 15px rgba(46,154,255,0.5); transform: scale(1.02); }
.stButton button:disabled { background: #333; color: #666; cursor: not-allowed; box-shadow: none; }
.stChatMessage { background-color: #161920; border: 1px solid #2B2D31; border-radius: 12px; padding: 1rem; margin-bottom: 1rem; }
/* API Key Gate */
.key-gate-box {
    background: linear-gradient(135deg, #161920 0%, #1a1f2e 100%);
    border: 1px solid #2E9AFF44;
    border-radius: 20px;
    padding: 3rem 2.5rem;
    max-width: 560px;
    margin: 4rem auto;
    box-shadow: 0 0 60px rgba(46,154,255,0.12);
}
.gate-logo { font-size: 3rem; text-align: center; margin-bottom: 0.5rem; }
.gate-title {
    background: -webkit-linear-gradient(45deg, #2E9AFF, #00CC96);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    font-weight: 800; font-size: 1.8rem; text-align: center; margin-bottom: 0.2rem;
}
.gate-subtitle { color: #888; text-align: center; font-size: 0.9rem; margin-bottom: 2rem; }
.or-links { display: flex; gap: 12px; justify-content: center; margin-top: 0.6rem; flex-wrap: wrap; }
.or-link {
    display: inline-flex; align-items: center; gap: 6px;
    background: #1E2330; border: 1px solid #2E9AFF55;
    color: #2E9AFF !important; border-radius: 8px;
    padding: 6px 14px; font-size: 0.82rem; font-weight: 600;
    text-decoration: none; transition: all 0.2s;
}
.or-link:hover { background: #2E9AFF22; border-color: #2E9AFF; box-shadow: 0 0 12px rgba(46,154,255,0.3); }
</style>
""", unsafe_allow_html=True)

# ─── LLM CLIENT (keyed by session API key, not cached globally) ──────────────
def get_llm_client(api_key: str) -> OpenAI:
    return OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={"HTTP-Referer": "http://localhost", "X-Title": "RetailOps Copilot"}
    )

LLM_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/owl-alpha")

# ─── FEW-SHOT SIMULATION PROMPT ──────────────────────────────────────────────
SYSTEM_PROMPT = """You are a RetailOps MCP orchestration engine. Given a product, store context, season/event, and forecast horizon, you simulate the output of 4 MCP server nodes:
1. catalog-enricher  → category, brand, segment, event detection
2. forecasting       → base_forecast, seasonal_multiplier, final_forecast, event signal, narrative
3. replenishment     → current_stock, reorder_qty, reorder_point, lead_days, timing, stockout_risk, narrative
4. pricing-strategy  → current_price, recommended_price, change_pct, type, competitor_price, elasticity, narrative

RULES:
- All numbers must be realistic for Indian retail (prices in INR ₹, volumes in units)
- seasonal_multiplier between 1.0-2.5 based on event proximity
- stockout_risk: "Low", "Medium", or "High"
- timing: "immediate", "soon", or "watch"
- type: "Discount", "Premium", or "Hold"
- change_pct: realistic % change (-20 to +15)
- Return ONLY a valid JSON object — no markdown, no explanation.

FEW-SHOT EXAMPLE 1:
Input: product=Samsung TV, store=Mumbai Flagship Store, season=Pre-Diwali, days=30
Output:
{
  "enrichment": {"category": "Electronics", "brand": "Samsung", "segment": "Large Appliances", "event": "Diwali"},
  "forecast": {"base": 820, "seasonal_multiplier": 1.55, "final": 1271, "event": "Diwali", "narrative": "Diwali surge driving 55% uplift. Samsung TVs historically peak in Oct-Nov. Strong consumer spending expected."},
  "replenishment": {"current_stock": 210, "reorder_qty": 650, "reorder_point": 300, "lead_days": 7, "timing": "immediate", "stockout_risk": "High", "narrative": "Current stock will last ~5 days at forecasted demand. Immediate replenishment critical to avoid Diwali stockout."},
  "pricing": {"current_price": 52000, "recommended_price": 47999, "change_pct": -7.7, "type": "Discount", "competitor_price": 49500, "elasticity": -1.4, "narrative": "Competitive 8% discount recommended to capture Diwali demand and undercut Croma/Reliance Digital pricing."}
}

FEW-SHOT EXAMPLE 2:
Input: product=Ariel 2kg Detergent, store=Delhi NCR Store, season=Regular, days=14
Output:
{
  "enrichment": {"category": "FMCG", "brand": "Ariel", "segment": "Laundry", "event": "None"},
  "forecast": {"base": 340, "seasonal_multiplier": 1.02, "final": 347, "event": "None", "narrative": "Steady demand with no seasonal uplift. Slight uptick from weekend restocking cycles."},
  "replenishment": {"current_stock": 45, "reorder_qty": 180, "reorder_point": 80, "lead_days": 2, "timing": "soon", "stockout_risk": "Medium", "narrative": "Stock will deplete in ~1.8 days. Recommend placing order within 24 hours given 2-day lead time."},
  "pricing": {"current_price": 289, "recommended_price": 279, "change_pct": -3.5, "type": "Discount", "competitor_price": 275, "elasticity": -2.1, "narrative": "Minor price reduction to match D-Mart and BigBasket pricing. High elasticity product — price sensitivity is strong."}
}

FEW-SHOT EXAMPLE 3:
Input: product=Nike Running Shoes, store=Bangalore Forum Mall, season=End of Season Sale, days=21
Output:
{
  "enrichment": {"category": "Fashion", "brand": "Nike", "segment": "Footwear", "event": "End of Season Sale"},
  "forecast": {"base": 95, "seasonal_multiplier": 1.8, "final": 171, "event": "End of Season Sale", "narrative": "EoSS creates 80% demand surge for branded footwear. Nike running category leads clearance volumes."},
  "replenishment": {"current_stock": 60, "reorder_qty": 0, "reorder_point": 20, "lead_days": 5, "timing": "watch", "stockout_risk": "Low", "narrative": "EoSS — do not replenish. Clear existing stock at discounted prices. No reorder recommended."},
  "pricing": {"current_price": 8995, "recommended_price": 6299, "change_pct": -30.0, "type": "Discount", "competitor_price": 6499, "elasticity": -1.9, "narrative": "30% markdown triggers clearance velocity. Slight undercut of Myntra EoSS pricing to drive footfall."}
}

Now simulate the output for the given input. Return ONLY the JSON object."""


def simulate_mcp_pipeline(product: str, store: str, season: str, days: int) -> dict:
    """Call OpenRouter (using session API key) to simulate the 4-node MCP pipeline."""
    client   = get_llm_client(st.session_state.openrouter_api_key)
    user_msg = f"product={product}, store={store}, season={season}, days={days}"

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg}
            ],
            max_tokens=1000,
            temperature=0.4,
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "LLM returned invalid JSON — try again.", "raw": raw}
    except Exception as e:
        return {"error": str(e)}


# ─── HELPERS ──────────────────────────────────────────────────────────────────
def stream_text(text, delay=0.02):
    for word in text.split(" "):
        yield word + " "
        time.sleep(delay)


def render_chart(forecast_val: float = 1200, days: int = 30):
    base = max(forecast_val * 0.7, 1)
    data = pd.DataFrame({
        "Day": range(1, days + 1),
        "Last Year":        np.random.normal(base, base * 0.1, days).cumsum() / days * 2,
        "Current Forecast": np.random.normal(forecast_val, forecast_val * 0.1, days).cumsum() / days * 2,
    }).melt("Day", var_name="Type", value_name="Sales")

    chart = (
        alt.Chart(data)
        .mark_line(interpolate="monotone")
        .encode(
            x="Day",
            y="Sales",
            color=alt.Color("Type", scale=alt.Scale(
                domain=["Last Year", "Current Forecast"],
                range=["#808080", "#00CC96"]
            )),
            tooltip=["Day", "Sales", "Type"],
        )
        .properties(height=250)
        .configure_view(strokeWidth=0)
        .configure_axis(grid=False)
        .interactive()
    )
    return chart


# ─── SESSION STATE ────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "script_step" not in st.session_state:
    st.session_state.script_step = 0
if "openrouter_api_key" not in st.session_state:
    # Pre-fill from .env if available (optional convenience for local dev)
    st.session_state.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")

# ─── API KEY GATE ─────────────────────────────────────────────────────────────
if not st.session_state.openrouter_api_key:
    # Centre the gate card using columns
    _, col_mid, _ = st.columns([1, 2, 1])
    with col_mid:
        st.markdown('<div class="key-gate-box">', unsafe_allow_html=True)

        st.markdown('<div class="gate-logo">🤖</div>', unsafe_allow_html=True)
        st.markdown('<div class="gate-title">RetailOps Copilot</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="gate-subtitle">Enterprise AI · Demand · Inventory · Pricing</div>',
            unsafe_allow_html=True,
        )
        st.markdown("---")
        st.markdown("#### 🔑 Enter your RetailOps API Key")
        st.caption(
            "Your key is stored only in this browser session and is used to authenticate "
            "with the RetailOps MCP orchestration backend."
        )

        key_input = st.text_input(
            "API Key",
            type="password",
            placeholder="sk-or-v1-...",
            label_visibility="collapsed",
            key="key_input_field",
        )

        # Quick-access links
        st.markdown(
            """
            <div class="or-links">
              <a class="or-link" href="https://openrouter.ai/sign-in" target="_blank">
                🔐 Sign in to OpenRouter
              </a>
              <a class="or-link" href="https://openrouter.ai/keys" target="_blank">
                ⚡ Generate API Key
              </a>
              <a class="or-link" href="https://openrouter.ai/models" target="_blank">
                🧠 Browse Models
              </a>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("🚀 Launch RetailOps Copilot", use_container_width=True):
            raw_key = key_input.strip()
            if not raw_key:
                st.error("Please paste your OpenRouter API key before launching.")
            elif not raw_key.startswith("sk-or-"):
                st.warning("That doesn't look like an OpenRouter key (should start with `sk-or-`). Double-check and try again.")
            else:
                st.session_state.openrouter_api_key = raw_key
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    # Hard stop — nothing below renders until the key is set
    st.stop()

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712035.png", width=50)
    st.markdown("### **RetailOps** `Enterprise`")
    st.markdown("---")

    col_p1, col_p2 = st.columns([1, 3])
    with col_p1:
        st.write("👤")
    with col_p2:
        st.caption("Logged in as")
        user_role = st.text_input("Role", value="Store Manager", label_visibility="collapsed")

    st.markdown("---")
    st.markdown("📍 **Store Context**")
    store_name   = st.text_input("Store Name", value="Mumbai Flagship Store")
    st.info(store_name)

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        product_input = st.text_input("Product", value="Samsung TV")
    with col_s2:
        season_input  = st.text_input("Season / Event", value="Pre-Diwali")

    days_ahead = st.slider("Forecast Horizon (Days)", min_value=7, max_value=90, value=30, step=7)

    st.markdown("---")
    st.markdown("📡 **System Status**")
    masked = "sk-or-..." + st.session_state.openrouter_api_key[-6:] if len(st.session_state.openrouter_api_key) > 6 else "Active ✅"
    st.markdown(f'<div><span class="status-indicator"></span>MCP Auth: <b>{masked}</b></div>', unsafe_allow_html=True)
    st.markdown('<div><span class="status-indicator"></span>Catalog Enricher: <b>Online</b></div>', unsafe_allow_html=True)
    st.markdown('<div><span class="status-indicator"></span>Forecasting Node: <b>Online</b></div>', unsafe_allow_html=True)
    st.markdown('<div><span class="status-indicator"></span>Replenishment Node: <b>Online</b></div>', unsafe_allow_html=True)
    st.markdown('<div><span class="status-indicator"></span>Pricing Node: <b>Online</b></div>', unsafe_allow_html=True)

    st.markdown("---")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        if st.button("Reset Demo", type="secondary", use_container_width=True):
            st.session_state.messages = []
            st.session_state.script_step = 0
            st.rerun()
    with col_r2:
        if st.button("🔑 Change Key", type="secondary", use_container_width=True):
            st.session_state.openrouter_api_key = ""
            st.session_state.messages = []
            st.session_state.script_step = 0
            st.rerun()

# ─── HEADER ───────────────────────────────────────────────────────────────────
col_h1, col_h2 = st.columns([8, 2])
with col_h1:
    st.markdown('<h1 class="title-text">RetailOps Copilot</h1>', unsafe_allow_html=True)
    st.caption("Orchestrating Demand, Inventory, and Pricing with Enterprise AI")
with col_h2:
    st.markdown(f"**{time.strftime('%A, %d %B')}**")
    st.markdown(f"*{time.strftime('%H:%M %p')}*")

st.divider()

# ─── LANDING PAGE ─────────────────────────────────────────────────────────────
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
            if st.button("Scan Low Stock Items", key="btn_inv", use_container_width=True):
                st.session_state.initial_input = "Scan inventory and check stockout risks"
                st.session_state.script_step = 1
                st.rerun()
    with c3:
        with st.container(border=True):
            st.markdown("🏷️ **Pricing Strategy**")
            st.caption(f"Optimize for {season_input}")
            if st.button("Review Competitor Pricing", key="btn_price", use_container_width=True):
                st.session_state.initial_input = "Review competitor pricing and suggest optimal price"
                st.session_state.script_step = 1
                st.rerun()

# ─── RENDER HISTORY ───────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🤖"):
        st.write(msg["content"])

        if msg.get("type") == "trend_analysis":
            data = msg.get("data", {})
            forecast_val   = data.get("forecast", {}).get("final") or 1200
            category_label = data.get("enrichment", {}).get("category") or product_input

            c1, c2 = st.columns([1, 2])
            with c1:
                st.metric("Category", category_label)
                st.metric("Velocity", "High", delta=product_input)
            with c2:
                st.altair_chart(render_chart(forecast_val, days_ahead), use_container_width=True)
            st.caption(f"Source: MCP Catalog Enricher → Forecasting Node")

        if msg.get("type") == "action_plan":
            data      = msg.get("data", {})
            event_lbl = data.get("forecast", {}).get("event") or season_input
            f_val     = data.get("forecast", {}).get("final") or 0
            req       = data.get("replenishment", {}).get("reorder_qty") or 0
            risk      = data.get("replenishment", {}).get("stockout_risk") or "High"
            price     = data.get("pricing", {}).get("recommended_price") or 0
            cat       = data.get("enrichment", {}).get("category") or product_input
            narrative_f = data.get("forecast", {}).get("narrative", "")
            narrative_r = data.get("replenishment", {}).get("narrative", "")
            narrative_p = data.get("pricing", {}).get("narrative", "")

            st.markdown(f"### 📋 {event_lbl} Executive Plan")
            col_a, col_b, col_c = st.columns(3)

            with col_a:
                with st.container(border=True):
                    st.markdown("#### 🔮 Forecast")
                    st.metric("Projected Demand", f"{f_val:,.0f} Units", delta="Seasonal Lift")
                    st.progress(85, text="Confidence Score: High")
                    if narrative_f:
                        st.caption(narrative_f)

            with col_b:
                with st.container(border=True):
                    st.markdown("#### 📦 Inventory")
                    st.error(f"⚠️ Risk: {risk} Stockout")
                    st.write(f"Category: **{cat}**")
                    st.write(f"Required: **{req:,} Units**")
                    if narrative_r:
                        st.caption(narrative_r)
                    if st.button("🚀 Create Purchase Order", key=f"po_{id(msg)}"):
                        st.toast("Purchase Order Sent to ERP!", icon="✅")

            with col_c:
                with st.container(border=True):
                    st.markdown("#### 🏷️ Pricing")
                    change = data.get("pricing", {}).get("change_pct", 0)
                    st.metric("Optimal Price", f"₹{price:,.0f}", delta=f"{change:+.1f}%")
                    st.slider("Discount Adjustment", 0, 15, 8, format="%d%%", key=f"sl_{id(msg)}")
                    if narrative_p:
                        st.caption(narrative_p)
                    if st.button("✅ Apply Pricing", key=f"pr_{id(msg)}"):
                        st.toast("Prices updated in POS system", icon="🏷️")

# ─── INPUT HANDLING ───────────────────────────────────────────────────────────
process_query = None
if "initial_input" in st.session_state:
    process_query = st.session_state.initial_input
    del st.session_state.initial_input
elif query := st.chat_input("Ask RetailOps a question..."):
    process_query = query

# ─── PROCESSING LOGIC ─────────────────────────────────────────────────────────
if process_query:
    with st.chat_message("user", avatar="👤"):
        st.write(process_query)
    st.session_state.messages.append({"role": "user", "content": process_query})

    # ── STEP 1: DEMAND TRENDS ─────────────────────────────────────────────────
    if st.session_state.script_step == 0 or any(
        kw in process_query.lower() for kw in ["demand", "trend", "sales", "history"]
    ):
        st.session_state.script_step = 1
        with st.chat_message("assistant", avatar="🤖"):

            with st.status("🔍 Analyzing sales data...", expanded=True) as status:
                st.write("📡 Connecting to **Catalog Enricher MCP Server**...")
                time.sleep(0.8)
                st.write(f"📂 Retrieving product context for **{product_input}**...")
                time.sleep(0.6)
                st.write("📊 Aggregating seasonality patterns...")
                time.sleep(0.5)
                status.update(label="Analysis Complete", state="complete", expanded=False)

            with st.spinner("Fetching live data from MCP servers..."):
                result = simulate_mcp_pipeline(product_input, store_name, season_input, days_ahead)

            if "error" in result:
                st.error(f"MCP Error: {result['error']}")
                st.stop()

            cat          = result.get("enrichment", {}).get("category") or product_input
            forecast_val = result.get("forecast", {}).get("final") or 1200
            narrative_f  = result.get("forecast", {}).get("narrative", "")

            intro = (
                f"**[Catalog Enricher + Forecasting Node]** I've retrieved the historical data. "
                f"Here is the demand analysis for **{cat}** over the next **{days_ahead} days**:"
            )
            st.write_stream(stream_text(intro))

            c1, c2 = st.columns([1, 2])
            with c1:
                st.metric("Category", cat)
                st.metric("Velocity", "High", delta=product_input)
                mult = result.get("forecast", {}).get("seasonal_multiplier", 1.0)
                st.metric("Seasonal Multiplier", f"{mult:.2f}x")
            with c2:
                st.altair_chart(render_chart(forecast_val, days_ahead), use_container_width=True)

            if narrative_f:
                st.info(f"📝 **Forecasting Node:** {narrative_f}")
            st.caption(f"Source: RetailOps MCP Mesh · catalog-enricher → forecasting-node")

            # ── Follow-up action buttons (persist after landing page disappears) ──
            st.markdown("**What would you like to do next?**")
            fa1, fa2 = st.columns(2)
            with fa1:
                if st.button("📦 Scan Low Stock Items", key="fa_inv", use_container_width=True):
                    st.session_state.initial_input = "Scan inventory and check stockout risks"
                    st.session_state.script_step = 1
                    st.rerun()
            with fa2:
                if st.button("🏷️ Review Competitor Pricing", key="fa_price", use_container_width=True):
                    st.session_state.initial_input = "Review competitor pricing and suggest optimal price"
                    st.session_state.script_step = 1
                    st.rerun()

        st.session_state.messages.append({
            "role": "assistant",
            "content": intro,
            "type": "trend_analysis",
            "data": result
        })

    # ── STEP 2: FULL ORCHESTRATION ────────────────────────────────────────────
    elif st.session_state.script_step == 1 or any(
        kw in process_query.lower()
        for kw in [
            "diwali", "prepare", "event", "plan",
            "stock", "stockout", "inventory", "scan",
            "order", "replenish",
            "price", "pricing", "competitor", "optimal",
        ]
    ):
        st.session_state.script_step = 2
        with st.chat_message("assistant", avatar="🤖"):

            with st.spinner("Running RetailOps MCP workflow..."):
                result = simulate_mcp_pipeline(product_input, store_name, season_input, days_ahead)

            if "error" in result:
                st.error(f"MCP Error: {result['error']}")
                st.stop()

            cat    = result.get("enrichment", {}).get("category") or product_input
            event  = result.get("forecast", {}).get("event") or season_input
            f_val  = result.get("forecast", {}).get("final") or 1200
            mult   = result.get("forecast", {}).get("seasonal_multiplier", 1.0)
            req    = result.get("replenishment", {}).get("reorder_qty") or 0
            risk   = result.get("replenishment", {}).get("stockout_risk") or "High"
            price  = result.get("pricing", {}).get("recommended_price") or 0
            p_type = result.get("pricing", {}).get("type") or "Discount"
            change = result.get("pricing", {}).get("change_pct", 0)
            stock  = result.get("replenishment", {}).get("current_stock", "N/A")
            comp   = result.get("pricing", {}).get("competitor_price", "N/A")

            with st.status("🧬 Running `RetailOpsState` Workflow...", expanded=True) as status:

                st.write("🧠 **Azure OpenAI** interpreting intent: 'Event Preparation'...")
                time.sleep(0.4)

                st.write("🔵 **Node 1: Catalog Enricher** (`enrichment_node`)")
                time.sleep(0.5)
                st.code(json.dumps(result.get("enrichment", {}), indent=2), language="json")

                st.write("📊 **Node 2: Forecasting** (`forecasting_node`)")
                time.sleep(0.6)
                st.code(json.dumps(result.get("forecast", {}), indent=2), language="json")

                st.write("📦 **Node 3: Replenishment** (`replenishment_node`)")
                time.sleep(0.6)
                st.code(json.dumps(result.get("replenishment", {}), indent=2), language="json")

                st.write("💰 **Node 4: Pricing Strategy** (`pricing_node`)")
                time.sleep(0.6)
                st.code(json.dumps(result.get("pricing", {}), indent=2), language="json")

                status.update(label="✅ Workflow Completed Successfully", state="complete", expanded=False)

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
                    st.metric("Seasonal Multiplier", f"{mult:.2f}x")
                    st.progress(85, text="Confidence: High")
                    st.caption(result.get("forecast", {}).get("narrative", ""))

            with col_b:
                with st.container(border=True):
                    st.markdown("#### 📦 Inventory")
                    st.error(f"⚠️ Risk: {risk} Stockout")
                    st.write(f"Current Stock: **{stock} Units**")
                    st.write(f"Required: **{req:,} Units**")
                    st.caption(result.get("replenishment", {}).get("narrative", ""))
                    if st.button("🚀 Create Purchase Order", key="k_inv"):
                        st.toast("Purchase Order Sent to ERP!", icon="✅")

            with col_c:
                with st.container(border=True):
                    st.markdown("#### 🏷️ Pricing")
                    st.metric("Optimal Price", f"₹{price:,.0f}", delta=f"{change:+.1f}%")
                    st.write(f"Competitor Price: ₹{comp:,}" if isinstance(comp, (int, float)) else f"Competitor Price: {comp}")
                    st.write(f"Strategy: **{p_type}**")
                    st.slider("Discount Adjustment", 0, 15, 8, key="sl_price", format="%d%%")
                    st.caption(result.get("pricing", {}).get("narrative", ""))
                    if st.button("✅ Apply Pricing", key="k_price"):
                        st.toast("Prices updated in POS system", icon="🏷️")

        st.session_state.messages.append({
            "role": "assistant",
            "content": intro,
            "type": "action_plan",
            "data": result
        })

    # ── FALLBACK ──────────────────────────────────────────────────────────────
    else:
        with st.chat_message("assistant", avatar="🤖"):
            st.write(
                f"I'm ready to help with **{store_name}**. "
                "Try asking about **'Demand Trends'** or **'Prepare for Diwali'** to start the workflow."
            )
