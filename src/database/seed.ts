import { PrismaClient } from '@prisma/client';
import * as fs from 'fs/promises';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const prisma = new PrismaClient();

async function main() {
  console.error("Starting database seed...");

  try {
    const projectRoot = path.resolve(__dirname, '../..');
    const catalogPath = path.join(projectRoot, 'servers/catalog-enricher/data/product_catalog.json');
    const mappingsPath = path.join(projectRoot, 'servers/catalog-enricher/data/category_mappings.json');

    console.error(`Loading product catalog from: ${catalogPath}`);
    const catalogData = JSON.parse(await fs.readFile(catalogPath, 'utf8'));

    console.error(`Loading category mappings from: ${mappingsPath}`);
    const mappingsData = JSON.parse(await fs.readFile(mappingsPath, 'utf8'));

    // Seed CatalogProducts
    for (const [id, product] of Object.entries(catalogData)) {
      const prod = product as any;
      await prisma.catalogProduct.upsert({
        where: { id },
        update: {
          name: prod.name,
          brand: prod.brand,
          category: prod.category,
          price: prod.price,
          marginPct: prod.margin_pct,
          description: prod.description
        },
        create: {
          id,
          name: prod.name,
          brand: prod.brand,
          category: prod.category,
          price: prod.price,
          marginPct: prod.margin_pct,
          description: prod.description
        }
      });
    }
    console.error(`Seeded ${Object.keys(catalogData).length} products.`);

    // Seed CategoryMappings
    for (const [keyword, category] of Object.entries(mappingsData)) {
      const cat = category as string;
      await prisma.categoryMapping.upsert({
        where: { keyword },
        update: { category: cat },
        create: { keyword, category: cat }
      });
    }
    console.error(`Seeded ${Object.keys(mappingsData).length} category mappings.`);

    console.error("Database seed completed successfully.");
  } catch (error) {
    console.error("Error seeding database:", error);
    process.exit(1);
  } finally {
    await prisma.$disconnect();
  }
}

main();
