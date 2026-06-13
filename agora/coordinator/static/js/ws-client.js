/* Phase 13.2c: WS client — WebSocket push with reconnection + offline indicator.
Features: exponential backoff, event queue, replay, status callbacks. */
import { resolve } from './ws-aliases.js';
const WS_BASE = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/dashboard`;
let socket = null, token = null, handlers = {};
let retryDelay = 1000, reconnectTimer = null;
const MAX_DELAY = 30000, MAX_QUEUE = 200;
let subscribed = [], eventQueue = [], status = 'offline';
const statusHandlers = new Set();

function setStatus(s) { if (s !== status) { status = s; statusHandlers.forEach(fn => fn(s)); } }

function connect(jwt) {
  token = jwt;
  if (socket) socket.close();
  setStatus('reconnecting');
  socket = new WebSocket(`${WS_BASE}?token=${encodeURIComponent(jwt)}`);
  socket.onopen = () => {
    retryDelay = 1000; setStatus('connected');
    if (subscribed.length) send({type:'SUBSCRIBE',payload:{channels:subscribed}});
    replayQueue();
  };
  socket.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data), r = resolve(msg.type);
      (handlers[msg.type]||[]).forEach(fn => fn(msg.payload));
      if (r !== msg.type) (handlers[r]||[]).forEach(fn => fn(msg.payload));
      (handlers['*']||[]).forEach(fn => fn(msg));
    } catch { /* ignore malformed */ }
  };
  socket.onclose = () => { setStatus('offline'); scheduleReconnect(); };
  socket.onerror = () => socket.close();
}

function scheduleReconnect() {
  if (reconnectTimer) return;
  setStatus('reconnecting');
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null; if (token) connect(token);
  }, retryDelay);
  retryDelay = Math.min(retryDelay * 2, MAX_DELAY);
}

function send(msg) {
  if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(msg));
  else if (eventQueue.length < MAX_QUEUE) eventQueue.push(msg);
}

function replayQueue() {
  const q = eventQueue.splice(0);
  q.forEach(msg => { if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(msg)); });
}

function subscribe(channels) {
  subscribed = [...new Set([...subscribed, ...channels])];
  send({type:'SUBSCRIBE',payload:{channels}});
}
function unsubscribe(channels) {
  subscribed = subscribed.filter(c => !channels.includes(c));
  send({type:'UNSUBSCRIBE',payload:{channels}});
}
function on(eventType, cb) {
  if (!handlers[eventType]) handlers[eventType] = new Set();
  handlers[eventType].add(cb);
  return () => { handlers[eventType]?.delete(cb); };
}
function onStatus(fn) { statusHandlers.add(fn); fn(status); return () => statusHandlers.delete(fn); }
function getStatus() { return status; }
function disconnect() {
  if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
  if (socket) socket.close();
  socket = null; token = null; handlers = {}; subscribed = [];
  eventQueue = []; setStatus('offline');
}

export const ws = { connect, disconnect, subscribe, unsubscribe, on, onStatus, getStatus };
