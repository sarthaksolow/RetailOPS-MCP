import fs from 'node:fs';
import path from 'node:path';
import { AuditResult, SalesRow } from '../types.js';
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

// Category price bounds: [minPrice, maxPrice]
const CATEGORY_PRICE_BOUNDS: Record<string, [number, number]> = {
  electronics:        [500,   200000],
  tv:                 [5000,  500000],
  laptop:             [10000, 300000],
  phone:              [2000,  200000],
  kitchen_appliances: [300,   100000],
  fashion:            [50,    50000],
  groceries:          [5,     10000],
  grocery:            [5,     10000],
  home:               [50,    100000],
  sports:             [50,    50000],
};

// Keywords used for category guessing (no LLM - pure heuristic)
const KEYWORD_CATEGORY_MAP: Array<{ keywords: string[]; category: string }> = [
  { keywords: ['tv', 'television', 'screen', 'oled', 'qled', 'smart tv', 'led tv'], category: 'tv' },
  { keywords: ['laptop', 'notebook', 'macbook', 'chromebook', 'thinkpad', 'ultrabook'], category: 'laptop' },
  { keywords: ['phone', 'mobile', 'iphone', 'android', 'smartphone', 'galaxy', 'realme', 'redmi', 'oneplus'], category: 'phone' },
  { keywords: ['headphone', 'earphone', 'speaker', 'router', 'tablet', 'ipad', 'kindle', 'monitor', 'printer', 'projector', 'camera'], category: 'electronics' },
  { keywords: ['shirt', 'trouser', 'dress', 'jeans', 'saree', 'kurta', 'jacket', 'shoe', 'sandal', 'bag', 'handbag', 'wallet', 'watch', 'belt'], category: 'fashion' },
  { keywords: ['rice', 'wheat', 'flour', 'dal', 'sugar', 'salt', 'oil', 'ghee', 'milk', 'butter', 'bread', 'biscuit', 'snack', 'spice', 'masala', 'noodle', 'cereal', 'juice', 'atta'], category: 'groceries' },
  { keywords: ['mixer', 'grinder', 'cooker', 'oven', 'microwave', 'fridge', 'refrigerator', 'washing', 'dishwasher', 'toaster', 'kettle', 'iron', 'fan', 'heater', 'ac', 'air conditioner'], category: 'kitchen_appliances' },
];

function guessCategory(productName: string): { category: string; confidence: number } {
  const lower = productName.toLowerCase();
  let bestCategory = 'electronics';
  let bestScore = 0;

  for (const entry of KEYWORD_CATEGORY_MAP) {
    for (const kw of entry.keywords) {
      if (lower.includes(kw)) {
        // Longer keyword matches are more specific
        const score = kw.length / lower.length + 0.5;
        if (score > bestScore) {
          bestScore = score;
          bestCategory = entry.category;
        }
      }
    }
  }

  // Cap confidence at 0.95
  const confidence = Math.min(bestScore, 0.95);
  return { category: bestCategory, confidence };
}

function parseCsv(raw: string): SalesRow[] {
  const lines = raw.trim().split('\n');
  if (lines.length < 2) return [];

  const header = lines[0].split(',').map(h => h.trim().toLowerCase());
  const rows: SalesRow[] = [];

  for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;

    // Handle quoted fields
    const parts: string[] = [];
    let current = '';
    let inQuotes = false;
    for (const ch of line) {
      if (ch === '"') {
        inQuotes = !inQuotes;
      } else if (ch === ',' && !inQuotes) {
        parts.push(current.trim());
        current = '';
      } else {
        current += ch;
      }
    }
    parts.push(current.trim());

    const get = (field: string): string => {
      const idx = header.indexOf(field);
      return idx >= 0 && idx < parts.length ? parts[idx] : '';
    };

    const qtyRaw = parseFloat(get('quantity') || get('qty') || '0');
    const priceRaw = parseFloat(get('unit_price') || get('price') || '0');

    rows.push({
      date: get('date'),
      product_id: get('product_id') || get('id') || `PROD-${i}`,
      product_name: get('product_name') || get('product') || get('name') || 'Unknown',
      category: get('category') || '',
      quantity: isNaN(qtyRaw) ? 0 : qtyRaw,
      unit_price: isNaN(priceRaw) ? 0 : priceRaw,
    });
  }

  return rows;
}

function buildDuplicateKey(row: SalesRow): string {
  return `${row.date}__${row.product_id}__${row.quantity}__${row.unit_price}`;
}

function computeMedianPrice(rows: SalesRow[], category: string): number {
  const prices = rows
    .filter(r => r.category === category && r.unit_price > 0)
    .map(r => r.unit_price)
    .sort((a, b) => a - b);

  if (prices.length === 0) return 1000;
  const mid = Math.floor(prices.length / 2);
  return prices.length % 2 === 0
    ? (prices[mid - 1] + prices[mid]) / 2
    : prices[mid];
}

function serializeCsv(rows: SalesRow[]): string {
  const header = 'date,product_id,product_name,category,quantity,unit_price';
  const lines = rows.map(r =>
    `${r.date},${r.product_id},"${r.product_name}",${r.category},${r.quantity},${r.unit_price.toFixed(2)}`
  );
  return [header, ...lines].join('\n') + '\n';
}

export class AuditorAgent {
  private messyCsvPath: string;
  private cleanCsvPath: string;

  constructor() {
    this.messyCsvPath = path.resolve('src/servers/forecasting/data/sales_history_messy.csv');
    this.cleanCsvPath = path.resolve('src/servers/forecasting/data/sales_history_clean.csv');
  }

  async run(): Promise<AuditResult> {
    // If messy CSV doesn't exist, fall back to the clean original
    const sourcePath = fs.existsSync(this.messyCsvPath)
      ? this.messyCsvPath
      : path.resolve('src/servers/forecasting/data/sales_history.csv');

    const raw = fs.readFileSync(sourcePath, 'utf-8');
    let rows = parseCsv(raw);

    let duplicatesRemoved = 0;
    let returns = 0;
    let flagged = 0;
    let anomaliesFixed = 0;

    // Step 1: Remove exact duplicates
    const seen = new Set<string>();
    const deduped: SalesRow[] = [];
    for (const row of rows) {
      const key = buildDuplicateKey(row);
      if (seen.has(key)) {
        duplicatesRemoved++;
      } else {
        seen.add(key);
        deduped.push(row);
      }
    }
    rows = deduped;

    // Step 2: Separate out returns (negative quantity)
    const nonNegative: SalesRow[] = [];
    for (const row of rows) {
      if (row.quantity < 0) {
        returns++;
        // Returns are not included in forward sales - skip them
      } else {
        nonNegative.push(row);
      }
    }
    rows = nonNegative;

    // Step 3: Fix missing categories (guess from product_name)
    const flaggedItems: Array<{
      row: SalesRow;
      guessedCategory: string;
      confidence: number;
    }> = [];

    for (const row of rows) {
      if (!row.category || row.category.trim() === '') {
        const { category, confidence } = guessCategory(row.product_name);
        if (confidence >= 0.7) {
          row.category = category;
          anomaliesFixed++;
        } else {
          row.category = category; // Still assign best guess
          flaggedItems.push({ row, guessedCategory: category, confidence });
          flagged++;
        }
      }
    }

    // Persist flagged items via Prisma
    if (flaggedItems.length > 0) {
      try {
        await prisma.flaggedItem.createMany({
          data: flaggedItems.map(fi => ({
            productId: fi.row.product_id,
            guessedCategory: fi.guessedCategory,
            confidence: fi.confidence,
            reason: `Missing category guessed based on keyword matched name: ${fi.row.product_name}`,
          })),
        });
      } catch (err) {
        console.error('[AUDITOR] Failed to persist flagged items:', err instanceof Error ? err.message : String(err));
      }
    }

    // Step 4: Fix impossible price outliers per category
    // First build a per-category median map from already-clean data
    const categoryMedians = new Map<string, number>();
    const categories = [...new Set(rows.map(r => r.category).filter(Boolean))];
    for (const cat of categories) {
      categoryMedians.set(cat, computeMedianPrice(rows, cat));
    }

    for (const row of rows) {
      if (!row.category) continue;
      const bounds = CATEGORY_PRICE_BOUNDS[row.category];
      if (!bounds) continue;

      const [minP, maxP] = bounds;
      if (row.unit_price > 0 && (row.unit_price < minP || row.unit_price > maxP)) {
        const median = categoryMedians.get(row.category) ?? 1000;
        row.unit_price = median;
        anomaliesFixed++;
      }
    }

    // Step 5: Write clean CSV
    const cleanCsv = serializeCsv(rows);
    try {
      const cleanDir = path.dirname(this.cleanCsvPath);
      if (!fs.existsSync(cleanDir)) {
        fs.mkdirSync(cleanDir, { recursive: true });
      }
      fs.writeFileSync(this.cleanCsvPath, cleanCsv, 'utf-8');
    } catch (err) {
      console.error('[AUDITOR] Failed to write clean CSV:', err instanceof Error ? err.message : String(err));
    }

    const cleaned = rows.length;

    console.error(`[AUDITOR] Audit complete: ${cleaned} clean rows, ${duplicatesRemoved} dupes removed, ${returns} returns removed, ${flagged} flagged, ${anomaliesFixed} anomalies fixed`);

    return {
      rows,
      cleaned,
      flagged,
      anomaliesFixed,
      quarantined: 0,
      confidenceMap: {},
    };
  }
}
