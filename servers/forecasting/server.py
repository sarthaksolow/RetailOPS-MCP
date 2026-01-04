import json
import pandas as pd
from datetime import datetime
from mcp.server.fastmcp import FastMCP
import os
from openai import OpenAI
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()

# Redirect prints to stderr so they don't interfere with STDIO JSON communication
def log(message):
    print(message, file=sys.stderr, flush=True)

log(">>> Loading Forecasting MCP Server")

# Initialize MCP server
mcp = FastMCP("forecasting-server")

# Load data safely
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    log(f"BASE_DIR: {BASE_DIR}")

    sales_path = os.path.join(BASE_DIR, "data", "sales_history.csv")
    events_path = os.path.join(BASE_DIR, "data", "events.json")
    surge_path = os.path.join(BASE_DIR, "data", "surge_profile.json")

    log(f"Sales path: {sales_path}")
    log(f"Events path: {events_path}")
    log(f"Surge path: {surge_path}")

    sales_df = pd.read_csv(sales_path)
    log(f">>> Sales loaded: {len(sales_df)} rows")

    with open(events_path, "r") as f:
        events = json.load(f)
    log(f">>> Events loaded: {len(events.get('events', []))} events")

    with open(surge_path, "r") as f:
        surge_profiles = json.load(f)
    log(f">>> Surge profiles loaded: {len(surge_profiles)} profiles")

except Exception as e:
    log(f"⚠️ Startup error loading files: {e}")
    import traceback
    traceback.print_exc(file=sys.stderr)
    raise SystemExit(1)

# Configure OpenRouter API Client
api_key = os.getenv("OPENROUTER_API_KEY")
if api_key:
    log(">>> OpenRouter API configured")
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "http://localhost",            # required
            "X-Title": "Forecasting MCP Server"            # required
        }
    )
else:
    log("⚠️ WARNING: OPENROUTER_API_KEY not set")
    client = None


def simple_moving_average(category, days=30):
    """Calculate simple moving average for a category"""
    filtered = sales_df[sales_df["category"] == category]
    if filtered.empty:
        return None

    last_days = filtered.tail(days)
    return round(last_days["sales"].mean(), 2)


def get_season_multiplier():
    """Get seasonal multiplier based on upcoming events (within 6 months)"""
    today = datetime.now()
    for e in events["events"]:
        event_date = datetime.strptime(e["date"], "%Y-%m-%d")
        days_until = (event_date - today).days
        # Look up to 180 days (6 months) ahead
        if 0 <= days_until <= 180:
            return e["name"], e["multiplier"]
    return None, 1.0


def get_historical_surge(category, event_name):
    """Get historical surge factor for a category during specific event"""
    if event_name and event_name in surge_profiles:
        return surge_profiles[event_name].get(category, 1.0)
    return 1.0


async def generate_narrative(category, base, season_mult, hist_mult, final, event):
    """Generate AI narrative for the forecast"""
    if client is None:
        return "Narrative generation unavailable (API key not set)"

    prompt = f"""
You are a senior retail forecasting expert.

Category: {category}
Base Forecast: {base}
Seasonal Multiplier: {season_mult}
Historical Festival Surge Factor: {hist_mult}
Event: {event}
Final Forecast: {final}

Explain how these factors combined to produce the final forecast.
Keep it short, clear, and store-manager friendly.
"""

    try:
        completion = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=180,
        )

        return completion.choices[0].message.content

    except Exception as e:
        log(f"Narrative generation error: {e}")
        import traceback
        traceback.print_exc(file=sys.stderr)
        return f"Narrative generation failed: {str(e)}"


@mcp.tool()
async def getForecast(category: str, days_ahead: int = 30) -> dict:
    """
    Generate a sales forecast for a product category.
    """
    log(f">>> getForecast called for category: {category}")

    base = simple_moving_average(category)
    if base is None:
        return {"error": f"No data found for category '{category}'."}

    event_name, season_mult = get_season_multiplier()
    hist_mult = get_historical_surge(category, event_name)

    final_forecast = round(base * season_mult * hist_mult, 2)

    narrative = await generate_narrative(
        category, base, season_mult, hist_mult, final_forecast, event_name
    )

    result = {
        "category": category,
        "base_forecast": base,
        "seasonal_multiplier": season_mult,
        "historical_surge_factor": hist_mult,
        "final_forecast": final_forecast,
        "event": event_name,
        "narrative": narrative
    }

    log(">>> Forecast generated successfully")
    return result


log(">>> Forecasting MCP Server loaded successfully")

# Run the server when executed directly
if __name__ == "__main__":
    log(">>> Starting MCP server in STDIO mode")
    mcp.run()
