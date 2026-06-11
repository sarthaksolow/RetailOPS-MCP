# 📐 Spec: Pricing Strategy Server Migration (TypeScript)

## 🎯 Purpose
Port the Pricing Strategy Server to TypeScript. This server recommends price adjustments based on price elasticity coefficients, competitor pricing, and inventory pressure.

---

## 📋 Requirements

### 1. File Data Loading
- Load configuration files:
  - `price_elasticity.json`: margin thresholds, coefficients, discount limits.
  - `competitor_prices.json`: average competitor price index.
- Use relative path resolution.

### 2. Pricing Recommendation Logic
- Calculate inventory ratio: `inventory_level / Math.max(1, forecasted_demand)`.
- Adjust price according to 4 modes:
  - **Clearance**: if inventory ratio > 2, recommend 8% discount.
  - **Premium**: if inventory ratio < 0.5, recommend 5% markup.
  - **Competitive**: if price exceeds competitor price by more than 10%, recommend 5% price reduction.
  - **Maintain**: no adjustment.
- Keep calculations formatted to 2 decimal places.

### 3. OpenRouter API Integration
- Expose MCP tool `getPricingStrategy(input)`.
- Connect to OpenRouter to explain the pricing recommendation in 2 sentences. Fall back to local rule-based templates if the API key is not present or calls fail.

---

## ✅ Acceptance Criteria
- Register `getPricingStrategy` tool.
- Return fields: `category`, `current_price`, `recommended_price`, `price_change_pct`, `recommendation_type`, `narrative`.
- Log only to `console.error` (stderr).
- No em dashes (—) exist in comments, strings, or code.
