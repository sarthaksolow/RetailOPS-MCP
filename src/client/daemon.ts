import { AuditorAgent } from './agents/auditor.js';
import { CompositeScorer } from './agents/scorer.js';
import { ProcurementAgent } from './agents/procurement.js';
import { PricingAgent } from './agents/pricing.js';
import { RecoveryPlanner } from './agents/recovery.js';
import { ActionLedger } from './agents/ledger.js';
import { AgentCycleEvent } from './types.js';
import { EventEmitter } from 'node:events';
import { broadcastEvent } from './wsBus.js';

// Global event emitter - Agent C's WebSocket server subscribes to this
export const daemonEvents = new EventEmitter();

const CYCLE_MS = parseInt(process.env.AGENT_CYCLE_MS ?? '20000', 10);

function emit(event: AgentCycleEvent): void {
  daemonEvents.emit('agent_event', event);
  broadcastEvent(event);
  console.error(`[${event.agentId.toUpperCase()}] ${event.message}`);
}

async function runCycle(cycleNum: number): Promise<void> {
  emit({ agentId: 'daemon', level: 'info', message: `Cycle ${cycleNum} started`, ts: new Date().toISOString() });

  const ledger = new ActionLedger();
  const auditor = new AuditorAgent();
  const scorer = new CompositeScorer();
  const procurement = new ProcurementAgent();
  const pricing = new PricingAgent();
  const recovery = new RecoveryPlanner();

  try {
    // Step 1: Audit
    emit({ agentId: 'auditor', level: 'info', message: 'Running data audit...', ts: new Date().toISOString() });
    const auditResult = await auditor.run();
    emit({ agentId: 'auditor', level: 'action', message: `Cleaned ${auditResult.cleaned} rows, flagged ${auditResult.flagged}, fixed ${auditResult.anomaliesFixed} anomalies`, ts: new Date().toISOString() });
    ledger.add({
      agentId: 'auditor',
      actionType: 'data_clean',
      payload: { cleaned: auditResult.cleaned, flagged: auditResult.flagged, anomaliesFixed: auditResult.anomaliesFixed },
      undoPayload: {},
      outcome: 'success',
    });

    // Step 2-5: Score and act on each product from the clean sales data
    const products = getUniqueProducts(auditResult.rows);

    for (const product of products) {
      // Load catalog data for this product to get marginPct and currentPrice
      const catalogItem = await getCatalogItem(product.category);
      if (!catalogItem) continue;

      // Score
      const score = scorer.score({
        marginPct: catalogItem.marginPct,
        forecastUnits: product.totalQty,
        reorderQty: Math.ceil(product.totalQty * 1.2),
        stockoutRisk: product.totalQty < 50 ? 'high' : product.totalQty < 150 ? 'medium' : 'low',
      });
      emit({ agentId: 'scorer', level: 'info', message: `${product.product_name}: score=${score.finalScore.toFixed(2)} tier=${score.actionTier}`, ts: new Date().toISOString() });

      if (score.actionTier === 'quarantine') {
        emit({ agentId: 'scorer', level: 'warn', message: `${product.product_name} quarantined (low score)`, ts: new Date().toISOString() });
        continue;
      }

      // Procurement
      const reorderQty = Math.ceil(product.totalQty * 1.2);
      const po = await procurement.run({
        category: product.category,
        productId: product.product_id,
        productName: product.product_name,
        reorderQty,
        score,
      });
      if (po) {
        emit({
          agentId: 'procurement',
          level: 'action',
          message: `PO ${po.id} created for ${po.productName}: ${po.qty} units from ${po.supplierName} | status=${po.status}`,
          data: po as unknown as Record<string, unknown>,
          ts: new Date().toISOString(),
        });
        if (po.logisticsEvent) {
          emit({ agentId: 'procurement', level: 'warn', message: `Logistics event: ${po.logisticsEvent.type} for PO ${po.id}`, ts: new Date().toISOString() });
        }
        ledger.add({
          agentId: 'procurement',
          actionType: 'purchase_order',
          payload: po as unknown as Record<string, unknown>,
          undoPayload: { poId: po.id, action: 'cancel' },
          outcome: po.status === 'auto_approved' ? 'success' : 'pending',
        });
      }

      // Pricing
      const recommendedPrice = catalogItem.price * (1 + (score.finalScore - 0.5) * 0.3);
      const priceAction = await pricing.run({
        category: product.category,
        productId: catalogItem.id,
        productName: product.product_name,
        currentPrice: catalogItem.price,
        recommendedPrice,
        score,
        stockoutRisk: product.totalQty < 50 ? 'high' : product.totalQty < 150 ? 'medium' : 'low',
        marginPct: catalogItem.marginPct,
      });
      emit({
        agentId: 'pricing',
        level: priceAction.status === 'applied' ? 'action' : 'warn',
        message: `${priceAction.productName}: ${priceAction.status === 'applied' ? 'Price updated' : 'Price queued for review'} Rs.${priceAction.oldPrice} -> Rs.${priceAction.newPrice.toFixed(0)} (${(priceAction.delta * 100).toFixed(1)}%)`,
        ts: new Date().toISOString(),
      });
      ledger.add({
        agentId: 'pricing',
        actionType: 'price_update',
        payload: priceAction as unknown as Record<string, unknown>,
        undoPayload: { productId: priceAction.productId, restorePrice: priceAction.oldPrice },
        outcome: priceAction.status === 'applied' ? 'success' : 'pending',
      });
    }

    // Step 5: Recovery
    emit({ agentId: 'recovery', level: 'info', message: 'Checking for failed/delayed POs...', ts: new Date().toISOString() });
    const recoveryActions = await recovery.run();
    for (const action of recoveryActions) {
      emit({ agentId: 'recovery', level: 'action', message: action, ts: new Date().toISOString() });
      ledger.add({ agentId: 'recovery', actionType: 'recovery', payload: { description: action }, undoPayload: {}, outcome: 'success' });
    }

    // Step 6: Flush ledger
    await ledger.flush();
    emit({ agentId: 'ledger', level: 'info', message: `Cycle ${cycleNum} complete - ledger flushed`, ts: new Date().toISOString() });

  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    emit({ agentId: 'daemon', level: 'error', message: `Cycle ${cycleNum} error: ${msg}`, ts: new Date().toISOString() });
  }
}

function getUniqueProducts(rows: import('./types.js').SalesRow[]): Array<{ product_id: string; product_name: string; category: string; totalQty: number }> {
  const map = new Map<string, { product_id: string; product_name: string; category: string; totalQty: number }>();
  for (const row of rows) {
    const existing = map.get(row.product_id);
    if (existing) {
      existing.totalQty += row.quantity;
    } else {
      map.set(row.product_id, { product_id: row.product_id, product_name: row.product_name, category: row.category, totalQty: row.quantity });
    }
  }
  return Array.from(map.values()).filter(p => p.category && p.totalQty > 0);
}

async function getCatalogItem(category: string): Promise<{ id: string; price: number; marginPct: number } | null> {
  const { PrismaClient } = await import('@prisma/client');
  const prisma = new PrismaClient();
  try {
    const item = await prisma.catalogProduct.findFirst({ where: { category } });
    return item ? { id: item.id, price: item.price, marginPct: item.marginPct } : null;
  } finally {
    await prisma.$disconnect();
  }
}

// Main entry point
let cycleNum = 0;
console.error(`[DAEMON] RetailOps Autonomous Agent starting. Cycle interval: ${CYCLE_MS}ms`);

async function tick() {
  cycleNum++;
  await runCycle(cycleNum);
  setTimeout(tick, CYCLE_MS);
}

tick();
