import { PrismaClient } from '@prisma/client';
import { PriceAction, CompositeScore } from '../types.js';

export class PricingAgent {
  private prisma: PrismaClient;

  constructor() {
    this.prisma = new PrismaClient();
  }

  async run(params: {
    category: string;
    productId: string;
    productName: string;
    currentPrice: number;
    recommendedPrice: number;
    score: CompositeScore;
    stockoutRisk: string;
    marginPct: number;
  }): Promise<PriceAction> {
    const { category, productId, productName, currentPrice, recommendedPrice, score, stockoutRisk, marginPct } = params;

    const delta = (recommendedPrice - currentPrice) / currentPrice;
    const absDelta = Math.abs(delta);
    const ts = new Date().toISOString();

    const justification = `Stockout risk ${stockoutRisk.toUpperCase()} + margin ${marginPct.toFixed(0)}% + volume score ${score.volumeScore.toFixed(2)} -> recommended price change of ${(delta * 100).toFixed(1)}%`;

    let status: PriceAction['status'];
    if (absDelta > 0.15) {
      status = 'pending_approval';
      // Insert into ReviewQueue
      try {
        await this.prisma.reviewQueue.create({
          data: {
            type: 'price',
            payload: JSON.stringify({
              productId,
              productName,
              category,
              oldPrice: currentPrice,
              newPrice: recommendedPrice,
              delta,
              justification,
              status,
              createdAt: ts
            }),
            status: 'pending',
          }
        });
        console.error(`[PRICING] Price update for ${productName} queued for review (delta ${(delta * 100).toFixed(1)}% > 15%)`);
      } catch (err) {
        console.error('[PRICING] Failed to insert price review item:', err instanceof Error ? err.message : String(err));
      }
    } else {
      status = 'approved'; // applied
      // Update CatalogProduct price directly in SQLite
      try {
        await this.prisma.catalogProduct.upsert({
          where: { id: productId },
          update: { price: recommendedPrice },
          create: {
            id: productId,
            name: productName,
            brand: 'Generic',
            category,
            price: recommendedPrice,
            marginPct,
            description: productName,
          }
        });
        console.error(`[PRICING] Price updated for ${productName} Rs.${currentPrice} -> Rs.${recommendedPrice.toFixed(0)}`);
      } catch (err) {
        console.error('[PRICING] Failed to update catalog product price:', err instanceof Error ? err.message : String(err));
      }
    }

    return {
      productId,
      productName,
      category,
      oldPrice: currentPrice,
      newPrice: recommendedPrice,
      delta,
      justification,
      status: status === 'approved' ? 'applied' : 'pending_approval',
      createdAt: ts,
    };
  }
}
