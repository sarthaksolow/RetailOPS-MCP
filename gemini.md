# 🛍️ RetailOps MCP - Project Conventions (TypeScript)

This guide defines the commands, conventions, architecture, and coding standards for the RetailOps TypeScript MCP project.

---

## 🛠️ Build and Run Commands

### Backend (TypeScript)
* **Node version**: Node 20+
* **Dependencies installation**: `npm install` (or `pnpm install` / `yarn install`)
* **Build TypeScript**: `npm run build`
* **Run Forecasting Server**: `npm run start:forecasting`
* **Run Replenishment Server**: `npm run start:replenishment`
* **Run Pricing Server**: `npm run start:pricing`
* **Run Catalog Enricher Server**: `npm run start:enricher`

### Database (SQLite)
* **Local DB file**: `data/retailops.db`
* **Schema migrations**: Prisma ORM with SQLite provider is used for database schema and persistence.

---

## 🧪 Testing Commands
* **Run Unit Tests**: `npm run test`
* **Run Integration Tests**: `npm run test:integration`

---

## 🏗️ Architecture & Flow

The system operates as a sequential workflow orchestrated in TypeScript:
```
[Catalog Enricher] -> [Forecasting] -> [Replenishment] -> [Pricing Strategy] -> [Frontend App]
```

### State Management
- Workflows must maintain a single, comprehensive state object that accumulates data from each server.
- The state must be type-safe, utilizing strict TypeScript interfaces.

---

## 💅 Code Style & Rules

### TypeScript Guidelines
- **Strict Typing**: Enforce strict TypeScript types and interfaces for all functions, tool inputs, and state schemas. Avoid the use of `any` unless absolutely necessary.
- **Variable Names**: Keep variables clean, short, and descriptive (e.g. `reqQty` instead of `requestedReorderQuantity`).
- **Fallbacks**: Wrap all external service/LLM queries in try-catch blocks and supply a local fallback template or rule-based response in case of API failure.
- **SQLite Caching**: Cache forecast data and analysis results in the local SQLite database to prevent redundant API calls.
- **Formatting Restriction**: NEVER use em dashes (—) anywhere in documentation, commits, comments, or strings. Use regular hyphens (-) or colons (:) instead.

### MCP Server Standards (TypeScript)
- **STDIO Safety**: Never use `console.log` or write to `stdout` for logging in MCP server code. All logs, warnings, or debug messages must go to `console.error` (which writes to `stderr`) to prevent protocol corruption.
- **Tool Registration**: Use `@modelcontextprotocol/sdk` to register tools with descriptions.

### Frontend Standards (TypeScript-based Web UI)
- **UI Stack**: A simple TypeScript/React/Vite single-page application (SPA).
- **Design Guidelines**: Cohesive design system, interactive charts (e.g. using Recharts), and responsive layouts.

---

## 🐙 Git Commit Conventions
Commit messages must follow the pattern:
```
[tag] Scope: Description
```

### Supported Tags
- `[add]`: Adding new feature code or files (e.g., `[add] FrontendUI : persona switcher added`)
- `[fix]`: Fixing bugs or issues (e.g., `[fix] BackendInfra : fixed deep dive threads`)
- `[update]`: Updating existing features, refactoring, or UI fixes (e.g., `[update] FrontendUI : chat layout fixes`)
- `[docs]`: Editing documentation (e.g., `[docs] update readme`)
- `[test]`: Adding or refactoring test suites (e.g., `[test] moved test scripts to a tests folder`)
