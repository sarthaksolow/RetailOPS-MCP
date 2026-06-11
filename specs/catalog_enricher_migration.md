# 📐 Spec: Catalog Enricher Server Migration (TypeScript)

## 🎯 Purpose
Port the Catalog Enricher server to TypeScript, migrating mock product listings and category keywords into the local SQLite database via Prisma, and providing a robust product classification tool.

---

## 📋 Requirements

### 1. Database Schema Extensions (Prisma)
Add the following models to `prisma/schema.prisma`:
- **CatalogProduct**: Stores the base product catalog (`id`, `name`, `brand`, `category`, `price`, `marginPct`, `description`).
- **CategoryMapping**: Stores keyword-to-category associations (`keyword`, `category`).

### 2. Database Seeding
- Implement a script to load and seed the SQLite database with the legacy data from `category_mappings.json` and `product_catalog.json`.

### 3. Server Logic (`src/servers/catalog-enricher/server.ts`)
- Use the `@modelcontextprotocol/sdk` to build the STDIO-based MCP server.
- Expose the MCP tool `enrichProduct(input: { product_name: string, product_data?: any })`.
- **Enrichment Pipeline**:
  1. **Clean Name**: Trim whitespace, normalize characters, remove noise words.
  2. **Categorize**:
     - Check database for exact or keyword matches (via `CategoryMapping` and `CatalogProduct` tables).
     - If no database match is found, fallback to OpenRouter zero-shot classification.
     - If OpenRouter fails, use rule-based category heuristics.
  3. **Extract Attributes**: Extract brand (e.g. first word), size/weight patterns, and write a default description.
  4. **Find Alternatives**: Search the `CatalogProduct` table for items matching the same category but with a different brand (up to 3 items).
  5. **Narrative Summary**: Call OpenRouter to summarize the product profile, falling back to a pre-defined local text template.

---

## ✅ Acceptance Criteria
- `npx prisma db push` successfully registers the new models in SQLite.
- A database seed script successfully populates the SQLite tables.
- Running the compiled server and calling `enrichProduct` with `"Samsung TV"` returns:
  - Cleaned name: `"Samsung TV"` or similar.
  - Category: `"electronics"`.
  - Brand: `"Samsung"`.
  - Alternatives: at least one other TV brand from the database (e.g., LG LED TV).
- All logs are written to `console.error` (stderr) and none to `console.log` (stdout).
- No em dashes exist in any source or config files.
