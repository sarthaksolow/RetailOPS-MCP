import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import * as path from "node:path";
import * as fs from "node:fs";
import { fileURLToPath } from "node:url";
import { PrismaClient } from "@prisma/client";
import {
  RetailOpsState,
  WorkflowResult,
} from "./types.js";

const prisma = new PrismaClient();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export class MCPServerManager {
  private baseDir: string;
  private serverScripts: Record<string, string>;

  constructor() {
    // Determine the root directory relative to this script
    this.baseDir = path.resolve(__dirname, "../../");
    this.serverScripts = {
      enricher: path.join(this.baseDir, "dist", "servers", "catalog-enricher", "server.js"),
      forecasting: path.join(this.baseDir, "dist", "servers", "forecasting", "server.js"),
      replenishment: path.join(this.baseDir, "dist", "servers", "replenishment", "server.js"),
      pricing: path.join(this.baseDir, "dist", "servers", "pricing-strategy", "server.js"),
    };
  }

  private getServerConfig(serverName: string): { command: string; args: string[]; env: Record<string, string> } {
    const scriptPath = this.serverScripts[serverName];
    if (!scriptPath || !fs.existsSync(scriptPath)) {
      throw new Error(`Server script not found: ${scriptPath}`);
    }

    const env: Record<string, string> = {
      ...process.env,
      OPENROUTER_API_KEY: process.env.OPENROUTER_API_KEY || "",
    };

    return { command: "node", args: [scriptPath], env };
  }

  private async runWithClient<T>(serverName: string, fn: (client: Client) => Promise<T>): Promise<T> {
    const config = this.getServerConfig(serverName);

    const transport = new StdioClientTransport({
      command: config.command,
      args: config.args,
      env: config.env,
      stderr: "inherit",
    });

    const client = new Client({
      name: `RetailOpsClient-${serverName}`,
      version: "1.0.0",
    });

    try {
      await client.connect(transport);
      const result = await fn(client);
      return result;
    } finally {
      try {
        await transport.close();
      } catch (err) {
        // Ignore transport close errors
      }
    }
  }

  public async callEnrichment(productName: string): Promise<Record<string, any>> {
    console.error(`[CLIENT] Mappings: Calling Catalog Enricher for '${productName}'`);
    try {
      return await this.runWithClient("enricher", async (client) => {
        const response = await client.callTool({
          name: "enrichProduct",
          arguments: {
            input: {
              product_name: productName,
              product_data: {},
            },
          },
        });

        const resp = response as any;
        if (resp.isError) {
          const errMsg = resp.content?.[0]?.type === "text" ? resp.content[0].text : "Unknown MCP error";
          return { error: errMsg };
        }

        if (response && response.content) {
          for (const content of (response.content as any[])) {
            if (content.type === "text" && content.text) {
              try {
                const result = JSON.parse(content.text);
                console.error(`[CLIENT] Enriched: Mapped to category '${result.category}'`);
                return result;
              } catch (parseErr) {
                return { error: `Failed to parse MCP response: ${content.text}` };
              }
            }
          }
        }
        return { error: "No enrichment data received" };
      });
    } catch (e: any) {
      console.error(`[CLIENT] Enrichment error: ${e.message}`);
      return { error: e.message };
    }
  }

  public async callForecasting(category: string, daysAhead: number = 30): Promise<Record<string, any>> {
    console.error(`[CLIENT] Calling Forecasting Server for ${category}`);
    try {
      return await this.runWithClient("forecasting", async (client) => {
        const response = await client.callTool({
          name: "getForecast",
          arguments: {
            category,
            days_ahead: daysAhead,
          },
        });

        const resp = response as any;
        if (resp.isError) {
          const errMsg = resp.content?.[0]?.type === "text" ? resp.content[0].text : "Unknown MCP error";
          return { error: errMsg };
        }

        if (response && response.content) {
          for (const content of (response.content as any[])) {
            if (content.type === "text" && content.text) {
              try {
                const result = JSON.parse(content.text);
                console.error(`[CLIENT] Forecast received: ${result.final_forecast}`);
                return result;
              } catch (parseErr) {
                return { error: `Failed to parse MCP response: ${content.text}` };
              }
            }
          }
        }
        return { error: "No forecast data received" };
      });
    } catch (e: any) {
      console.error(`[CLIENT] Forecasting error: ${e.message}`);
      return { error: e.message };
    }
  }

  public async callReplenishment(
    forecastData: Record<string, any>,
    currentStock?: number,
    inTransit?: number
  ): Promise<Record<string, any>> {
    console.error(`[CLIENT] Calling Replenishment Server`);
    try {
      const inventoryLevels: Record<string, { current: number; inTransit: number }> = {
        tv: { current: 45, inTransit: 10 },
        laptop: { current: 25, inTransit: 5 },
        phone: { current: 80, inTransit: 20 },
        electronics: { current: 150, inTransit: 50 },
        fashion: { current: 350, inTransit: 50 },
        groceries: { current: 800, inTransit: 200 },
      };

      const category = forecastData.category || "general";
      const inv = inventoryLevels[category] || { current: 200, inTransit: 50 };

      const actualCurrent = currentStock !== undefined ? currentStock : inv.current;
      const actualInTransit = inTransit !== undefined ? inTransit : inv.inTransit;

      // Robustly parse the input structure which may come from the workflow or the stress test.
      const forecasted_demand = forecastData.forecasted_demand !== undefined 
        ? forecastData.forecasted_demand 
        : (forecastData.final_forecast !== undefined ? forecastData.final_forecast : 0);

      const avg_daily_demand = forecastData.avg_daily_demand !== undefined 
        ? forecastData.avg_daily_demand 
        : (forecasted_demand / 30);

      const demand_volatility = forecastData.demand_volatility !== undefined
        ? forecastData.demand_volatility
        : "medium";

      let eventName: string | null = null;
      let eventDays: number | null = null;

      if (forecastData.event) {
        if (typeof forecastData.event === "object") {
          eventName = forecastData.event.name || null;
          eventDays = forecastData.event.days_to_event !== undefined ? forecastData.event.days_to_event : null;
        } else if (typeof forecastData.event === "string") {
          eventName = forecastData.event;
          eventDays = 10;
        }
      }

      const replenishInput = {
        category,
        forecast: {
          forecasted_demand,
          avg_daily_demand,
          demand_volatility,
          event: {
            name: eventName,
            days_to_event: eventDays,
          },
        },
        inventory: {
          current_stock: actualCurrent,
          in_transit_stock: actualInTransit,
        },
        supplier: {
          lead_time_days: 10,
          minimum_order_quantity: 50,
        },
      };

      return await this.runWithClient("replenishment", async (client) => {
        const response = await client.callTool({
          name: "getReplenishmentDecision",
          arguments: {
            input: replenishInput,
          },
        });

        const resp = response as any;
        if (resp.isError) {
          const errMsg = resp.content?.[0]?.type === "text" ? resp.content[0].text : "Unknown MCP error";
          return { error: errMsg };
        }

        if (response && response.content) {
          for (const content of (response.content as any[])) {
            if (content.type === "text" && content.text) {
              try {
                const result = JSON.parse(content.text);
                console.error(`[CLIENT] Replenishment: ${result.reorder_qty} units`);
                return result;
              } catch (parseErr) {
                return { error: `Failed to parse MCP response: ${content.text}` };
              }
            }
          }
        }
        return { error: "No replenishment data received" };
      });
    } catch (e: any) {
      console.error(`[CLIENT] Replenishment error: ${e.message}`);
      return { error: e.message };
    }
  }

  public async callPricing(
    category: string,
    forecastedDemand: number,
    inventoryLevel?: number,
    currentPrice?: number
  ): Promise<Record<string, any>> {
    console.error(`[CLIENT] Calling Pricing Strategy Server`);
    try {
      const defaultPrices: Record<string, number> = {
        electronics: 9000,
        tv: 28000,
        laptop: 48000,
        phone: 16000,
        kitchen_appliances: 5500,
        fashion: 1500,
        groceries: 220,
      };

      const actualPrice = currentPrice !== undefined ? currentPrice : (defaultPrices[category] || 5000);
      const actualInventory = inventoryLevel !== undefined ? inventoryLevel : 100;

      const pricingInput = {
        category,
        current_price: actualPrice,
        forecasted_demand: forecastedDemand,
        inventory_level: actualInventory,
        target_profit_pct: 0,
      };

      return await this.runWithClient("pricing", async (client) => {
        const response = await client.callTool({
          name: "getPricingStrategy",
          arguments: {
            input: pricingInput,
          },
        });

        const resp = response as any;
        if (resp.isError) {
          const errMsg = resp.content?.[0]?.type === "text" ? resp.content[0].text : "Unknown MCP error";
          return { error: errMsg };
        }

        if (response && response.content) {
          for (const content of (response.content as any[])) {
            if (content.type === "text" && content.text) {
              try {
                const result = JSON.parse(content.text);
                console.error(`[CLIENT] Pricing: recommended ${result.recommended_price}`);
                return result;
              } catch (parseErr) {
                return { error: `Failed to parse MCP response: ${content.text}` };
              }
            }
          }
        }
        return { error: "No pricing data received" };
      });
    } catch (e: any) {
      console.error(`[CLIENT] Pricing error: ${e.message}`);
      return { error: e.message };
    }
  }
}

export class RetailOpsClient {
  private serverManager: MCPServerManager;

  constructor() {
    this.serverManager = new MCPServerManager();
  }

  private async enrichmentNode(state: RetailOpsState): Promise<RetailOpsState> {
    console.error(`[CLIENT] NODE 1: Catalog Enrichment for '${state.product_name}'`);
    const enrichResult = await this.serverManager.callEnrichment(state.product_name);

    if (enrichResult.error) {
      state.errors.push(`Enrichment: ${enrichResult.error}`);
      state.category = "general";
      return state;
    }

    state.category = enrichResult.category || "general";
    state.brand = enrichResult.brand || "Unknown";
    state.description = enrichResult.description || "";
    state.alternatives = enrichResult.alternatives || [];
    state.enrichment_narrative = enrichResult.narrative || "";
    return state;
  }

  private async forecastingNode(state: RetailOpsState): Promise<RetailOpsState> {
    const category = state.category || "general";
    console.error(`[CLIENT] NODE 2: Forecasting for category '${category}'`);

    const days = Number(state.days_ahead || 30);
    const forecastResult = await this.serverManager.callForecasting(category, days);

    if (forecastResult.error) {
      state.errors.push(`Forecasting: ${forecastResult.error}`);
      state.workflow_status = "failed_forecast";
      return state;
    }

    state.forecast_data = forecastResult;
    state.base_forecast = forecastResult.base_forecast || 0;
    state.final_forecast = forecastResult.final_forecast || 0;
    state.seasonal_multiplier = forecastResult.seasonal_multiplier || 1.0;
    state.event = forecastResult.event || "None";
    state.forecast_narrative = forecastResult.narrative || "";
    return state;
  }

  private async replenishmentNode(state: RetailOpsState): Promise<RetailOpsState> {
    console.error(`[CLIENT] NODE 3: Replenishment Decision`);
    if (state.workflow_status === "failed_forecast") {
      return state;
    }

    if (!state.forecast_data) {
      state.errors.push("Replenishment: Missing forecast data");
      state.workflow_status = "failed_replenishment";
      return state;
    }

    const replenishResult = await this.serverManager.callReplenishment(state.forecast_data);

    if (replenishResult.error) {
      state.errors.push(`Replenishment: ${replenishResult.error}`);
      state.workflow_status = "failed_replenishment";
      return state;
    }

    state.replenishment_data = replenishResult;
    state.reorder_qty = replenishResult.reorder_qty || 0;
    state.reorder_timing = replenishResult.reorder_timing || "unknown";
    state.stockout_risk = replenishResult.stockout_risk || "unknown";
    state.replenishment_narrative = replenishResult.narrative || "";
    return state;
  }

  private async pricingNode(state: RetailOpsState): Promise<RetailOpsState> {
    console.error(`[CLIENT] NODE 4: Pricing Strategy`);
    if (state.workflow_status.startsWith("failed")) {
      return state;
    }

    if (state.final_forecast === undefined) {
      state.errors.push("Pricing: Missing final forecast");
      state.workflow_status = "failed_pricing";
      return state;
    }

    const pricingResult = await this.serverManager.callPricing(
      state.category || "general",
      state.final_forecast
    );

    if (pricingResult.error) {
      state.errors.push(`Pricing: ${pricingResult.error}`);
      state.workflow_status = "failed_pricing";
      return state;
    }

    state.pricing_data = pricingResult;
    state.current_price = pricingResult.current_price || 0;
    state.recommended_price = pricingResult.recommended_price || 0;
    state.price_change_pct = pricingResult.price_change_pct || 0;
    state.recommendation_type = pricingResult.recommendation_type || "maintain";
    state.pricing_narrative = pricingResult.narrative || "";

    state.workflow_status = "completed";
    return state;
  }

  private async persistRunResult(state: RetailOpsState): Promise<void> {
    try {
      await prisma.analysisRun.create({
        data: {
          category: state.category || "general",
          status: state.workflow_status,
          errors: state.errors.length > 0 ? state.errors.join("; ") : null,
          forecast: state.final_forecast !== undefined ? {
            create: {
              category: state.category || "general",
              baseForecast: state.base_forecast || 0,
              finalForecast: state.final_forecast || 0,
              seasonalMultiplier: state.seasonal_multiplier || 1.0,
              event: state.event || "None",
              narrative: state.forecast_narrative || "",
            }
          } : undefined,
          replenishment: state.reorder_qty !== undefined ? {
            create: {
              category: state.category || "general",
              reorderQty: state.reorder_qty || 0,
              timing: state.reorder_timing || "unknown",
              risk: state.stockout_risk || "unknown",
              narrative: state.replenishment_narrative || "",
            }
          } : undefined,
          pricing: state.recommended_price !== undefined ? {
            create: {
              category: state.category || "general",
              recommendedPrice: state.recommended_price || 0,
              priceChangePct: state.price_change_pct || 0,
              strategy: state.recommendation_type || "maintain",
              narrative: state.pricing_narrative || "",
            }
          } : undefined
        }
      });
    } catch (dbError: any) {
      console.error(`[CLIENT] Failed to persist workflow run to database: ${dbError.message}`);
    }
  }

  public async runFullWorkflow(productName: string, daysAhead: number = 30): Promise<WorkflowResult> {
    console.error(`\n============================================================`);
    console.error(`🎯 Starting Full Workflow for '${productName}'`);
    console.error(`============================================================\n`);

    let state: RetailOpsState = {
      product_name: productName,
      days_ahead: daysAhead,
      errors: [],
      workflow_status: "running",
      timestamp: new Date().toISOString(),
    };

    try {
      state = await this.enrichmentNode(state);
      state = await this.forecastingNode(state);
      state = await this.replenishmentNode(state);
      state = await this.pricingNode(state);

      const result: WorkflowResult = {
        product_name: productName,
        category: state.category,
        timestamp: state.timestamp,
        status: state.workflow_status,
        enrichment: {
          category: state.category,
          brand: state.brand,
          description: state.description,
          narrative: state.enrichment_narrative,
        },
        forecast: {
          final: state.final_forecast,
          event: state.event,
          narrative: state.forecast_narrative,
        },
        replenishment: {
          reorder_qty: state.reorder_qty,
          timing: state.reorder_timing,
          narrative: state.replenishment_narrative,
        },
        pricing: {
          recommended_price: state.recommended_price,
          change_pct: state.price_change_pct,
          narrative: state.pricing_narrative,
        },
        errors: state.errors,
      };

      console.error(`\n============================================================`);
      console.error(`✅ Workflow Completed: ${result.status}`);
      console.error(`============================================================\n`);

      // Persist result to SQLite database
      await this.persistRunResult(state);

      return result;
    } catch (e: any) {
      console.error(`[CLIENT] Workflow failed: ${e.message}`);
      state.errors.push(e.message);
      state.workflow_status = "failed";

      // Persist partial results on failure
      await this.persistRunResult(state);

      return {
        product_name: productName,
        timestamp: state.timestamp,
        status: "error",
        enrichment: {},
        forecast: {},
        replenishment: {},
        pricing: {},
        errors: state.errors,
      };
    }
  }

  public async runForecastOnly(category: string, daysAhead: number = 30): Promise<Record<string, any>> {
    return await this.serverManager.callForecasting(category, daysAhead);
  }

  public async runBatchWorkflow(productNames: string[], daysAhead: number = 30): Promise<WorkflowResult[]> {
    console.error(`\n🔄 Running batch workflow for ${productNames.length} products`);
    const promises = productNames.map((name) => this.runFullWorkflow(name, daysAhead));
    return await Promise.all(promises);
  }
}
