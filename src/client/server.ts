import express from 'express';
import cors from 'cors';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createServer } from 'node:http';
import { WebSocketServer, WebSocket } from 'ws';
import { PrismaClient } from '@prisma/client';
import { RetailOpsClient } from './orchestrator.js';
import { wsBus } from './wsBus.js';

const prisma = new PrismaClient();
const client = new RetailOpsClient();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const httpServer = createServer(app);
const wss = new WebSocketServer({ server: httpServer });

const port = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// Static files - serve compiled dist/public first, fallback to src/public in dev
const distPublicPath = path.join(__dirname, '../public');
const srcPublicPath = path.join(__dirname, '../../src/public');
app.use(express.static(distPublicPath));
app.use(express.static(srcPublicPath));

// ---- WebSocket: broadcast daemon events to all connected clients ----
const clients = new Set<WebSocket>();

wsBus.on('broadcast', (event: unknown) => {
  const msg = JSON.stringify({ type: 'agent_event', data: event });
  for (const ws of clients) {
    if (ws.readyState === WebSocket.OPEN) ws.send(msg);
  }
});

wss.on('connection', (ws: WebSocket) => {
  clients.add(ws);
  console.error('[WS] Client connected. Total:', clients.size);

  // Replay last 50 ActionLog entries to newly connected client
  prisma.actionLog.findMany({
    orderBy: { createdAt: 'desc' },
    take: 50,
  }).then(logs => {
    const replay = JSON.stringify({ type: 'replay', data: logs.reverse() });
    if (ws.readyState === WebSocket.OPEN) ws.send(replay);
  }).catch(e => console.error('[WS] Replay error:', e));

  ws.on('message', async (raw: Buffer) => {
    try {
      const msg = JSON.parse(raw.toString()) as { type: string; id?: string; action?: string };
      if (msg.type === 'review_action' && msg.id && msg.action) {
        const { id, action } = msg;
        await prisma.reviewQueue.update({
          where: { id },
          data: { status: action },
        });
        const ack = JSON.stringify({ type: 'review_ack', data: { id, action } });
        for (const c of clients) {
          if (c.readyState === WebSocket.OPEN) c.send(ack);
        }
        console.error(`[WS] Review ${id} marked ${action}`);
      }
    } catch (e) {
      console.error('[WS] Message parse error:', e);
    }
  });

  ws.on('close', () => {
    clients.delete(ws);
    console.error('[WS] Client disconnected. Total:', clients.size);
  });

  ws.on('error', (err: Error) => {
    console.error('[WS] Client error:', err.message);
    clients.delete(ws);
  });
});

// ---- Existing REST routes ----

app.post('/api/analyze', async (req: express.Request, res: express.Response): Promise<void> => {
  try {
    const { product_name, days_ahead } = req.body as { product_name?: string; days_ahead?: number };
    if (!product_name) {
      res.status(400).json({ error: 'product_name is required' });
      return;
    }
    const days = days_ahead !== undefined ? Number(days_ahead) : 30;
    console.error(`[SERVER] Running workflow for product: "${product_name}" days_ahead: ${days}`);
    const result = await client.runFullWorkflow(product_name, days);
    res.json(result);
  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : String(error);
    console.error(`[SERVER] Error in POST /api/analyze: ${msg}`);
    res.status(500).json({ error: msg });
  }
});

app.get('/api/runs', async (req: express.Request, res: express.Response): Promise<void> => {
  try {
    const runs = await prisma.analysisRun.findMany({
      include: { forecast: true, replenishment: true, pricing: true },
      orderBy: { timestamp: 'desc' },
    });
    res.json(runs);
  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : String(error);
    console.error(`[SERVER] Error in GET /api/runs: ${msg}`);
    res.status(500).json({ error: msg });
  }
});

app.delete('/api/runs', async (req: express.Request, res: express.Response): Promise<void> => {
  try {
    console.error('[SERVER] Deleting all analysis runs from SQLite cache');
    await prisma.analysisRun.deleteMany();
    res.json({ message: 'All analysis runs deleted successfully' });
  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : String(error);
    console.error(`[SERVER] Error in DELETE /api/runs: ${msg}`);
    res.status(500).json({ error: msg });
  }
});

// ---- NEW: Review Queue ----

// GET /api/review-queue - returns all pending review items
app.get('/api/review-queue', async (req: express.Request, res: express.Response): Promise<void> => {
  try {
    const items = await prisma.reviewQueue.findMany({
      where: { status: 'pending' },
      orderBy: { createdAt: 'desc' },
    });
    const parsed = items.map(item => ({ ...item, payload: JSON.parse(item.payload) as unknown }));
    res.json(parsed);
  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : String(error);
    res.status(500).json({ error: msg });
  }
});

// POST /api/review/:id - approve or reject a review item (REST fallback for WS)
app.post('/api/review/:id', async (req: express.Request, res: express.Response): Promise<void> => {
  try {
    const { id } = req.params;
    const { action } = req.body as { action?: string };
    if (!action || !['approved', 'rejected'].includes(action)) {
      res.status(400).json({ error: 'action must be "approved" or "rejected"' });
      return;
    }
    const updated = await prisma.reviewQueue.update({ where: { id }, data: { status: action } });
    const ack = JSON.stringify({ type: 'review_ack', data: { id, action } });
    for (const c of clients) {
      if (c.readyState === WebSocket.OPEN) c.send(ack);
    }
    res.json(updated);
  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : String(error);
    res.status(500).json({ error: msg });
  }
});

// ---- NEW: Action Ledger ----

// GET /api/ledger - returns the last 100 action log entries
app.get('/api/ledger', async (req: express.Request, res: express.Response): Promise<void> => {
  try {
    const entries = await prisma.actionLog.findMany({
      orderBy: { createdAt: 'desc' },
      take: 100,
    });
    const parsed = entries.map(e => ({
      ...e,
      payload: JSON.parse(e.payload) as unknown,
      undoPayload: JSON.parse(e.undoPayload) as unknown,
    }));
    res.json(parsed);
  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : String(error);
    res.status(500).json({ error: msg });
  }
});

// POST /api/ledger/:id/undo - reverse a previously applied action
app.post('/api/ledger/:id/undo', async (req: express.Request, res: express.Response): Promise<void> => {
  try {
    const { id } = req.params;
    const entry = await prisma.actionLog.findUnique({ where: { id } });
    if (!entry) {
      res.status(404).json({ error: 'Ledger entry not found' });
      return;
    }
    if (entry.outcome === 'undone') {
      res.status(400).json({ error: 'Already undone' });
      return;
    }

    const undoPayload = JSON.parse(entry.undoPayload) as { productId?: string; restorePrice?: number; poId?: string };

    if (entry.actionType === 'price_update' && undoPayload.productId && undoPayload.restorePrice !== undefined) {
      await prisma.catalogProduct.update({
        where: { id: undoPayload.productId },
        data: { price: undoPayload.restorePrice },
      });
    } else if (entry.actionType === 'purchase_order' && undoPayload.poId) {
      await prisma.purchaseOrderLog.updateMany({
        where: { poId: undoPayload.poId },
        data: { status: 'cancelled' },
      });
    }

    await prisma.actionLog.update({ where: { id }, data: { outcome: 'undone' } });

    const event = JSON.stringify({ type: 'undo_ack', data: { id, actionType: entry.actionType } });
    for (const c of clients) {
      if (c.readyState === WebSocket.OPEN) c.send(event);
    }
    res.json({ success: true });
  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : String(error);
    res.status(500).json({ error: msg });
  }
});

// ---- NEW: Event Replay (REST fallback for clients that miss WS connection) ----

// GET /api/events/replay?since=<ISO8601> - returns events after the given timestamp
app.get('/api/events/replay', async (req: express.Request, res: express.Response): Promise<void> => {
  try {
    const since = req.query['since'] as string | undefined;
    const where = since ? { createdAt: { gte: new Date(since) } } : {};
    const events = await prisma.actionLog.findMany({
      where,
      orderBy: { createdAt: 'asc' },
      take: 50,
    });
    res.json(events);
  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : String(error);
    res.status(500).json({ error: msg });
  }
});

// ---- NEW: Agent Config ----

// GET /api/agent-config - returns all config keys as a flat key:value map
app.get('/api/agent-config', async (req: express.Request, res: express.Response): Promise<void> => {
  try {
    const configs = await prisma.agentConfig.findMany();
    const map: Record<string, string> = {};
    for (const c of configs) map[c.key] = c.value;
    res.json(map);
  } catch (error: unknown) {
    // Return empty map rather than 500 if table is empty or unreachable
    res.json({});
  }
});

// POST /api/agent-config - upsert a single config key
app.post('/api/agent-config', async (req: express.Request, res: express.Response): Promise<void> => {
  try {
    const { key, value } = req.body as { key?: string; value?: unknown };
    if (!key || value === undefined) {
      res.status(400).json({ error: 'key and value are required' });
      return;
    }
    await prisma.agentConfig.upsert({
      where: { key },
      update: { value: String(value) },
      create: { key, value: String(value) },
    });
    res.json({ key, value });
  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : String(error);
    res.status(500).json({ error: msg });
  }
});

// ---- Start ----

const startServer = (portToTry: number): void => {
  httpServer.listen(portToTry, () => {
    console.error(`[SERVER] RetailOps dashboard + WebSocket server listening on port ${portToTry}`);
    console.error(`[SERVER] HTTP:      http://localhost:${portToTry}`);
    console.error(`[SERVER] WebSocket: ws://localhost:${portToTry}`);
  });

  httpServer.on('error', (error: NodeJS.ErrnoException) => {
    if (error.code === 'EADDRINUSE') {
      console.error(`[SERVER] Port ${portToTry} in use. Trying ${portToTry + 1}...`);
      startServer(portToTry + 1);
    } else {
      console.error(`[SERVER] Server error: ${error.message}`);
    }
  });
};

startServer(Number(port));
