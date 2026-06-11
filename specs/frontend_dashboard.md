# 📐 Spec: Frontend Web UI & API Server (TypeScript & React)

## 🎯 Purpose
Build a lightweight Express API server and an interactive React/Tailwind frontend dashboard to query, execute, and visualize the RetailOps workflow states and historical SQLite cache logs.

---

## 📋 Requirements

### 1. API Server (`src/client/server.ts`)
Implement an Express server in TypeScript that serves:
- **Endpoints**:
  - `POST /api/analyze`: Body: `{ product_name: string, days_ahead?: number }`. Runs the full `RetailOpsClient` workflow and returns the accumulated state (written to SQLite).
  - `GET /api/runs`: Returns all analysis runs in SQLite using Prisma Client (`AnalysisRun` model with relations), sorted by timestamp descending.
  - `DELETE /api/runs`: Clears all analysis runs and cascade deletes cached records.
- **Static Assets**: Serve the compiled React SPA static folder from `dist/public`.

### 2. React SPA Frontend Dashboard (`src/public/index.html`)
Build a beautiful, modern single-page application (SPA) with React and Tailwind CSS:
- **Visual Design**:
  - Sleek dark mode using a premium, coordinated color palette (slate/indigo/indigo-accent).
  - Subtle micro-animations (hover transitions, spinner status).
  - Cohesive card layout for displaying:
    - **Forecast**: Projected demand, seasonal multiplier, upcoming event.
    - **Replenishment**: Reorder quantity, timing urgencies, stockout risk color coding.
    - **Pricing**: Recommended price, discount adjustments, strategy types.
- **Workflow Run Panel**: Simple inputs to test category names (e.g. `tv`, `laptop`, `groceries`, `fashion`) and forecast periods.
- **Run Logs Table**: Paginated list of past database entries from SQLite, allowing historical review.

---

## ✅ Acceptance Criteria
- `npm run start:dashboard` starts the server on port 3000.
- Accessing `http://localhost:3000` loads the dashboard interface.
- Running an analysis displays cards and updates the historical run table in real-time.
- Standard logs are written to `console.error` (stderr).
- No em dashes (—) are present.
