import fs from 'node:fs';
import path from 'node:path';
import { PrismaClient } from '@prisma/client';
import { PurchaseOrder, Supplier, CompositeScore, LogisticsEvent } from '../types.js';

// Raw shape coming from the existing suppliers.json file
interface RawSupplierEntry {
  id: string;
  name: string;
  category: string;   // single category string in the existing file
  leadTimeDays: number;
  costPerUnit: number;
  minOrderQty: number;
  reliability: number;
}

interface RawSuppliersFile {
  suppliers: RawSupplierEntry[];
}

function loadSuppliers(): Supplier[] {
  const filePath = path.resolve('src/servers/replenishment/data/suppliers.json');
  try {
    const raw = fs.readFileSync(filePath, 'utf-8');
    const parsed: RawSuppliersFile = JSON.parse(raw);
    return parsed.suppliers.map(s => ({
      id: s.id,
      name: s.name,
      category: s.category === 'grocery' ? 'groceries' : s.category,
      costPerUnit: s.costPerUnit,
      leadTimeDays: s.leadTimeDays,
      minOrderQty: s.minOrderQty,
      reliability: s.reliability,
    }));
  } catch (err) {
    console.error('[PROCUREMENT] Failed to load suppliers.json:', err instanceof Error ? err.message : String(err));
    return [];
  }
}

function generatePoId(): string {
  const now = new Date();
  const date = now.toISOString().slice(0, 10).replace(/-/g, '');
  const time = now.toTimeString().slice(0, 8).replace(/:/g, '');
  const rand = Math.floor(Math.random() * 900 + 100).toString();
  return `PO-${date}-${time}-${rand}`;
}

function simulateLogistics(reorderQty: number): LogisticsEvent | undefined {
  const roll = Math.random();
  if (roll < 0.05) {
    // 5%: rejected
    return { type: 'rejected' };
  } else if (roll < 0.15) {
    // 10%: partial (5-15% range)
    return {
      type: 'partial',
      qty: Math.floor(reorderQty * 0.6),
    };
  } else if (roll < 0.35) {
    // 20%: delayed
    const resolution = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();
    return { type: 'delayed', estimatedResolution: resolution };
  } else {
    return undefined;
  }
}

export class ProcurementAgent {
  private suppliers: Supplier[];
  private prisma: PrismaClient;

  constructor() {
    this.suppliers = loadSuppliers();
    this.prisma = new PrismaClient();
  }

  async run(params: {
    category: string;
    productId: string;
    productName: string;
    reorderQty: number;
    score: CompositeScore;
    blacklistedSupplierIds?: string[];
  }): Promise<PurchaseOrder | null> {
    const { category, productId, productName, reorderQty, blacklistedSupplierIds = [] } = params;

    // Filter suppliers by category, excluding blacklisted
    const eligible = this.suppliers.filter(
      s =>
        s.category === category &&
        !blacklistedSupplierIds.includes(s.id)
    );

    if (eligible.length === 0) {
      console.error(`[PROCUREMENT] No eligible suppliers for category '${category}'`);
      return null;
    }

    // Normalize cost for scoring
    const maxCost = Math.max(...eligible.map(s => s.costPerUnit));

    // Score each supplier
    const scored = eligible.map(s => {
      const normalizedCost = maxCost > 0 ? s.costPerUnit / maxCost : 1;
      const supplierScore =
        0.5 / s.leadTimeDays +
        0.3 * s.reliability +
        0.2 * (1 - normalizedCost);
      return { supplier: s, supplierScore };
    });

    // Select highest-scored supplier
    scored.sort((a, b) => b.supplierScore - a.supplierScore);
    const { supplier } = scored[0];

    const poId = generatePoId();
    const totalValue = reorderQty * supplier.costPerUnit;
    const createdAt = new Date().toISOString();

    // Simulate logistics event
    const logisticsEvent = simulateLogistics(reorderQty);

    // Determine status
    let status: PurchaseOrder['status'];
    if (logisticsEvent?.type === 'rejected') {
      status = 'rejected';
    } else if (logisticsEvent?.type === 'partial') {
      status = 'partial';
    } else if (logisticsEvent?.type === 'delayed') {
      status = 'delayed';
    } else if (totalValue > 50000) {
      status = 'pending_approval';
    } else {
      status = 'auto_approved';
    }

    // If pending_approval due to value, insert into ReviewQueue
    if (totalValue > 50000 && !logisticsEvent) {
      try {
        await this.prisma.reviewQueue.create({
          data: {
            type: 'po',
            payload: JSON.stringify({ poId, productId, productName, supplierId: supplier.id, supplierName: supplier.name, qty: reorderQty, totalValue }),
            status: 'pending',
          },
        });
        console.error(`[PROCUREMENT] PO ${poId} queued for review (value Rs.${totalValue.toFixed(0)} > 50000)`);
      } catch (err) {
        console.error('[PROCUREMENT] Failed to insert ReviewQueue entry:', err instanceof Error ? err.message : String(err));
      }
    }

    const po: PurchaseOrder = {
      id: poId,
      productId,
      productName,
      supplierId: supplier.id,
      supplierName: supplier.name,
      category,
      qty: logisticsEvent?.type === 'partial' ? (logisticsEvent.qty ?? reorderQty) : reorderQty,
      totalValue,
      status,
      logisticsEvent,
      createdAt,
    };

    // Write PO JSON to disk
    const poDir = path.resolve('data/purchase_orders');
    try {
      if (!fs.existsSync(poDir)) {
        fs.mkdirSync(poDir, { recursive: true });
      }
      fs.writeFileSync(path.join(poDir, `${poId}.json`), JSON.stringify(po, null, 2), 'utf-8');
    } catch (err) {
      console.error(`[PROCUREMENT] Failed to write PO file for ${poId}:`, err instanceof Error ? err.message : String(err));
    }

    // Persist to PurchaseOrderLog via Prisma
    try {
      await this.prisma.purchaseOrderLog.create({
        data: {
          poId,
          supplierId: supplier.id,
          category,
          qty: po.qty,
          totalValue,
          status,
          logisticsEvent: logisticsEvent ? JSON.stringify(logisticsEvent) : undefined,
        },
      });
    } catch (err) {
      console.error('[PROCUREMENT] Failed to persist PurchaseOrderLog:', err instanceof Error ? err.message : String(err));
    }

    return po;
  }
}
