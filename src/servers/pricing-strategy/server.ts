import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import * as fs from "fs/promises";
import * as path from "path";
import { fileURLToPath } from "url";
import * as dotenv from "dotenv";

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const server = new McpServer({
  name: "pricing-strategy-server",
  version: "1.0.0"
});

// Paths to config files
const DATA_DIR = path.join(__dirname, "data");
const elasticityPath = path.join(DATA_DIR, "price_elasticity.json");
const competitorPath = path.join(DATA_DIR, "competitor_prices.json");

// Cache variables
let elasticityData: Record<string, any> = {};
let competitorData: Record<string, any> = {};

// Helper to log to stderr
function log(msg: string) {
  console.error(msg);
}

// Load config files on startup
async function loadData() {
  try {
    log(`[PRICING] Loading elasticity parameters from: ${elasticityPath}`);
    elasticityData = JSON.parse(await fs.readFile(elasticityPath, "utf8"));
    log(`[PRICING] Elasticity parameters loaded: ${Object.keys(elasticityData).length} categories`);

    log(`[PRICING] Loading competitor prices from: ${competitorPath}`);
    competitorData = JSON.parse(await fs.readFile(competitorPath, "utf8"));
    log(`[PRICING] Competitor prices loaded: ${Object.keys(competitorData).length} categories`);
  } catch (error) {
    log(`[PRICING] Error loading config files: ${error}`);
    process.exit(1);
  }
}

/**
 * Call OpenRouter API using native fetch.
 */
async function callOpenRouter(prompt: string, maxTokens: number = 120, temperature: number = 0.7): Promise<string | null> {
  const apiKey = process.env.OPENROUTER_API_KEY;
  if (!apiKey) {
    log("[PRICING] OPENROUTER_API_KEY not found - running in fallback mode");
    return null;
  }
  const model = process.env.OPENROUTER_MODEL || "meta-llama/llama-3.1-8b-instruct";
  
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 seconds timeout
  
  try {
    const response = await fetch("https://openrouter.ai/api/v1/chat/completions", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${apiKey}`,
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "RetailOPS Pricing Strategy"
      },
      body: JSON.stringify({
        model,
        messages: [{ role: "user", content: prompt }],
        max_tokens: maxTokens,
        temperature
      }),
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    if (!response.ok) {
      log(`[PRICING] OpenRouter error response status: ${response.status}`);
      return null;
    }
    const data = await response.json() as any;
    const content = data?.choices?.[0]?.message?.content;
    return content ? content.trim() : null;
  } catch (error: any) {
    clearTimeout(timeoutId);
    log(`[PRICING] OpenRouter API call failed or timed out: ${error.message || error}`);
    return null;
  }
}

server.tool(
  "getPricingStrategy",
  "Generate pricing recommendations based on elasticity, inventory, and competitor pricing.",
  {
    input: z.object({
      category: z.string(),
      current_price: z.number(),
      forecasted_demand: z.number(),
      inventory_level: z.number(),
      target_profit_pct: z.number().optional()
    })
  },
  async ({ input }) => {
    log(`[PRICING] getPricingStrategy called for category: ${input.category}`);

    const cat = input.category;
    const price = input.current_price;
    const forecastedDemand = input.forecasted_demand;
    const inventoryLevel = input.inventory_level;

    const competitorPrice = competitorData[cat]?.competitor_avg_price ?? price;
    const inventoryRatio = inventoryLevel / Math.max(1, forecastedDemand);
    const explanationFactors: string[] = [];

    let newPrice = price;
    let recType = "maintain";

    // Pricing recommendation logic
    if (inventoryRatio > 2) {
      newPrice = price * 0.92;
      recType = "clearance";
      explanationFactors.push("excess inventory");
    } else if (inventoryRatio < 0.5) {
      newPrice = price * 1.05;
      recType = "premium";
      explanationFactors.push("low inventory");
    } else if (price > competitorPrice * 1.1) {
      newPrice = price * 0.95;
      recType = "competitive";
      explanationFactors.push("above competitor pricing");
    }

    const recommendedPrice = parseFloat(newPrice.toFixed(2));
    const priceChangePct = parseFloat((((newPrice - price) / price) * 100).toFixed(2));

    const prompt = `You are a retail pricing expert.

Category: ${cat}
Current Price: INR ${price}
Recommended Price: INR ${recommendedPrice}
Reason: ${explanationFactors.join(", ") || "maintain market positioning"}

Explain this pricing decision clearly in 2 sentences.`;

    const llmNarrative = await callOpenRouter(prompt, 120, 0.7);
    const narrative = llmNarrative || 
      `${recType} pricing recommended (${priceChangePct}% change) due to ${explanationFactors.join(", ") || "market alignment"}.`;

    const result = {
      category: cat,
      current_price: price,
      recommended_price: recommendedPrice,
      price_change_pct: priceChangePct,
      recommendation_type: recType,
      narrative
    };

    log("[PRICING] Pricing recommendations generated successfully");
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
  await loadData();
  const transport = new StdioServerTransport();
  await server.connect(transport);
  log("[PRICING] Pricing Strategy MCP Server running on STDIO");
}

main().catch((error) => {
  log(`[PRICING] Fatal error in main(): ${error}`);
  process.exit(1);
});
