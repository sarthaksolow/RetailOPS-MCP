import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { PrismaClient } from "@prisma/client";
import { z } from "zod";
import * as dotenv from "dotenv";

dotenv.config();

const prisma = new PrismaClient();

const server = new McpServer({
  name: "catalog-enricher-server",
  version: "1.0.0"
});

/**
 * Call OpenRouter API using native fetch.
 * Returns null if API call fails or key is missing.
 */
async function callOpenRouter(prompt: string, maxTokens: number = 150, temperature: number = 0.7): Promise<string | null> {
  const apiKey = process.env.OPENROUTER_API_KEY;
  if (!apiKey) {
    console.error("Warning: OPENROUTER_API_KEY not found - running in local fallback mode");
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
        "X-Title": "RetailOPS Catalog Enricher"
      },
      body: JSON.stringify({
        model,
        messages: [{ role: "user", content: prompt }],
        max_tokens: maxTokens,
        temperature
      })
    });
    if (!response.ok) {
      console.error(`OpenRouter error response status: ${response.status}`);
      return null;
    }
    const data = await response.json() as any;
    const content = data?.choices?.[0]?.message?.content;
    return content ? content.trim() : null;
  } catch (error) {
    console.error("OpenRouter API call failed:", error);
    return null;
  }
}

server.tool(
  "enrichProduct",
  "Enrich product catalog data by cleaning, categorizing, and filling missing fields.",
  {
    input: z.object({
      product_name: z.string(),
      product_data: z.record(z.string(), z.any()).optional()
    })
  },
  async ({ input }) => {
    const { product_name: productName, product_data: productData } = input;
    const reasoning: string[] = [];

    // Step 1: Clean Name
    let cleanedName = productName.trim();
    cleanedName = cleanedName.replace(/\s+/g, " "); // Normalize whitespace
    const prefixes = ["New", "Best", "Premium", "Super"];
    for (const prefix of prefixes) {
      if (cleanedName.startsWith(prefix + " ")) {
        cleanedName = cleanedName.slice(prefix.length + 1);
      }
    }
    reasoning.push(`cleaned product name: '${productName}' -> '${cleanedName}'`);

    // Step 2: Categorize
    let category = productData?.category || null;
    if (category) {
      reasoning.push(`using existing category: ${category}`);
    } else {
      // 1. Check exact database match
      const exactMatch = await prisma.catalogProduct.findFirst({
        where: {
          name: {
            equals: cleanedName
          }
        }
      });
      if (exactMatch) {
        category = exactMatch.category;
        reasoning.push(`exact database match found: category is ${category}`);
      } else {
        // 2. Check keyword mappings in database
        const mappings = await prisma.categoryMapping.findMany();
        const match = mappings.find(m => cleanedName.toLowerCase().includes(m.keyword.toLowerCase()));
        if (match) {
          category = match.category;
          reasoning.push(`keyword database match found: category is ${category}`);
        } else {
          // 3. Fallback to OpenRouter zero-shot classification
          const categoryPrompt = `Categorize this product into one of these retail categories:
- electronics
- groceries
- fashion
- kitchen_appliances
- home_appliances
- beauty_personal_care
- sports_fitness
- general

Product name: ${cleanedName}

Respond with ONLY the category name, nothing else.`;
          
          const llmCategory = await callOpenRouter(categoryPrompt, 20, 0.1);
          const validCategories = ["electronics", "groceries", "fashion", "kitchen_appliances", "home_appliances", "beauty_personal_care", "sports_fitness", "general"];
          if (llmCategory && validCategories.includes(llmCategory.toLowerCase())) {
            category = llmCategory.toLowerCase();
            reasoning.push(`LLM categorized as: ${category}`);
          } else {
            // 4. Fallback to local rule-based category heuristics
            const nameLower = cleanedName.toLowerCase();
            if (["tv", "television", "screen", "laptop", "computer", "notebook", "phone", "smartphone", "mobile"].some(word => nameLower.includes(word))) {
              category = "electronics";
            } else if (["detergent", "soap", "shampoo", "pack"].some(word => nameLower.includes(word))) {
              category = "groceries";
            } else if (["shirt", "pants", "dress", "fashion"].some(word => nameLower.includes(word))) {
              category = "fashion";
            } else {
              category = "general";
            }
            reasoning.push(`fallback categorization: ${category}`);
          }
        }
      }
    }

    // Step 3: Extract Attributes
    // Extract Brand
    let brand = productData?.brand || null;
    if (!brand) {
      const words = cleanedName.split(" ");
      if (words.length > 0 && words[0]) {
        brand = words[0].charAt(0).toUpperCase() + words[0].slice(1).toLowerCase();
      } else {
        brand = "Unknown";
      }
    }

    // Extract Description
    let description = productData?.description || null;
    if (!description) {
      const descPrompt = `Generate a brief product description (1-2 sentences) for: ${cleanedName}\nBe concise and professional.`;
      const llmDesc = await callOpenRouter(descPrompt, 60, 0.7);
      if (llmDesc) {
        description = llmDesc;
      } else {
        description = `Product: ${cleanedName}`;
      }
    }

    // Extract size and weight
    const attributes: Record<string, any> = { ...(productData?.attributes || {}) };
    const weightRegex = /(\d+(?:\.\d+)?)\s*(kg|g|lb|oz)/i;
    const weightMatch = cleanedName.match(weightRegex);
    if (weightMatch && !attributes.weight) {
      attributes.weight = weightMatch[0];
    }
    const sizeRegex = /(\d+(?:\.\d+)?)\s*(ml|l|oz)/i;
    const sizeMatch = cleanedName.match(sizeRegex);
    if (sizeMatch && !attributes.size) {
      attributes.size = sizeMatch[0];
    }
    reasoning.push(`extracted brand: ${brand}, attributes: ${Object.keys(attributes).length} fields`);

    // Step 4: Missing Fields
    const missingFields: string[] = [];
    if (!productData?.category) missingFields.push("category");
    if (!productData?.brand) missingFields.push("brand");
    if (!productData?.description) missingFields.push("description");

    if (missingFields.length > 0) {
      reasoning.push(`missing fields: ${missingFields.join(", ")}`);
    } else {
      reasoning.push("all required fields present");
    }

    // Step 5: Find Alternatives
    let alternatives: any[] = [];
    const dbAlts = await prisma.catalogProduct.findMany({
      where: {
        category: category,
        name: {
          not: cleanedName
        },
        brand: {
          not: brand
        }
      },
      take: 3
    });
    alternatives = dbAlts.map(alt => ({
      name: alt.name,
      brand: alt.brand,
      category: alt.category,
      price: alt.price,
      margin: alt.marginPct
    }));

    if (alternatives.length === 0) {
      const altPrompt = `Given this product is out of stock, suggest 2-3 alternative products in the same category.
Product: ${cleanedName} (Category: ${category}, Brand: ${brand})

Respond with a JSON array of alternatives, each with: name, brand, reason.
Example: [{"name": "Surf Excel 2kg", "brand": "Surf Excel", "reason": "Similar detergent, same size"}]`;
      const llmAltsStr = await callOpenRouter(altPrompt, 200, 0.7);
      if (llmAltsStr) {
        try {
          let cleanJsonStr = llmAltsStr.trim();
          if (cleanJsonStr.startsWith("```")) {
            const lines = cleanJsonStr.split("\n");
            if (lines[0].startsWith("```json") || lines[0].startsWith("```")) {
              lines.shift();
            }
            if (lines[lines.length - 1].startsWith("```")) {
              lines.pop();
            }
            cleanJsonStr = lines.join("\n").trim();
          }
          const parsedAlts = JSON.parse(cleanJsonStr);
          if (Array.isArray(parsedAlts)) {
            alternatives = parsedAlts.slice(0, 3);
          }
        } catch (err) {
          console.error("Failed to parse LLM alternatives JSON:", err);
        }
      }
    }

    if (alternatives.length > 0) {
      reasoning.push(`found ${alternatives.length} alternative products`);
    } else {
      reasoning.push("no alternatives found");
    }

    // Step 6: Narrative Summary
    let narrative = "";
    const narrativePrompt = `You are a retail catalog expert. Summarize the product enrichment:

Product: ${cleanedName}
Category: ${category}
Brand: ${brand}
Description: ${description}
Missing fields filled: ${missingFields.join(", ")}
Alternatives found: ${alternatives.length}

Provide a concise summary (2-3 sentences) of the enrichment work done.`;
    const llmNarrative = await callOpenRouter(narrativePrompt, 150, 0.7);
    if (llmNarrative) {
      narrative = llmNarrative;
    } else {
      narrative = `Enriched product: ${cleanedName}. Category: ${category}, Brand: ${brand}. Found ${alternatives.length} alternatives.`;
    }

    const result = {
      product_name: cleanedName,
      category,
      brand,
      description,
      attributes,
      missing_fields: missingFields,
      alternatives,
      narrative,
      reasoning
    };

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
  console.error("Catalog Enricher MCP Server running on STDIO");
}

main().catch((error) => {
  console.error("Fatal error in main():", error);
  process.exit(1);
});
