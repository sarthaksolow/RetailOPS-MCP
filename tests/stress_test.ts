import { MCPServerManager } from "../src/client/orchestrator.js";
import { PrismaClient } from "@prisma/client";
import * as dotenv from "dotenv";

dotenv.config();

const prisma = new PrismaClient();
const manager = new MCPServerManager();

async function runStressTest() {
  console.error("\n=============================================================");
  console.error("🧪 RUNNING SYNTHETIC STRESS TEST & LOGIC VALIDATION");
  console.error("=============================================================\n");

  let passed = 0;
  let failed = 0;

  // 1. Catalog Database Check
  console.error("1️⃣ Check: Catalog Seeding Status");
  try {
    const productsCount = await prisma.catalogProduct.count();
    const mappingsCount = await prisma.categoryMapping.count();
    console.error(`   - SQLite Catalog contains ${productsCount} products.`);
    console.error(`   - SQLite Category mappings contains ${mappingsCount} keywords.`);
    if (productsCount >= 5 && mappingsCount >= 10) {
      console.error("   ✅ PASSED: Database catalog seeded successfully.");
      passed++;
    } else {
      throw new Error(`Insufficient seeded data: products=${productsCount}, keywords=${mappingsCount}`);
    }
  } catch (err: any) {
    console.error(`   ❌ FAILED: Database catalog verify error: ${err.message}`);
    failed++;
  }

  // 2. Catalog Enrichment Logic Check
  console.error("\n2️⃣ Check: Catalog Enrichment Mapping & Alternatives");
  try {
    const enrichResult = await manager.callEnrichment("Samsung 55 inch TV");
    console.error(`   - Input: "Samsung 55 inch TV"`);
    console.error(`   - Mapped Category: "${enrichResult.category}"`);
    console.error(`   - Detected Brand: "${enrichResult.brand}"`);
    console.error(`   - Alternatives count: ${enrichResult.alternatives?.length || 0}`);
    
    if (enrichResult.alternatives && enrichResult.alternatives.length > 0) {
      console.error(`   - Top Alternative: "${enrichResult.alternatives[0].name}" by ${enrichResult.alternatives[0].brand}`);
    }

    if (enrichResult.category === "electronics" && enrichResult.brand === "Samsung" && enrichResult.alternatives?.length > 0) {
      console.error("   ✅ PASSED: Category mapping and alternatives lookup is correct.");
      passed++;
    } else {
      throw new Error(`Incorrect mapping: category=${enrichResult.category}, brand=${enrichResult.brand}, alts=${enrichResult.alternatives?.length}`);
    }
  } catch (err: any) {
    console.error(`   ❌ FAILED: Enrichment check error: ${err.message}`);
    failed++;
  }

  // 3. Forecasting Logic Check
  console.error("\n3️⃣ Check: Sales Forecasting (Moving Average Baseline)");
  try {
    const forecast = await manager.callForecasting("tv", 30);
    console.error(`   - Category: tv`);
    console.error(`   - Base Forecast (Moving Average): ${forecast.base_forecast} units`);
    console.error(`   - Seasonal Event: "${forecast.event}" (Multiplier: ${forecast.seasonal_multiplier}x)`);
    console.error(`   - Surge Profile Multiplier: ${forecast.historical_surge_factor}x`);
    console.error(`   - Final Demand Forecast: ${forecast.final_forecast} units`);

    if (forecast.base_forecast > 0 && forecast.final_forecast > 0) {
      console.error("   ✅ PASSED: Forecasting server parsed CSV and calculated SMA successfully.");
      passed++;
    } else {
      throw new Error(`Invalid forecast values: base=${forecast.base_forecast}, final=${forecast.final_forecast}`);
    }
  } catch (err: any) {
    console.error(`   ❌ FAILED: Forecasting check error: ${err.message}`);
    failed++;
  }

  // 4. Replenishment Reasoning Check (Safety Stock & Runway)
  console.error("\n4️⃣ Check: Inventory Replenishment Runways & Risks");
  try {
    // Scenario A: Overstocked / Low Risk
    // daily demand = 5, current + in-transit = 200, lead time = 10, MOQ = 50.
    // Runway = 200 / 5 = 40 days.
    const lowRiskInput = {
      forecasted_demand: 150,
      avg_daily_demand: 5,
      demand_volatility: "low",
      event: { name: "None", days_to_event: 100 }
    };
    const lowRiskResult = await manager.callReplenishment(lowRiskInput, 200, 50); // current: 200, transit: 50 -> 250
    console.error("   Scenario A: Current Stock: 200, In-Transit: 50 (Total: 250), Daily Demand: 5");
    console.error(`     - Reorder Qty: ${lowRiskResult.reorder_qty} units`);
    console.error(`     - Timing: "${lowRiskResult.reorder_timing}"`);
    console.error(`     - Stockout Risk: "${lowRiskResult.stockout_risk}"`);

    // Scenario B: High Stockout Risk
    // daily demand = 5, current + in-transit = 10, lead time = 10, MOQ = 50.
    // Runway = 10 / 5 = 2 days < lead time (10 days).
    const highRiskInput = {
      forecasted_demand: 150,
      avg_daily_demand: 5,
      demand_volatility: "high",
      event: { name: "Diwali", days_to_event: 4 }
    };
    const highRiskResult = await manager.callReplenishment(highRiskInput, 10, 0); // current: 10, transit: 0
    console.error("   Scenario B: Current Stock: 10, In-Transit: 0 (Total: 10), Daily Demand: 5, Lead Time: 10");
    console.error(`     - Reorder Qty: ${highRiskResult.reorder_qty} units`);
    console.error(`     - Timing: "${highRiskResult.reorder_timing}"`);
    console.error(`     - Stockout Risk: "${highRiskResult.stockout_risk}"`);

    if (lowRiskResult.reorder_qty === 0 && lowRiskResult.reorder_timing === "defer" && highRiskResult.reorder_qty >= 50 && highRiskResult.reorder_timing === "immediate") {
      console.error("   ✅ PASSED: Safety stock, runway days, and MoQ limits calculations are correct.");
      passed++;
    } else {
      throw new Error(`Replenishment logic error: lowRiskQty=${lowRiskResult.reorder_qty}, highRiskQty=${highRiskResult.reorder_qty}`);
    }
  } catch (err: any) {
    console.error(`   ❌ FAILED: Replenishment check error: ${err.message}`);
    failed++;
  }

  // 5. Pricing Logic Check (Markdown vs Markup vs Competitive)
  console.error("\n5️⃣ Check: Dynamic Pricing Adjustments");
  try {
    // Scenario A: Clearance Mode (inventory ratio > 2)
    // stock = 240, demand = 100 -> ratio = 2.4. Price = 1000. Expected: 8% discount (920).
    const clearanceResult = await manager.callPricing("electronics", 100, 240, 1000);
    console.error("   Scenario A: Clearance (Ratio: 2.4, Base Price: 1000)");
    console.error(`     - Recommended Price: ₹${clearanceResult.recommended_price} (${clearanceResult.price_change_pct}%)`);
    console.error(`     - Strategy: "${clearanceResult.recommendation_type}"`);

    // Scenario B: Premium Mode (inventory ratio < 0.5)
    // stock = 30, demand = 100 -> ratio = 0.3. Price = 1000. Expected: 5% markup (1050).
    const premiumResult = await manager.callPricing("electronics", 100, 30, 1000);
    console.error("   Scenario B: Premium (Ratio: 0.3, Base Price: 1000)");
    console.error(`     - Recommended Price: ₹${premiumResult.recommended_price} (${premiumResult.price_change_pct}%)`);
    console.error(`     - Strategy: "${premiumResult.recommendation_type}"`);

    // Scenario C: Competitive Adjustment
    // Our price = 28000, competitor average = 25000 (we're 12% higher). Price = 28000. Expected: 5% discount (26600).
    const competitiveResult = await manager.callPricing("tv", 100, 100, 28000);
    console.error("   Scenario C: Competitive Price Match (Competitor: 25000, Ours: 28000)");
    console.error(`     - Recommended Price: ₹${competitiveResult.recommended_price} (${competitiveResult.price_change_pct}%)`);
    console.error(`     - Strategy: "${competitiveResult.recommendation_type}"`);

    const isClearanceCorrect = clearanceResult.recommended_price === 920 && clearanceResult.recommendation_type === "clearance";
    const isPremiumCorrect = premiumResult.recommended_price === 1050 && premiumResult.recommendation_type === "premium";
    const isCompetitiveCorrect = competitiveResult.recommended_price === 26600 && competitiveResult.recommendation_type === "competitive";

    if (isClearanceCorrect && isPremiumCorrect && isCompetitiveCorrect) {
      console.error("   ✅ PASSED: Clearance, Premium, and Competitive pricing rules match spec formulas.");
      passed++;
    } else {
      throw new Error(`Pricing logic error: clearance=${clearanceResult.recommended_price}, premium=${premiumResult.recommended_price}, competitive=${competitiveResult.recommended_price}`);
    }
  } catch (err: any) {
    console.error(`   ❌ FAILED: Pricing check error: ${err.message}`);
    failed++;
  }

  // Summary
  console.error("\n=============================================================");
  console.error("📊 STRESS TEST SUMMARY");
  console.error("=============================================================");
  console.error(`✅ Passed: ${passed}`);
  console.error(`❌ Failed: ${failed}`);
  console.error(`📈 Logic Accuracy: ${(passed / (passed + failed) * 100).toFixed(1)}%`);
  if (failed === 0) {
    console.error("\n🎉 ALL LOGIC AND STRESS TESTS PASSED SUCCESSFULLY!");
  } else {
    console.error("\n⚠️ Some test assertions failed. Review log trace above.");
  }
  console.error("=============================================================\n");

  await prisma.$disconnect();
  process.exit(failed === 0 ? 0 : 1);
}

runStressTest().catch(async (e) => {
  console.error("Fatal error running stress test:", e);
  await prisma.$disconnect();
  process.exit(1);
});
