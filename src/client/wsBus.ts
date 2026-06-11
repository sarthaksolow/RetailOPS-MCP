// Shared WebSocket broadcast bus - decouples daemon from server
import { EventEmitter } from 'node:events';

class WsBus extends EventEmitter {}
export const wsBus = new WsBus();

export function broadcastEvent(event: unknown): void {
  wsBus.emit('broadcast', event);
}
