import { PrismaClient } from '@prisma/client';
import { ActionLedgerEntry } from '../types.js';
import crypto from 'node:crypto';

export class ActionLedger {
  private buffer: ActionLedgerEntry[];
  private prisma: PrismaClient;

  constructor() {
    this.buffer = [];
    this.prisma = new PrismaClient();
  }

  add(entry: Omit<ActionLedgerEntry, 'id' | 'ts'>): void {
    this.buffer.push({
      ...entry,
      id: crypto.randomUUID(),
      ts: new Date().toISOString(),
    });
  }

  async flush(): Promise<void> {
    if (this.buffer.length === 0) return;

    try {
      await this.prisma.actionLog.createMany({
        data: this.buffer.map(entry => ({
          id: entry.id,
          agentId: entry.agentId,
          actionType: entry.actionType,
          payload: JSON.stringify(entry.payload),
          undoPayload: JSON.stringify(entry.undoPayload),
          outcome: entry.outcome,
          createdAt: new Date(entry.ts),
        })),
      });
      console.error(`[LEDGER] Flushed ${this.buffer.length} entries to database`);
      this.buffer = [];
    } catch (err) {
      console.error('[LEDGER] Failed to flush action ledger entries:', err instanceof Error ? err.message : String(err));
    }
  }

  async undo(entryId: string): Promise<boolean> {
    try {
      const entry = await this.prisma.actionLog.findUnique({
        where: { id: entryId },
      });

      if (!entry) {
        console.error(`[LEDGER] Entry ${entryId} not found for undo`);
        return false;
      }

      if (entry.outcome === 'undone') {
        console.error(`[LEDGER] Entry ${entryId} already undone`);
        return false;
      }

      const undoPayload = JSON.parse(entry.undoPayload) as { productId?: string; restorePrice?: number; poId?: string };

      if (entry.actionType === 'price_update' && undoPayload.productId && undoPayload.restorePrice !== undefined) {
        await this.prisma.catalogProduct.update({
          where: { id: undoPayload.productId },
          data: { price: undoPayload.restorePrice },
        });
        console.error(`[LEDGER] Price rolled back to Rs.${undoPayload.restorePrice} for product ${undoPayload.productId}`);
      } else if (entry.actionType === 'purchase_order' && undoPayload.poId) {
        await this.prisma.purchaseOrderLog.updateMany({
          where: { poId: undoPayload.poId },
          data: { status: 'cancelled' },
        });
        console.error(`[LEDGER] PO ${undoPayload.poId} cancelled`);
      }

      await this.prisma.actionLog.update({
        where: { id: entryId },
        data: { outcome: 'undone' },
      });

      return true;
    } catch (err) {
      console.error(`[LEDGER] Failed to undo entry ${entryId}:`, err instanceof Error ? err.message : String(err));
      return false;
    }
  }
}
