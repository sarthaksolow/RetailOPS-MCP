/**
 * RetailOps CLI - Command Line Interface
 * Easy command-line access to retail operations workflows in TypeScript.
 * Ensures no em dashes (-) are used.
 */

import { RetailOpsClient } from "./orchestrator.js";
import { WorkflowResult } from "./types.js";

function printBanner(): void {
  console.log("\n" + "=".repeat(70));
  console.log("🛍️  RetailOps MCP Client - CLI (TypeScript)");
  console.log("=".repeat(70) + "\n");
}

function printResult(result: WorkflowResult): void {
  console.log(`\n${"=".repeat(70)}`);
  console.log(`📊 RESULTS FOR: ${(result.category || "").toUpperCase()}`);
  console.log("=".repeat(70));

  const statusEmoji = result.status === "completed" ? "✅" : "⚠️";
  console.log(`\nStatus: ${statusEmoji} ${result.status}`);

  if (result.errors && result.errors.length > 0) {
    console.log("\n❌ Errors:");
    for (const error of result.errors) {
      console.log(`   - ${error}`);
    }
    return;
  }

  const forecast = result.forecast || {};
  console.log("\n📈 FORECAST:");
  console.log(`   Final Forecast: ${forecast.final} units`);
  console.log(`   Upcoming Event: ${forecast.event}`);

  const replenish = result.replenishment || {};
  console.log("\n📦 REPLENISHMENT:");
  console.log(`   Reorder Quantity: ${replenish.reorder_qty} units`);
  console.log(`   Timing: ${(replenish.timing || "").toUpperCase()}`);

  const pricing = result.pricing || {};
  const change = pricing.change_pct || 0;
  const arrow = change > 0 ? "↑" : change < 0 ? "↓" : "→";
  console.log("\n💰 PRICING:");
  console.log(`   Recommended Price: ₹${pricing.recommended_price} (${arrow} ${change}%)`);

  console.log(`\n${"=".repeat(70)}\n`);
}

function printBatchResults(results: WorkflowResult[]): void {
  console.log(`\n${"=".repeat(70)}`);
  console.log(`📊 BATCH RESULTS (${results.length} categories)`);
  console.log("=".repeat(70) + "\n");

  results.forEach((result, idx) => {
    const cat = (result.category || "unknown").toUpperCase().padEnd(20);
    const forecast = result.forecast?.final !== undefined ? String(result.forecast.final).padStart(8) : "N/A";
    const reorder = result.replenishment?.reorder_qty !== undefined ? String(result.replenishment.reorder_qty).padStart(6) : "N/A";
    const price = result.pricing?.recommended_price !== undefined ? `₹${result.pricing.recommended_price}` : "N/A";

    console.log(`${idx + 1}. ${cat} | Forecast: ${forecast} | Reorder: ${reorder} | Price: ${price}`);
  });

  console.log(`\n${"=".repeat(70)}\n`);
}

async function cmdAnalyze(category: string, days: number = 30): Promise<void> {
  printBanner();
  console.log(`🎯 Analyzing category: ${category}`);
  console.log(`📅 Forecast period: ${days} days`);

  const client = new RetailOpsClient();
  const result = await client.runFullWorkflow(category, days);

  printResult(result);
}

async function cmdBatch(categories: string[], days: number = 30): Promise<void> {
  printBanner();
  console.log(`🎯 Batch analyzing ${categories.length} categories`);
  console.log(`📅 Forecast period: ${days} days`);

  const client = new RetailOpsClient();
  const results = await client.runBatchWorkflow(categories, days);

  printBatchResults(results);
}

async function cmdForecast(category: string, days: number = 30): Promise<void> {
  printBanner();
  console.log(`🎯 Forecasting: ${category}`);
  console.log(`📅 Period: ${days} days`);

  const client = new RetailOpsClient();
  const forecast = await client.runForecastOnly(category, days);

  if (forecast.error) {
    console.log(`\n❌ Error: ${forecast.error}\n`);
    return;
  }

  console.log(`\n${"=".repeat(70)}`);
  console.log("📈 FORECAST RESULTS");
  console.log("=".repeat(70));
  console.log(`\nCategory: ${forecast.category}`);
  console.log(`Base Forecast: ${forecast.base_forecast} units`);
  console.log(`Final Forecast: ${forecast.final_forecast} units`);
  console.log(`Seasonal Multiplier: ${forecast.seasonal_multiplier}x`);
  console.log(`Event: ${forecast.event}`);
  console.log("\nNarrative:");
  console.log(forecast.narrative);
  console.log(`\n${"=".repeat(70)}\n`);
}

async function cmdJson(category: string, days: number = 30): Promise<void> {
  const client = new RetailOpsClient();
  const result = await client.runFullWorkflow(category, days);
  console.log(JSON.stringify(result, null, 2));
}

function printHelp(): void {
  console.log(`
🛍️  RetailOps CLI - Help (TypeScript)

USAGE:
    npm run cli <command> [options]

COMMANDS:
    analyze <category> [--days N]
        Run full workflow (forecast + replenishment + pricing) for a category
        Example: npm run cli analyze tv --days 30

    batch <cat1> <cat2> ... [--days N]
        Run full workflow for multiple categories in parallel
        Example: npm run cli batch tv laptop phone --days 30

    forecast <category> [--days N]
        Run forecast only (no replenishment or pricing)
        Example: npm run cli forecast electronics --days 30

    json <category> [--days N]
        Output results as JSON (useful for scripts)
        Example: npm run cli json tv --days 30 > output.json

    help
        Show this help message

OPTIONS:
    --days N            Forecast horizon in days (default: 30)

SUPPORTED CATEGORIES:
    - electronics
    - tv
    - laptop
    - phone
    - smartphones
    - kitchen_appliances
    - fashion
    - groceries

EXAMPLES:
    # Analyze TV category
    npm run cli analyze tv

    # Batch process multiple categories
    npm run cli batch electronics fashion groceries

    # Get 60-day forecast
    npm run cli forecast laptop --days 60

    # Output as JSON for automation
    npm run cli json phone --days 30 > phone_analysis.json

For more information, see: client/README.md
`);
}

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  if (args.length < 1) {
    printHelp();
    return;
  }

  const command = args[0].toLowerCase();

  try {
    if (command === "help") {
      printHelp();
      return;
    }

    if (command === "analyze") {
      if (args.length < 2) {
        console.log("❌ Error: Missing category");
        console.log("Usage: npm run cli analyze <category> [--days N]");
        return;
      }

      const category = args[1];
      let days = 30;

      const daysIdx = args.indexOf("--days");
      if (daysIdx !== -1 && daysIdx + 1 < args.length) {
        days = parseInt(args[daysIdx + 1], 10);
      }

      await cmdAnalyze(category, days);
      return;
    }

    if (command === "batch") {
      if (args.length < 2) {
        console.log("❌ Error: Missing categories");
        console.log("Usage: npm run cli batch <cat1> <cat2> ... [--days N]");
        return;
      }

      const rawCategories = args.slice(1);
      let days = 30;

      const daysIdx = rawCategories.indexOf("--days");
      let categories = rawCategories;

      if (daysIdx !== -1) {
        if (daysIdx + 1 < rawCategories.length) {
          days = parseInt(rawCategories[daysIdx + 1], 10);
        }
        categories = rawCategories.slice(0, daysIdx);
      }

      await cmdBatch(categories, days);
      return;
    }

    if (command === "forecast") {
      if (args.length < 2) {
        console.log("❌ Error: Missing category");
        console.log("Usage: npm run cli forecast <category> [--days N]");
        return;
      }

      const category = args[1];
      let days = 30;

      const daysIdx = args.indexOf("--days");
      if (daysIdx !== -1 && daysIdx + 1 < args.length) {
        days = parseInt(args[daysIdx + 1], 10);
      }

      await cmdForecast(category, days);
      return;
    }

    if (command === "json") {
      if (args.length < 2) {
        console.log("❌ Error: Missing category");
        console.log("Usage: npm run cli json <category> [--days N]");
        return;
      }

      const category = args[1];
      let days = 30;

      const daysIdx = args.indexOf("--days");
      if (daysIdx !== -1 && daysIdx + 1 < args.length) {
        days = parseInt(args[daysIdx + 1], 10);
      }

      await cmdJson(category, days);
      return;
    }

    console.log(`❌ Unknown command: ${command}`);
    console.log("Run 'npm run cli help' for usage information");

  } catch (e: any) {
    console.log(`\n❌ Error: ${e.message}`);
    if (e.stack) {
      console.error(e.stack);
    }
  }
}

main();
