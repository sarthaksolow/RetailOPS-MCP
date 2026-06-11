import express from "express";
import cors from "cors";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { PrismaClient } from "@prisma/client";
import { RetailOpsClient } from "./orchestrator.js";

const prisma = new PrismaClient();
const client = new RetailOpsClient();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const port = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// Serve static files from the compiled public directory
// For development, also fallback to serve from src/public if dist/public is not built yet
const distPublicPath = path.join(__dirname, "../public");
const srcPublicPath = path.join(__dirname, "../../src/public");

app.use(express.static(distPublicPath));
app.use(express.static(srcPublicPath));

// POST /api/analyze: runs full RetailOpsClient workflow
app.post("/api/analyze", async (req: express.Request, res: express.Response): Promise<void> => {
  try {
    const { product_name, days_ahead } = req.body;
    if (!product_name) {
      res.status(400).json({ error: "product_name is required" });
      return;
    }
    const days = days_ahead !== undefined ? Number(days_ahead) : 30;
    console.error(`[SERVER] Running workflow for product: "${product_name}" with days_ahead: ${days}`);
    const result = await client.runFullWorkflow(product_name, days);
    res.json(result);
  } catch (error: any) {
    console.error(`[SERVER] Error in POST /api/analyze: ${error.message}`);
    res.status(500).json({ error: error.message });
  }
});

// GET /api/runs: returns all runs with relations
app.get("/api/runs", async (req: express.Request, res: express.Response): Promise<void> => {
  try {
    const runs = await prisma.analysisRun.findMany({
      include: {
        forecast: true,
        replenishment: true,
        pricing: true,
      },
      orderBy: {
        timestamp: "desc",
      },
    });
    res.json(runs);
  } catch (error: any) {
    console.error(`[SERVER] Error in GET /api/runs: ${error.message}`);
    res.status(500).json({ error: error.message });
  }
});

// DELETE /api/runs: clears all analysis runs and cascade deletes cached records
app.delete("/api/runs", async (req: express.Request, res: express.Response): Promise<void> => {
  try {
    console.error("[SERVER] Deleting all analysis runs from SQLite cache");
    await prisma.analysisRun.deleteMany();
    res.json({ message: "All analysis runs deleted successfully" });
  } catch (error: any) {
    console.error(`[SERVER] Error in DELETE /api/runs: ${error.message}`);
    res.status(500).json({ error: error.message });
  }
});

app.listen(port, () => {
  console.error(`[SERVER] RetailOps dashboard server listening on port ${port}`);
});
