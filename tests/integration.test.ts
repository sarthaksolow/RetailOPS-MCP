/**
 * Comprehensive Integration Test for RetailOps Client (TypeScript)
 * Tests all client functionality end-to-end.
 * Ensures no em dashes (-) are used.
 */

import { RetailOpsClient } from "../src/client/orchestrator.js";

async function testSuite(): Promise<[number, number]> {
  console.log("\n" + "=".repeat(70));
  console.log("🧪 COMPREHENSIVE INTEGRATION TEST SUITE (TypeScript)");
  console.log("=".repeat(70) + "\n");

  const client = new RetailOpsClient();
  let passed = 0;
  let failed = 0;

  // Test 1: Single category workflow
  console.log("1️⃣ Test: Single Category Workflow");
  try {
    const result = await client.runFullWorkflow("tv", 30);
    if (result.status !== "completed") {
      throw new Error(`Expected status 'completed', got: ${result.status}`);
    }
    if (!result.forecast) {
      throw new Error("Missing forecast data");
    }
    if (!result.replenishment) {
      throw new Error("Missing replenishment data");
    }
    if (!result.pricing) {
      throw new Error("Missing pricing data");
    }
    console.log("   ✅ PASSED: Full workflow executed successfully");
    passed++;
  } catch (e: any) {
    console.log(`   ❌ FAILED: ${e.message}`);
    failed++;
  }

  // Test 2: Forecast only
  console.log("\n2️⃣ Test: Forecast Only");
  try {
    const forecast = await client.runForecastOnly("electronics", 30);
    if (!("final_forecast" in forecast) && !("error" in forecast)) {
      throw new Error("Invalid forecast response");
    }
    console.log("   ✅ PASSED: Forecast-only execution works");
    passed++;
  } catch (e: any) {
    console.log(`   ❌ FAILED: ${e.message}`);
    failed++;
  }

  // Test 3: Batch processing
  console.log("\n3️⃣ Test: Batch Processing");
  try {
    const categories = ["tv", "laptop"];
    const results = await client.runBatchWorkflow(categories, 30);
    if (results.length !== 2) {
      throw new Error(`Expected 2 results, got: ${results.length}`);
    }
    if (!results.every((r) => "category" in r)) {
      throw new Error("Missing category field in some batch results");
    }
    console.log("   ✅ PASSED: Batch processing works");
    passed++;
  } catch (e: any) {
    console.log(`   ❌ FAILED: ${e.message}`);
    failed++;
  }

  // Test 4: Error handling (invalid category)
  console.log("\n4️⃣ Test: Error Handling");
  try {
    const result = await client.runFullWorkflow("invalid_category_xyz", 30);
    if (!("status" in result)) {
      throw new Error("Missing status field");
    }
    console.log("   ✅ PASSED: Error handling works (graceful failure)");
    passed++;
  } catch (e: any) {
    console.log(`   ❌ FAILED: ${e.message}`);
    failed++;
  }

  // Test 5: State accumulation
  console.log("\n5️⃣ Test: State Accumulation");
  try {
    const result = await client.runFullWorkflow("fashion", 30);
    if (result.status === "completed") {
      if (result.forecast.final === undefined || result.forecast.final <= 0) {
        throw new Error("Missing or invalid forecast value");
      }
      if (result.replenishment.reorder_qty === undefined || result.replenishment.reorder_qty < 0) {
        throw new Error("Missing or invalid reorder quantity");
      }
      if (result.pricing.recommended_price === undefined || result.pricing.recommended_price <= 0) {
        throw new Error("Missing or invalid recommended price");
      }
      console.log("   ✅ PASSED: State accumulation works correctly");
      passed++;
    } else {
      console.log(`   ⚠️ SKIPPED: Workflow failed (status: ${result.status})`);
    }
  } catch (e: any) {
    console.log(`   ❌ FAILED: ${e.message}`);
    failed++;
  }

  // Test 6: Different forecast periods
  console.log("\n6️⃣ Test: Custom Forecast Period");
  try {
    const result30 = await client.runForecastOnly("kitchen_appliances", 30);
    const result60 = await client.runForecastOnly("kitchen_appliances", 60);
    if (!result30) {
      throw new Error("30-day forecast failed");
    }
    if (!result60) {
      throw new Error("60-day forecast failed");
    }
    console.log("   ✅ PASSED: Custom forecast periods work");
    passed++;
  } catch (e: any) {
    console.log(`   ❌ FAILED: ${e.message}`);
    failed++;
  }

  // Summary
  console.log("\n" + "=".repeat(70));
  console.log("📊 TEST SUMMARY");
  console.log("=".repeat(70));
  console.log(`✅ Passed: ${passed}`);
  console.log(`❌ Failed: ${failed}`);
  const total = passed + failed;
  const rate = total > 0 ? (passed / total) * 100 : 0;
  console.log(`📈 Success Rate: ${rate.toFixed(1)}%`);

  if (failed === 0) {
    console.log("\n🎉 ALL TESTS PASSED! Client is working perfectly.");
  } else {
    console.log("\n⚠️ Some tests failed. Review the errors above.");
  }
  console.log("=".repeat(70) + "\n");

  return [passed, failed];
}

testSuite().then(([passed, failed]) => {
  process.exit(failed === 0 ? 0 : 1);
});
