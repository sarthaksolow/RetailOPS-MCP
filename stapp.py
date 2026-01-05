import streamlit as st
import time
import pandas as pd
import numpy as np
import altair as alt

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="RetailOps | LangGraph Orchestrator",
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
            background-color: #0E1117;
            color: #FAFAFA;
        }

        /* Gradient Title */
        .title-text {
            background: -webkit-linear-gradient(45deg, #2E9AFF, #00CC96);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
            font-size: 3rem;
            letter-spacing: -1px;
        }

        /* Metric Cards Styling */
        div[data-testid="stMetric"] {
            background-color: #1E1E1E;
            border: 1px solid #333;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            transition: all 0.3s ease;
        }
        div[data-testid="stMetric"]:hover {
            transform: translateY(-5px);
            border-color: #2E9AFF;
            box-shadow: 0 10px 20px rgba(46, 154, 255, 0.2);
        }

        /* Status Indicators */
        .status-badge {
            display: inline-flex;
            align-items: center;
            padding: 4px 8px;
            border-radius: 4px;
            background: rgba(0, 204, 150, 0.1);
            border: 1px solid rgba(0, 204, 150, 0.3);
            color: #00CC96;
            font-size: 0.8rem;
            margin-bottom: 5px;
        }
        .status-dot {
            width: 6px;
            height: 6px;
            background-color: #00CC96;
            border-radius: 50%;
            margin-right: 6px;
            box-shadow: 0 0 8px #00CC96;
        }
        
        /* Action Button Styling */
        .stButton button {
            background: linear-gradient(90deg, #2E9AFF 0%, #0078D7 100%);
            border: none;
            padding: 0.6rem 1.2rem;
            color: white;
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            width: 100%;
        }

        .stButton button:hover {
            box-shadow: 0 0 15px rgba(46, 154, 255, 0.5);
            transform: scale(1.02);
        }
        
        .stButton button:disabled {
            background: #333;
            color: #666;
            cursor: not-allowed;
        }
        
        /* Chat Message Styling */
        .stChatMessage {
            background-color: #161920;
            border: 1px solid #2B2D31;
            border-radius: 12px;
            padding: 1rem;
        }
        
        /* Custom Container Borders */
        div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"] {
            border: 1px solid #333;
            border-radius: 12px;
            padding: 1rem;
            background: #161920;
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- INITIALIZATION ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "script_step" not in st.session_state:
    st.session_state.script_step = 0

# --- SIDEBAR (MCP SERVER STATUS) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712035.png", width=50) # Generic AI Icon
    st.markdown("### **RetailOps** `Orchestrator`")
    st.markdown("---")
    
    # Context
    st.markdown("📍 **LangGraph State**")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.metric("Product", "Samsung TV", border=False)
    with col_s2:
        st.metric("Horizon", "30 Days", border=False)
        
    st.markdown("---")
    
    # MCP Server Status (Matching client.py MCPServerManager)
    st.markdown("📡 **Active MCP Servers**")
    
    servers = [
        "Catalog Enricher",
        "Forecasting Server",
        "Replenishment Server",
        "Pricing Strategy"
    ]
    
    for server in servers:
        st.markdown(f'''
        <div class="status-badge" style="width: 100%; justify-content: space-between;">
            <span><span class="status-dot"></span>{server}</span>
            <span style="opacity: 0.7;">Idle</span>
        </div>
        ''', unsafe_allow_html=True)
    
    st.markdown("---")
    if st.button("Reset Demo", type="secondary"):
        st.session_state.messages = []
        st.session_state.script_step = 0
        st.rerun()

# --- MAIN HEADER ---
col_h1, col_h2 = st.columns([8, 2])
with col_h1:
    st.markdown('<h1 class="title-text">RetailOps Client</h1>', unsafe_allow_html=True)
    st.caption("LangGraph Orchestrator: Enrich → Forecast → Replenish → Price")
with col_h2:
    st.markdown(f"**{time.strftime('%A, %d %B')}**")
    st.markdown(f"*{time.strftime('%H:%M %p')}*")

st.divider()

# --- HELPER FUNCTIONS ---
def stream_text(text, delay=0.03):
    for word in text.split(" "):
        yield word + " "
        time.sleep(delay)

def render_chart():
    data = pd.DataFrame({
        'Day': range(1, 31),
        'Base Demand': np.random.normal(100, 10, 30).cumsum(),
        'Enriched Forecast': np.random.normal(120, 15, 30).cumsum()
    }).melt('Day', var_name='Type', value_name='Sales')

    chart = alt.Chart(data).mark_line(interpolate='monotone').encode(
        x='Day',
        y='Sales',
        color=alt.Color('Type', scale=alt.Scale(domain=['Base Demand', 'Enriched Forecast'], range=['#555', '#00CC96'])),
        tooltip=['Day', 'Sales', 'Type']
    ).properties(height=250).configure_view(strokeWidth=0).configure_axis(grid=False)
    
    return chart

# --- CHAT UI LOGIC ---

# 1. LANDING PAGE (Empty State)
if len(st.session_state.messages) == 0:
    st.markdown("### 👋 Orchestrator Ready.")
    st.markdown("I am connected to the MCP Server Mesh. How should I initialize the workflow?")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.info("📊 **Analyze Trends**")
        if st.button("Show recent demand trends", key="btn_trends"):
            st.session_state.initial_input = "Show me recent demand trends"
            st.session_state.script_step = 1
            st.rerun()
    with c2:
        st.warning("⚡ **Full Workflow**")
        st.button("Prepare store for Diwali", key="btn_diwali", disabled=True)
    with c3:
        st.success("⚙️ **System Check**")
        st.button("Ping MCP Servers", key="btn_ping", disabled=True)

# 2. RENDER HISTORY
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🤖"):
        st.write(msg["content"])
        
        # Render Trend Analysis
        if msg.get("type") == "trend_analysis":
            st.markdown("#### 🧹 Catalog Enricher Output")
            st.caption("Mapped Input 'Trends' → Category 'Electronics'")
            
            c1, c2 = st.columns([1, 2])
            with c1:
                st.metric("Category Detected", "Electronics")
                st.metric("Historical Velocity", "High", delta="Smart TVs")
            with c2:
                st.altair_chart(render_chart(), use_container_width=True)

        # Render Full Workflow Output (The 3 Agent Cards)
        if msg.get("type") == "action_plan":
            st.markdown("### 🧬 LangGraph Execution Result")
            
            col_a, col_b, col_c = st.columns(3)
            
            # Forecasting Node Output
            with col_a:
                st.markdown("#### 📊 Forecasting")
                st.caption("Node: `forecasting_node`")
                st.metric("Final Forecast", "1,200 Units", delta="45% Seasonal Lift")
                st.progress(85, text="Event Detected: Diwali")
            
            # Replenishment Node Output
            with col_b:
                st.markdown("#### 📦 Replenishment")
                st.caption("Node: `replenishment_node`")
                st.error("Risk: Stockout Likely")
                st.write("Reorder Qty: **600 Units**")
                if st.button("🚀 Create PO #9021"):
                    st.toast("Purchase Order Sent via ERP!", icon="✅")
            
            # Pricing Node Output
            with col_c:
                st.markdown("#### 💰 Pricing Strategy")
                st.caption("Node: `pricing_node`")
                st.metric("Recommended Price", "₹28,000", delta="-₹4,000")
                st.write("Recommendation: **Discount**")
                if st.button("✅ Apply Pricing"):
                    st.toast("Prices updated in POS system", icon="🏷️")

# 3. INPUT HANDLING
process_query = None
if "initial_input" in st.session_state:
    process_query = st.session_state.initial_input
    del st.session_state.initial_input
elif query := st.chat_input("Ask the Orchestrator..."):
    process_query = query

# 4. PROCESSING LOGIC
if process_query:
    # Show User Message
    with st.chat_message("user", avatar="👤"):
        st.write(process_query)
    st.session_state.messages.append({"role": "user", "content": process_query})

    # --- STEP 1: DEMAND TRENDS (Enricher + History) ---
    if st.session_state.script_step == 0 or "demand" in process_query.lower():
        st.session_state.script_step = 1
        with st.chat_message("assistant", avatar="🤖"):
            # Visualize the Node Execution
            with st.status("🔗 Executing Graph...", expanded=True) as status:
                st.write("🔵 **Node 1: Catalog Enricher**")
                time.sleep(0.8)
                st.write("   └─ Input: 'Demand Trends'")
                time.sleep(0.5)
                st.write("   └─ Output: Category='Electronics', Brand='Generic'")
                status.update(label="Enrichment Complete", state="complete", expanded=False)
            
            intro = "I've passed the input through the **Catalog Enricher**. It mapped your query to the **Electronics** category. Retrieving historical data..."
            st.write_stream(stream_text(intro))
            
            # Chart & Metrics
            st.markdown("#### 🧹 Catalog Enricher Output")
            st.caption("Mapped Input 'Trends' → Category 'Electronics'")
            
            c1, c2 = st.columns([1, 2])
            with c1:
                st.metric("Category Detected", "Electronics")
                st.metric("Historical Velocity", "High", delta="Smart TVs")
            with c2:
                st.altair_chart(render_chart(), use_container_width=True)

        # Save state
        st.session_state.messages.append({
            "role": "assistant",
            "content": intro,
            "type": "trend_analysis"
        })

    # --- STEP 2: DIWALI PREP (Full LangGraph Chain) ---
    elif st.session_state.script_step == 1 or "diwali" in process_query.lower():
        st.session_state.script_step = 2
        with st.chat_message("assistant", avatar="🤖"):
            
            # THIS MATCHES YOUR CLIENT.PY FLOW EXACTLY
            with st.status("🧬 Running `RetailOpsState` Workflow...", expanded=True) as status:
                
                # Node 1: Enricher
                st.write("🔵 **Node 1: Catalog Enricher** (`enrichment_node`)")
                time.sleep(0.8)
                st.code("State Update: {'category': 'Electronics', 'event': 'Diwali'}", language="json")
                
                # Node 2: Forecasting
                st.write("📊 **Node 2: Forecasting** (`forecasting_node`)")
                time.sleep(0.8)
                st.code("Output: {'final_forecast': 1200, 'seasonal_multiplier': 1.45}", language="json")
                
                # Node 3: Replenishment
                st.write("📦 **Node 3: Replenishment** (`replenishment_node`)")
                time.sleep(0.8)
                st.code("Output: {'reorder_qty': 600, 'risk': 'High'}", language="json")
                
                # Node 4: Pricing
                st.write("💰 **Node 4: Pricing Strategy** (`pricing_node`)")
                time.sleep(0.8)
                st.code("Output: {'rec_price': 28000, 'type': 'Discount'}", language="json")
                
                status.update(label="Workflow Completed Successfully", state="complete", expanded=False)
            
            intro = "The **LangGraph Orchestrator** has completed the chain. Here is the unified decision output:"
            st.write_stream(stream_text(intro))

            # The Result Cards
            st.markdown("### 🧬 LangGraph Execution Result")
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                st.markdown("#### 📊 Forecasting")
                st.caption("Node: `forecasting_node`")
                st.metric("Final Forecast", "1,200 Units", delta="45% Seasonal Lift")
                st.progress(85, text="Event Detected: Diwali")
            
            with col_b:
                st.markdown("#### 📦 Replenishment")
                st.caption("Node: `replenishment_node`")
                st.error("Risk: Stockout Likely")
                st.write("Reorder Qty: **600 Units**")
                if st.button("🚀 Create PO #9021", key="k_inv"):
                    st.toast("PO Sent!", icon="✅")
            
            with col_c:
                st.markdown("#### 💰 Pricing Strategy")
                st.caption("Node: `pricing_node`")
                st.metric("Recommended Price", "₹28,000", delta="-₹4,000")
                st.write("Recommendation: **Discount**")
                if st.button("✅ Apply Pricing", key="k_price"):
                    st.toast("Prices Updated!", icon="🏷️")

        # Save state
        st.session_state.messages.append({
            "role": "assistant",
            "content": intro,
            "type": "action_plan"
        })

    # --- FALLBACK ---
    else:
        with st.chat_message("assistant", avatar="🤖"):
            st.write("Workflow ready. Please initialize with 'Demand Trends' or 'Diwali Prep'.")