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
  name: "forecasting-server",
  version: "1.0.0"
});

// Paths to data files
const DATA_DIR = path.join(__dirname, "data");
const salesPath = path.join(DATA_DIR, "sales_history.csv");
const eventsPath = path.join(DATA_DIR, "events.json");
const surgePath = path.join(DATA_DIR, "surge_profile.json");

// Cache variables
let salesData: { date: string; category: string; sales: number }[] = [];
let events: { events: { name: string; date: string; multiplier: number }[] } = { events: [] };
let surgeProfiles: Record<string, Record<string, number>> = {};

// Helper to log to stderr
function log(msg: string) {
  console.error(msg);
}

// Load data files on startup
async function loadData() {
  try {
    log(`[FORECAST] Loading sales data from: ${salesPath}`);
    const csvContent = await fs.readFile(salesPath, "utf8");
    const lines = csvContent.split("\n");
    salesData = [];
    for (let i = 1; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;
      const parts = line.split(",");
      if (parts.length >= 3) {
        salesData.push({
          date: parts[0].trim(),
          category: parts[1].trim(),
          sales: parseFloat(parts[2].trim())
        });
      }
    }
    log(`[FORECAST] Sales loaded: ${salesData.length} rows`);

    log(`[FORECAST] Loading events from: ${eventsPath}`);
    events = JSON.parse(await fs.readFile(eventsPath, "utf8"));
    log(`[FORECAST] Events loaded: ${events.events?.length || 0} events`);

    log(`[FORECAST] Loading surge profiles from: ${surgePath}`);
    surgeProfiles = JSON.parse(await fs.readFile(surgePath, "utf8"));
    log(`[FORECAST] Surge profiles loaded: ${Object.keys(surgeProfiles).length} profiles`);
  } catch (error) {
    log(`[FORECAST] Error loading data files: ${error}`);
    process.exit(1);
  }
}

/**
 * Call OpenRouter API using native fetch.
 */
async function callOpenRouter(prompt: string, maxTokens: number = 180, temperature: number = 0.7): Promise<string | null> {
  const apiKey = process.env.OPENROUTER_API_KEY;
  if (!apiKey) {
    log("[FORECAST] OPENROUTER_API_KEY not found - running in fallback mode");
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
        "X-Title": "Forecasting MCP Server"
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
      log(`[FORECAST] OpenRouter error response status: ${response.status}`);
      return null;
    }
    const data = await response.json() as any;
    const content = data?.choices?.[0]?.message?.content;
    return content ? content.trim() : null;
  } catch (error: any) {
    clearTimeout(timeoutId);
    log(`[FORECAST] OpenRouter API call failed or timed out: ${error.message || error}`);
    return null;
  }
}

function calculateMovingAverage(category: string, days: number = 30): number | null {
  const filtered = salesData.filter(item => item.category.toLowerCase() === category.toLowerCase());
  if (filtered.length === 0) return null;
  
  const lastDays = filtered.slice(-days);
  const total = lastDays.reduce((sum, item) => sum + item.sales, 0);
  return parseFloat((total / lastDays.length).toFixed(2));
}

function getSeasonMultiplier(): { eventName: string | null; multiplier: number } {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  for (const e of events.events) {
    const eventDate = new Date(e.date);
    eventDate.setHours(0, 0, 0, 0);

    const diffTime = eventDate.getTime() - today.getTime();
    const daysUntil = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (daysUntil >= 0 && daysUntil <= 180) {
      return { eventName: e.name, multiplier: e.multiplier };
    }
  }
  return { eventName: null, multiplier: 1.0 };
}

function getHistoricalSurge(category: string, eventName: string | null): number {
  if (eventName && surgeProfiles[eventName]) {
    return surgeProfiles[eventName][category] ?? 1.0;
  }
  return 1.0;
}

server.tool(
  "getForecast",
  "Generate a sales forecast for a product category.",
  {
    category: z.string(),
    days_ahead: z.number().optional()
  },
  async ({ category, days_ahead }) => {
    const days = days_ahead ?? 30;
    log(`[FORECAST] getForecast called for category: ${category}, days_ahead: ${days}`);

    const base = calculateMovingAverage(category, days);
    if (base === null) {
      const result = { error: `No data found for category '${category}'.` };
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(result)
          }
        ]
      };
    }

    const { eventName, multiplier: seasonMult } = getSeasonMultiplier();
    const histMult = getHistoricalSurge(category, eventName);
    const finalForecast = parseFloat((base * seasonMult * histMult).toFixed(2));

    const prompt = `You are a senior retail forecasting expert.

Category: ${category}
Base Forecast: ${base}
Seasonal Multiplier: ${seasonMult}
Historical Festival Surge Factor: ${histMult}
Event: ${eventName || "None"}
Final Forecast: ${finalForecast}

Explain how these factors combined to produce the final forecast.
Keep it short, clear, and store-manager friendly.`;

    const llmNarrative = await callOpenRouter(prompt, 180, 0.7);
    const narrative = llmNarrative || 
      `The forecast for ${category} is based on a ${days}-day moving average baseline of ${base}. ` +
      (eventName 
        ? `Adjusting for the upcoming ${eventName} (seasonal multiplier: ${seasonMult}) and its historical surge factor of ${histMult}, the final forecast is estimated at ${finalForecast}.`
        : `With no major upcoming seasonal events in the next 180 days, the forecast maintains the baseline level of ${finalForecast}.`);

    const result = {
      category,
      base_forecast: base,
      seasonal_multiplier: seasonMult,
      historical_surge_factor: histMult,
      final_forecast: finalForecast,
      event: eventName,
      narrative
    };

    log("[FORECAST] Forecast generated successfully");
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
  log("[FORECAST] Forecasting MCP Server running on STDIO");
}

main().catch((error) => {
  log(`[FORECAST] Fatal error in main(): ${error}`);
  process.exit(1);
});
