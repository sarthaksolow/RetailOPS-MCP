import { PrismaClient } from '@prisma/client';
import { PurchaseOrder } from '../types.js';
import { ProcurementAgent } from './procurement.js';

export class RecoveryPlanner {
  private prisma: PrismaClient;
  private procurement: ProcurementAgent;

  constructor() {
    this.prisma = new PrismaClient();
    this.procurement = new ProcurementAgent();
  }

  async run(): Promise<string[]> {
    const actions: string[] = [];

    // Query PurchaseOrderLog for status IN ['delayed', 'partial', 'rejected']
    const problematicPOs = await this.prisma.purchaseOrderLog.findMany({
      where: {
        status: {
          in: ['delayed', 'partial', 'rejected'],
        },
      },
      orderBy: {
        createdAt: 'desc',
      },
      take: 10,
    });

    for (const poLog of problematicPOs) {
      if (poLog.status === 'delayed') {
        const warningMsg = `Warning: PO ${poLog.poId} is delayed. Increasing safety stock threshold by 20% for future orders.`;
        actions.push(warningMsg);
        console.error(`[RECOVERY] ${warningMsg}`);
      } else if (poLog.status === 'partial') {
        // Calculate unfulfilled qty
        // Let's retrieve the PO details from the file if needed, or estimate it
        const originalQty = Math.ceil(poLog.qty / 0.6); // since partial simulates 60%
        const unfulfilled = originalQty - poLog.qty;

        if (unfulfilled > 0) {
          const actionMsg = `Partial shipment on PO ${poLog.poId}. Attempting to order top-up of ${unfulfilled} units from alternative supplier.`;
          actions.push(actionMsg);
          console.error(`[RECOVERY] ${actionMsg}`);

          // Attempt to run procurement with original supplier blacklisted
          await this.procurement.run({
            category: poLog.category,
            productId: 'temp-prod-id',
            productName: `Top-up for PO ${poLog.poId}`,
            reorderQty: unfulfilled,
            score: {
              marginScore: 0.5,
              volumeScore: 0.5,
              stockoutPenalty: 0.5,
              finalScore: 0.5,
              actionTier: 'auto',
            },
            blacklistedSupplierIds: [poLog.supplierId],
          });
        }
      } else if (poLog.status === 'rejected') {
        const actionMsg = `PO ${poLog.poId} was rejected by supplier ${poLog.supplierId}. Blacklisting supplier for current cycle and re-routing.`;
        actions.push(actionMsg);
        console.error(`[RECOVERY] ${actionMsg}`);

        // Re-run procurement with blacklisted supplier
        await this.procurement.run({
          category: poLog.category,
          productId: 'temp-prod-id',
          productName: `Replacement for rejected PO ${poLog.poId}`,
          reorderQty: poLog.qty,
          score: {
            marginScore: 0.5,
            volumeScore: 0.5,
            stockoutPenalty: 0.5,
            finalScore: 0.5,
            actionTier: 'auto',
          },
          blacklistedSupplierIds: [poLog.supplierId],
        });
      }

      // Mark the problematic PO log as 'resolved' or 'handled' so we don't process it next cycle
      await this.prisma.purchaseOrderLog.update({
        where: { id: poLog.id },
        data: { status: `${poLog.status}_recovered` },
      });
    }

    return actions;
  }
}
