# 🛍️ RetailOps Autonomous Agent System

**AI-Powered Retail Operations Copilot with MCP Servers, SQLite Ledger, React Dashboard, and Autonomous Agent Loop**

A complete Model Context Protocol (MCP) system implemented in TypeScript that orchestrates forecasting, replenishment, pricing strategy, and recovery servers into an autonomous agentic loop.

---

## 🎯 System Architecture

Unlike standard static dashboards, RetailOps operates as a continuous, stateful, and self-correcting agent loop:

```
                  [Messy Data Sources]
                           |
                           v
         +----------------------------------+
         |     CYCLE TICK (every 20s)       |
         +----------------------------------+
                           |
                           v
                  [1. AUDITOR AGENT]
                  - Zero-shot LLM cleaning
                  - Category identification
                           |
                           v
                 [2. COMPOSITE SCORER]
                 - Calculates efficiency score
                 - Auto vs review tiering
                           |
               +-----------+-----------+
               |                       |
               v                       v
      [3. PROCUREMENT AGENT]   [4. PRICING AGENT]
      - Budget check (₹50k)    - Elasticity matches
      - Supplier routing       - Variance checks (15%)
      - Logistics delay sim
               |                       |
               +-----------+-----------+
                           |
                           v
                 [5. RECOVERY PLANNER]
                 - Resolves delayed orders
                 - Alt-supplier failover
                           |
                           v
                    [ACTION LEDGER]
                    - Reversible snapshots
                    - Undo capability
                           |
                           v
               [SEQUENCE FINANCIAL CONSOLE]
```

### The Autonomous Agents
* **Auditor Agent**: Dedupes records, filters anomalies, and uses zero-shot classification to map product descriptions to categories with confidence thresholds.
* **Scorer Agent**: Calculates composite business scores combining margins, demand volumes, and stockout risk penalties. Determines if the action is low-risk (auto-apply) or high-risk (queue for human review).
* **Procurement Agent**: Scores suppliers based on cost, lead time, and reliability to route orders. Purchase orders over ₹50,000 are queued for review; smaller orders execute automatically.
* **Pricing Agent**: Recommends discounts or premium markups. Changes exceeding 15% variance require manual operator sign-off.
* **Recovery Planner**: Automatically resolves simulated logistics disruptions (delays, partial deliveries, rejections) by re-routing orders to alternative suppliers.

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
# Launches the Express server and React dashboard
npm run start:dashboard
```
* The server listens on [http://localhost:3001](http://localhost:3001) in your browser.
* Dashboard uses bidirection WebSockets (`ws://localhost:3001`) to push live events and pull approvals.

### 🤖 Start the Autonomous Agent Daemon
```bash
# Start the background operations loop (ticks every 20 seconds)
npm run start:agent
```

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

## 🏗️ Technical Specifications & Conventions

### Sequence Financial Design System
The frontend has been redesigned to match the visual language of the Sequence Financial Dashboard (Dipa Inhouse):
* **Colors**: Background slate `#080b11`, Card base `#0e121e`, and Neon Phosphor Green `#00ff66` active indicators.
* **Layout**: Left vertical navigation rail, top header with WS status glow beacon, and structured summary metrics (logged procurement value, loop efficiency rating, pending approvals backlog).
* **Components**: SVG activity sparkline graph, tabbed consoles, and double-entry action logs.

### Stdio Safety
All MCP servers must print debug logs, warnings, or info to `console.error` (stderr). Writing to `stdout` is reserved exclusively for the MCP JSON-RPC protocol to prevent communication corruption.

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
NEVER use em dashes anywhere in documentation, commits, comments, or strings. Use regular hyphens (-) or colons (:) instead.
agy --conversation=608fcf84-04d7-48e8-ba2d-9540976550c2