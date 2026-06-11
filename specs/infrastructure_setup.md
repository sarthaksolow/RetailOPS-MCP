# 📐 Spec: Infrastructure Setup (TypeScript & Prisma/SQLite)

## 🎯 Purpose
Establish the core runtime, TypeScript build pipeline, and Prisma ORM configuration with SQLite for the RetailOps system. This acts as the baseline infrastructure before migrating the MCP servers and orchestrator client to TypeScript.

---

## 📋 Requirements

### 1. Node.js & TypeScript Runtime
- Target Node.js version 20+.
- Initialize a root-level `package.json` supporting build, start, and test scripts.
- Configure `tsconfig.json` with strict type checking, ESNext targets, and module resolution for Node.js.

### 2. Database Persistence (SQLite & Prisma)
- Configure Prisma ORM with the SQLite database provider.
- Specify the database connection URL pointing to a local file: `file:../data/retailops.db` or similar within the workspace.
- Define a base Prisma schema to model:
  - **CategoryForecast**: Caches forecasting calculations.
  - **ReplenishmentDecision**: Caches inventory reorder quantities and timings.
  - **PricingRecommendation**: Caches recommended prices and strategies.
  - **AnalysisRun**: Logs the combined execution runs and errors.

### 3. Build & Formatting Checks
- Compile TypeScript source code successfully without syntax or type errors.
- Do NOT use em dashes (-) anywhere in text, comments, or scripts.

---

## ✅ Acceptance Criteria
- `npm install` installs all TS, Prisma, and MCP dependencies successfully.
- `npm run build` compiles TS files to a distribution directory (e.g. `dist/`).
- `npx prisma db push` or similar command runs without database errors and creates the SQLite database at `data/retailops.db`.
- No em dashes exist in any created config or source files.
