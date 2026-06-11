# 📐 Spec: Replenishment Server Migration (TypeScript)

## 🎯 Purpose
Port the Replenishment Server to TypeScript. This server recommends restocking quantities and timing (immediate, soon, or defer) using safety stock formulas and festival urgency.

---

## 📋 Requirements

### 1. Server Configuration
- Implement standard MCP STDIO server protocol.
- Expose the MCP tool `getReplenishmentDecision(input)`.

### 2. Replenishment Reasoning Logic
Implement the 7 reasoning nodes:
1. **Demand Risk Check**:
   - Parse `demand_volatility` (`low`: 1.1x, `medium`: 1.25x, `high`: 1.4x).
2. **Festival Urgency Check**:
   - Check if an upcoming festival event is within the supplier lead time. If yes, apply a `1.2` multiplier.
3. **Inventory Runway Calculation**:
   - Effective stock = `current_stock + in_transit_stock`.
   - Runway (days) = `effective_stock / avg_daily_demand`.
4. **Safety Stock Calculation**:
   - `safety_stock = Math.round(avg_daily_demand * lead_time_days * volatility_multiplier * festival_multiplier)`.
5. **Reorder Decision Logic**:
   - Raw quantity = `demand + safety_stock - effective_stock`.
   - If greater than 0, enforce `minimum_order_quantity` (MOQ). Otherwise, reorder quantity is 0.
6. **Timing Risk Classification**:
   - `immediate`: runway < supplier lead time (high risk)
   - `soon`: runway < 30 days (medium risk)
   - `defer`: runway >= 30 days (low risk)
7. **Narrative Generation**:
   - Construct a prompt and call OpenRouter to explain the decision.
   - If the API key is not present or calls fail, fall back to a local rule-based template narrative.

---

## ✅ Acceptance Criteria
- Register `getReplenishmentDecision` tool.
- Verify return fields: `reorder_qty`, `reorder_timing`, `stockout_risk`, `narrative`.
- Log only to `console.error` (stderr).
- No em dashes (—) exist in comments, strings, or code.
