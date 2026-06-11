import { CompositeScore, ActionTier } from '../types.js';

export class CompositeScorer {
  score(params: {
    marginPct: number;
    forecastUnits: number;
    reorderQty: number;
    stockoutRisk: string;
    currentStock?: number;
  }): CompositeScore {
    const { marginPct, forecastUnits, stockoutRisk } = params;

    // marginScore: marginPct / 100, clamped to [0, 1]
    const marginScore = Math.min(Math.max(marginPct / 100, 0), 1);

    // volumeScore: forecastUnits / 500, capped at 1.0
    const volumeScore = Math.min(forecastUnits / 500, 1);

    // stockoutPenalty: high=1.0, medium=0.6, low=0.2
    let stockoutPenalty: number;
    switch (stockoutRisk) {
      case 'high':
        stockoutPenalty = 1.0;
        break;
      case 'medium':
        stockoutPenalty = 0.6;
        break;
      default:
        stockoutPenalty = 0.2;
        break;
    }

    // Weighted composite
    const finalScore =
      marginScore * 0.4 +
      volumeScore * 0.35 +
      stockoutPenalty * 0.25;

    // Tier assignment
    let actionTier: ActionTier;
    if (finalScore > 0.6) {
      actionTier = 'auto';
    } else if (finalScore >= 0.3) {
      actionTier = 'review';
    } else {
      actionTier = 'quarantine';
    }

    return {
      marginScore,
      volumeScore,
      stockoutPenalty,
      finalScore,
      actionTier,
    };
  }
}
