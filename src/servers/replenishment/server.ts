import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import * as dotenv from "dotenv";

dotenv.config();

const server = new McpServer({
  name: "replenishment-server",
  version: "1.0.0"
});

// Helper to log to stderr
function log(msg: string) {
  console.error(msg);
}

/**
 * Call OpenRouter API using native fetch.
 */
async function callOpenRouter(prompt: string, maxTokens: number = 120, temperature: number = 0.7): Promise<string | null> {
  const apiKey = process.env.OPENROUTER_API_KEY;
  if (!apiKey) {
    log("[REPLENISH] OPENROUTER_API_KEY not found - running in fallback mode");
    return null;
  }
  const model = process.env.OPENROUTER_MODEL || "meta-llama/llama-3.1-8b-instruct";
  try {
    const response = await fetch("https://openrouter.ai/api/v1/chat/completions", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${apiKey}`,
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "Replenishment Reasoning Engine"
      },
      body: JSON.stringify({
        model,
        messages: [{ role: "user", content: prompt }],
        max_tokens: maxTokens,
        temperature
      })
    });
    if (!response.ok) {
      log(`[REPLENISH] OpenRouter error response status: ${response.status}`);
      return null;
    }
    const data = await response.json() as any;
    const content = data?.choices?.[0]?.message?.content;
    return content ? content.trim() : null;
  } catch (error) {
    log(`[REPLENISH] OpenRouter API call failed: ${error}`);
    return null;
  }
}

server.tool(
  "getReplenishmentDecision",
  "Generate a replenishment decision using safety stock and runway calculations.",
  {
    input: z.object({
      category: z.string().optional(),
      forecast: z.object({
        demand_volatility: z.enum(["low", "medium", "high"]),
        event: z.object({
          name: z.string().nullable(),
          days_to_event: z.number().nullable()
        }),
        avg_daily_demand: z.number(),
        forecasted_demand: z.number()
      }),
      inventory: z.object({
        current_stock: z.number(),
        in_transit_stock: z.number()
      }),
      supplier: z.object({
        lead_time_days: z.number(),
        minimum_order_quantity: z.number()
      })
    })
  },
  async ({ input }) => {
    log(">>> MCP Tool called: getReplenishmentDecision");

    const { forecast, inventory, supplier } = input;
    const explanationFactors: string[] = [];

    // Node 1: Demand Risk Check
    const volatilityMap: Record<string, number> = { low: 1.1, medium: 1.25, high: 1.4 };
    const volatilityMult = volatilityMap[forecast.demand_volatility] || 1.25;
    explanationFactors.push(`demand volatility is ${forecast.demand_volatility}`);

    // Node 2: Festival Urgency Check
    let festivalMult = 1.0;
    if (forecast.event.days_to_event !== null && forecast.event.days_to_event <= supplier.lead_time_days) {
      festivalMult = 1.2;
      explanationFactors.push(`festival (${forecast.event.name}) is within supplier lead time`);
    }

    // Node 3: Inventory Runway Calculation
    const effectiveStock = inventory.current_stock + inventory.in_transit_stock;
    const stockRunwayDays = parseFloat((effectiveStock / forecast.avg_daily_demand).toFixed(1));

    // Node 4: Safety Stock Calculation
    const safetyStock = Math.round(forecast.avg_daily_demand * supplier.lead_time_days * volatilityMult * festivalMult);

    // Node 5: Reorder Decision
    const rawQty = Math.max(0, Math.floor(forecast.forecasted_demand + safetyStock - effectiveStock));
    let reorderQty = 0;
    if (rawQty > 0) {
      reorderQty = Math.max(rawQty, supplier.minimum_order_quantity);
    }

    // Node 6: Timing Risk Classification
    let reorderTiming = "defer";
    let stockoutRisk = "low";

    if (stockRunwayDays < supplier.lead_time_days) {
      reorderTiming = "immediate";
      stockoutRisk = "high";
    } else if (stockRunwayDays < 30) {
      reorderTiming = "soon";
      stockoutRisk = "medium";
    }

    explanationFactors.push(`stock runway is ${stockRunwayDays} days`);

    // Node 7: Narrative Generation
    const prompt = `You are a retail supply chain expert.

Decision:
- Reorder Quantity: ${reorderQty}
- Timing: ${reorderTiming}
- Stockout Risk: ${stockoutRisk}

Reasoning factors:
${explanationFactors.join(", ")}

Explain the replenishment decision in clear, store-manager friendly language.
Keep it concise (2-3 sentences).`;

    const llmNarrative = await callOpenRouter(prompt, 120, 0.7);
    const narrative = llmNarrative || 
      `Replenishment decision: reorder quantity of ${reorderQty} units is recommended with timing classified as ${reorderTiming} due to ${explanationFactors.join(", ")}.`;

    const result = {
      reorder_qty: reorderQty,
      reorder_timing: reorderTiming,
      stockout_risk: stockoutRisk,
      narrative
    };

    log("[REPLENISH] Decision generated successfully");
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(result)
        }
      ]
    };
  }
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  log("[REPLENISH] Replenishment MCP Server running on STDIO");
}

main().catch((error) => {
  log(`[REPLENISH] Fatal error in main(): ${error}`);
  process.exit(1);
});
