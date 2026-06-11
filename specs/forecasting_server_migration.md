# 📐 Spec: Forecasting Server Migration (TypeScript)

## 🎯 Purpose
Port the Forecasting Server to TypeScript. The server generates sales forecasts for product categories using moving averages, seasonal events, and surge profiles.

---

## 📋 Requirements

### 1. Data File Reading
- The server must read the following configuration files from `servers/forecasting/data/`:
  - `sales_history.csv`: Historical sales records (`date`, `category`, `sales`).
  - `events.json`: Proximity seasonal multipliers.
  - `surge_profile.json`: Category-specific multiplier surge metrics per event.
- Use path resolution relative to the script directory using `Path` or `fs` to prevent location errors.

### 2. Algorithmic Forecasting
- **Moving Average Baseline**: Calculate the simple moving average sales for the specified category over the past 30 days.
- **Event Proximity Multiplier**: Read events from `events.json`. Find any event within the next 180 days from the current date. Retrieve its multiplier.
- **Historical Surge Profile**: Find the multiplier corresponding to the category and event combination in `surge_profile.json`.
- **Calculation**: `Final Forecast = Base Forecast * Event Multiplier * Historical Surge Multiplier`. Round to two decimal places.

### 3. OpenRouter API Integration
- Define a tool `getForecast(category: string, days_ahead?: number)` returning:
  - `category`: string
  - `base_forecast`: number
  - `seasonal_multiplier`: number
  - `historical_surge_factor`: number
  - `final_forecast`: number
  - `event`: string
  - `narrative`: string
- Connect to OpenRouter to explain the forecast details. If the API key is not present or calls fail, fall back to a local rule-based template narrative.

---

## ✅ Acceptance Criteria
- Running the compiled server and calling `getForecast` with `"tv"` returns the correct calculated metrics.
- No em dashes (—) are present.
- Standard logs are written to `console.error` (stderr).
