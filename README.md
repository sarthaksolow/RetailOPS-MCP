# 🛍️ RetailOps TypeScript MCP System

**AI-Powered Retail Operations Suite with MCP Servers, SQLite Cache, and React Dashboard**

A complete Model Context Protocol (MCP) system implemented in TypeScript that orchestrates forecasting, replenishment, and pricing strategy servers into intelligent retail workflows.

---

## 🎯 What This Does

Transform retail operations with AI-powered decision making:

```
[Catalog Enricher] -> [Forecasting] -> [Replenishment] -> [Pricing Strategy] -> [Express Server / SQLite] -> [React Dashboard]
```

* **Catalog Enrichment**: Maps category keywords, extracts brands, and searches alternative recommendations in SQLite.
* **Forecasting**: Predicts demand using sales history CSV and seasonal events.
* **Replenishment**: Recommends optimal reorder quantities and timing using safety stock formulas and festival urgency.
* **Pricing**: Recommends price adjustments (clearance discounts, premium markups, competitive price matches) based on stock levels, competitor pricing, and elasticity parameters.
* **Database Logs & Cache**: Persists analysis runs in SQLite with Prisma ORM.
* **React Web UI**: Premium glassmorphism dark-themed dashboard displaying forecasts, replenishment timing, stock risk, and pricing history.

---

## 🚀 Quick Start (5 Minutes)

### 1. Install Dependencies
Ensure you have Node 20+ installed.
```bash
npm install
```

### 2. Set Up Environment Variables
Create a `.env` file in the root directory:
```env
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct
```

### 3. Initialize & Seed Database
Sync the SQLite database schema and run the seed script:
```bash
# Push schema to data/retailops.db
npx prisma db push

# Generate Prisma Client
npm run prisma:generate

# Seed database with product catalog and mappings
npm run db:seed
```

### 4. Build the TypeScript Code
```bash
npm run build
```

---

## 🖥️ Running the Applications

### 🌐 Start the Web Dashboard
```bash
# Launches the Express server and React SPA dashboard
npm run start:dashboard
```
* The server automatically checks if port `3000` is in use (e.g. by Grafana) and falls back to `3001` or another port dynamically.
* Open [http://localhost:3001](http://localhost:3001) in your browser.

### 🔌 Start Individual MCP Servers
If you want to run the servers independently via STDIO:
```bash
# Catalog Enricher Server
npm run start:enricher

# Forecasting Server
npm run start:forecasting

# Replenishment Server
npm run start:replenishment

# Pricing Server
npm run start:pricing
```

### ⌨️ CLI Interface
Run analysis directly from the command line:
```bash
# Analyze a single product category
npm run cli analyze tv

# Run batch analysis
npm run cli batch electronics fashion groceries

# Forecast only
npm run cli forecast laptop

# Output JSON analysis
npm run cli json phone
```

---

## 🧪 Testing

The project contains two comprehensive TypeScript test suites:

### 1. E2E Integration Tests
Verifies the client orchestrator, STDIO server connections, state accumulation, and SQLite run persistence:
```bash
npm run test:integration
```

### 2. Mathematical Stress Tests
Validates mathematical calculations, safety stock triggers, MOQ limits, inventory runways, and dynamic pricing rules using synthetic datasets:
```bash
npm run test:stress
```

---

## 🏗️ Architecture & Conventions

### Stdio Safety
All MCP servers must print debug logs, warnings, or info to `console.error` (stderr). Writing to `stdout` is reserved exclusively for the MCP JSON-RPC protocol to prevent communication corruption.

### State Management
The orchestrator accumulates results sequentially from each server node in a single state object:
1. **Catalog Enricher**: Identifies the category and alternative suggestions.
2. **Forecasting**: Calculates demand forecasts.
3. **Replenishment**: Determines runway and safety stock levels.
4. **Pricing**: Recommends discounts or markup strategies.
5. **Persistence**: Saves the consolidated results to `data/retailops.db`.

### Git Commit Conventions
Commit messages must follow the pattern:
```
[tag] Scope: Description
```
Supported tags:
* `[add]`: Adding new feature code or files.
* `[fix]`: Fixing bugs or issues.
* `[update]`: Updating existing features, refactoring, or UI fixes.
* `[docs]`: Editing documentation.
* `[test]`: Adding or refactoring test suites.

### Strict Coding Constraints
NEVER use em dashes (-) anywhere in documentation, commits, comments, or strings. Use regular hyphens (-) or colons (:) instead.
