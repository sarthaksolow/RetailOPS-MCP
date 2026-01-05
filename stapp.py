import streamlit as st
import time
import pandas as pd
import numpy as np
import altair as alt

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
            background-position: right center; /* change the direction of the change here */
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

# --- INITIALIZATION ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "script_step" not in st.session_state:
    st.session_state.script_step = 0

# --- SIDEBAR (COMMAND CENTER CONTEXT) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712035.png", width=50) # Generic AI Icon
    st.markdown("### **RetailOps** `Enterprise`")
    st.markdown("---")
    
    # Profile
    col_p1, col_p2 = st.columns([1, 3])
    with col_p1:
        st.write("👤")
    with col_p2:
        st.caption("Logged in as")
        st.write("**Store Manager**")
    
    st.markdown("---")
    
    # Context
    st.markdown("📍 **Store Context**")
    st.info("Mumbai Flagship Store")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.metric("Category", "Electronics", border=False)
    with col_s2:
        st.metric("Season", "Pre-Diwali", delta="Peak", border=False)
        
    st.markdown("---")
    
    # System Status (The "Trust" Factor)
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
    # A date display to make it look live
    st.markdown(f"**{time.strftime('%A, %d %B')}**")
    st.markdown(f"*{time.strftime('%H:%M %p')}*")

st.divider()

# --- HELPER FUNCTIONS ---
def stream_text(text, delay=0.03):
    for word in text.split(" "):
        yield word + " "
        time.sleep(delay)

def render_chart():
    # Mock Data for Comparison
    data = pd.DataFrame({
        'Day': range(1, 31),
        'Last Year': np.random.normal(100, 10, 30).cumsum(),
        'Current Forecast': np.random.normal(120, 15, 30).cumsum()
    }).melt('Day', var_name='Type', value_name='Sales')

    chart = alt.Chart(data).mark_line(interpolate='monotone').encode(
        x='Day',
        y='Sales',
        color=alt.Color('Type', scale=alt.Scale(domain=['Last Year', 'Current Forecast'], range=['#808080', '#00CC96'])),
        tooltip=['Day', 'Sales', 'Type']
    ).properties(height=300).configure_view(strokeWidth=0)
    
    return chart

# --- CHAT UI LOGIC ---

# 1. LANDING PAGE (Empty State)
if len(st.session_state.messages) == 0:
    st.markdown("### 👋 Good morning, Manager.")
    st.markdown("I've analyzed yesterday's sales. Your **Electronics** category is moving fast.")
    
    st.markdown("#### Suggested Actions:")
    
    # Interactive Suggestion Cards
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
            st.caption("Optimize for Diwali")
            st.button("Review Competitor Pricing", key="btn_price", use_container_width=True, disabled=True)

# 2. RENDER HISTORY
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🤖"):
        st.write(msg["content"])
        
        # Render complex UI elements stored in history
        if msg.get("type") == "trend_analysis":
            c1, c2 = st.columns([1, 2])
            with c1:
                st.metric("Growth (MoM)", "15%", delta="4.2%", help="Month over Month Growth")
                st.metric("Velocity", "High", delta="Smart TVs", help="Fastest moving SKU")
            with c2:
                st.altair_chart(render_chart(), use_container_width=True)
            st.caption("Source: Azure AI Search index `sales-history-2023`")

        if msg.get("type") == "action_plan":
            # The Action Plan Dashboard
            st.markdown("### 📋 Diwali Executive Plan")
            
            # Three Cards for the Agents
            col_a, col_b, col_c = st.columns(3)
            
            # Forecast Card
            with col_a:
                with st.container(border=True):
                    st.markdown("#### 🔮 Forecast")
                    st.metric("Projected Demand", "1,200 Units", delta="45% Surge")
                    st.progress(85, text="Confidence Score: High")
                    st.caption("Driven by: 'Pre-Diwali' Event Signal")
            
            # Inventory Card
            with col_b:
                with st.container(border=True):
                    st.markdown("#### 📦 Inventory")
                    st.error("⚠️ Risk: High Stockout")
                    st.write("Current Stock: **45 Units**")
                    st.write("Required: **600 Units**")
                    if st.button("🚀 Create PO #9021"):
                        st.toast("Purchase Order Sent to ERP!", icon="✅")
            
            # Pricing Card
            with col_c:
                with st.container(border=True):
                    st.markdown("#### 🏷️ Pricing")
                    st.metric("Optimal Price", "₹28,000", delta="-₹4,000")
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
    # Show User Message
    with st.chat_message("user", avatar="👤"):
        st.write(process_query)
    st.session_state.messages.append({"role": "user", "content": process_query})

    # --- STEP 1: DEMAND TRENDS ---
    if st.session_state.script_step == 0 or "demand" in process_query.lower():
        st.session_state.script_step = 1
        with st.chat_message("assistant", avatar="🤖"):
            # AI Magic Status
            with st.status("🔍 analyzing sales data...", expanded=True) as status:
                st.write("Connecting to Azure AI Search...")
                time.sleep(1)
                st.write("Retrieving index `sales_history_mumbai`...")
                time.sleep(0.5)
                st.write("Aggregating seasonality patterns...")
                time.sleep(0.5)
                status.update(label="Analysis Complete", state="complete", expanded=False)
            
            # Text Response
            intro = "**[Azure AI Search]** I've retrieved the historical data. Here is the demand analysis for **Electronics**:"
            st.write_stream(stream_text(intro))
            
            # Chart & Metrics
            c1, c2 = st.columns([1, 2])
            with c1:
                st.metric("Growth (MoM)", "15%", delta="4.2%")
                st.metric("Velocity", "High", delta="Smart TVs")
            with c2:
                st.altair_chart(render_chart(), use_container_width=True)
            st.caption("Source: Azure AI Search index `sales-history-2023`")

        # Save state
        st.session_state.messages.append({
            "role": "assistant",
            "content": intro,
            "type": "trend_analysis"
        })

    # --- STEP 2: DIWALI PREP ---
    elif st.session_state.script_step == 1 or "diwali" in process_query.lower():
        st.session_state.script_step = 2
        with st.chat_message("assistant", avatar="🤖"):
            # AI Magic Status
            with st.status("⚡ Orchestrating Retail Agents...", expanded=True) as status:
                st.write("🧠 **Azure OpenAI** interpreting intent: 'Event Preparation'...")
                time.sleep(1)
                st.write("🔮 **Forecaster Agent:** Calculating demand surge...")
                time.sleep(0.8)
                st.write("📦 **Inventory Agent:** Checking supply chain lead times...")
                time.sleep(0.8)
                st.write("🏷️ **Pricing Agent:** Simulating elasticity...")
                time.sleep(0.8)
                status.update(label="Action Plan Generated", state="complete", expanded=False)
            
            intro = "Based on the orchestration, here is your unified **Diwali Action Plan**. I have coordinated the forecast, inventory, and pricing agents."
            st.write_stream(stream_text(intro))

            # The Cards
            st.markdown("### 📋 Diwali Executive Plan")
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                with st.container(border=True):
                    st.markdown("#### 🔮 Forecast")
                    st.metric("Projected Demand", "1,200 Units", delta="45% Surge")
                    st.progress(85, text="Confidence: High")
            
            with col_b:
                with st.container(border=True):
                    st.markdown("#### 📦 Inventory")
                    st.error("⚠️ Risk: High Stockout")
                    st.write("Required: **600 Units**")
                    if st.button("🚀 Create PO #9021", key="k_inv"):
                        st.toast("PO Sent!", icon="✅")
            
            with col_c:
                with st.container(border=True):
                    st.markdown("#### 🏷️ Pricing")
                    st.metric("Optimal Price", "₹28,000", delta="-₹4,000")
                    st.slider("Discount", 0, 15, 8, key="sl_price")
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
            st.write("I'm ready for the demo. Try asking about 'Demand Trends' or 'Diwali'.")