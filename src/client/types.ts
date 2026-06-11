/**
 * Types and interfaces for the RetailOps MCP Client.
 * Represents the workflow state, intermediate steps, and final results.
 * Ensure no em dashes (-) are used.
 */

export interface EnrichmentOutput {
  category: string;
  brand: string;
  description: string;
  alternatives: Record<string, any>[];
  narrative: string;
}

export interface ForecastOutput {
  category: string;
  days_ahead: number;
  base_forecast: number;
  final_forecast: number;
  seasonal_multiplier: number;
  event: string;
  narrative: string;
  forecast_data?: Record<string, any>;
}

export interface ReplenishmentOutput {
  reorder_qty: number;
  reorder_timing: string;
  stockout_risk: string;
  narrative: string;
  replenishment_data?: Record<string, any>;
}

export interface PricingOutput {
  recommended_price: number;
  current_price: number;
  price_change_pct: number;
  recommendation_type: string;
  narrative: string;
  pricing_data?: Record<string, any>;
}

export interface RetailOpsState {
  // Input parameters
  product_name: string;
  days_ahead: number;

  // Catalog Enrichment outputs
  category?: string;
  brand?: string;
  description?: string;
  alternatives?: Record<string, any>[];
  enrichment_narrative?: string;

  // Forecasting outputs
  forecast_data?: Record<string, any>;
  base_forecast?: number;
  final_forecast?: number;
  seasonal_multiplier?: number;
  event?: string;
  forecast_narrative?: string;

  // Replenishment outputs
  replenishment_data?: Record<string, any>;
  reorder_qty?: number;
  reorder_timing?: string;
  stockout_risk?: string;
  replenishment_narrative?: string;

  // Pricing outputs
  pricing_data?: Record<string, any>;
  current_price?: number;
  recommended_price?: number;
  price_change_pct?: number;
  recommendation_type?: string;
  pricing_narrative?: string;

  // Workflow tracking
  errors: string[];
  workflow_status: string; // e.g. "running", "completed", "failed_forecast", "failed_replenishment", "failed_pricing", etc.
  timestamp: string;
}

export interface WorkflowResult {
  product_name: string;
  category?: string;
  timestamp: string;
  status: string;
  enrichment: {
    category?: string;
    brand?: string;
    description?: string;
    narrative?: string;
  };
  forecast: {
    base?: number;
    final?: number;
    multiplier?: number;
    event?: string;
    narrative?: string;
  };
  replenishment: {
    reorder_qty?: number;
    timing?: string;
    risk?: string;
    narrative?: string;
  };
  pricing: {
    recommended_price?: number;
    current_price?: number;
    change_pct?: number;
    strategy?: string;
    narrative?: string;
  };
  errors: string[];
}
