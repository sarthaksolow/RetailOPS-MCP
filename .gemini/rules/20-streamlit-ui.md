---
globs:
  - "stapp.py"
  - "stapp_*.py"
  - "streamlit_*.py"
---
# 🎨 Frontend & UI Conventions

## Design Principles
- UI components must look premium and professional. Avoid default plain Streamlit components.
- Use custom HTML styled with vanilla CSS (inside `st.markdown(..., unsafe_allow_html=True)`) to design dashboard metric cards, error alerts, and statuses.
- Use HSL-curated or cohesive color palettes (dark/cool tones) for charts instead of default simple red/blue/green.

## Integration & Dynamism
- Dashboards must query backend client processes dynamically. Avoid hardcoding outputs in live execution states.
- If backend servers are offline or error out, display clear warning alerts in the UI with option to re-try or fallback to mock data.
