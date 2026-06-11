/* WebSocket client with auto-reconnect and exponential backoff */
const WS_BASE = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/dashboard`;

let socket = null;
let token = null;
let handlers = {};       // eventType → Set of callbacks
let retryDelay = 1000;   // start at 1s
const MAX_DELAY = 30000; // cap at 30s
let subscribed = [];     // channels to re-subscribe on reconnect
let reconnectTimer = null;

function connect(jwt) {
  token = jwt;
  if (socket) socket.close();
  socket = new WebSocket(`${WS_BASE}?token=${encodeURIComponent(jwt)}`);
  
  socket.onopen = () => {
    retryDelay = 1000;
    if (subscribed.length) {
      send({ type: 'SUBSCRIBE', payload: { channels: subscribed } });
    }
  };
  
  socket.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      const cbs = handlers[msg.type];
      if (cbs) cbs.forEach(fn => fn(msg.payload));
      // wildcard handler
      const all = handlers['*'];
      if (all) all.forEach(fn => fn(msg));
    } catch { /* ignore malformed */ }
  };
  
  socket.onclose = () => { scheduleReconnect(); };
  socket.onerror = () => { socket.close(); };
}

function scheduleReconnect() {
  if (reconnectTimer) return;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    if (token) connect(token);
  }, retryDelay);
  retryDelay = Math.min(retryDelay * 2, MAX_DELAY);
}

function send(msg) {
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(msg));
  }
}

function subscribe(channels) {
  subscribed = [...new Set([...subscribed, ...channels])];
  send({ type: 'SUBSCRIBE', payload: { channels } });
}

function unsubscribe(channels) {
  subscribed = subscribed.filter(c => !channels.includes(c));
  send({ type: 'UNSUBSCRIBE', payload: { channels } });
}

function on(eventType, callback) {
  if (!handlers[eventType]) handlers[eventType] = new Set();
  handlers[eventType].add(callback);
  return () => { handlers[eventType]?.delete(callback); };
}

function disconnect() {
  if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
  if (socket) socket.close();
  socket = null; token = null; handlers = {}; subscribed = [];
}

export const ws = { connect, disconnect, subscribe, unsubscribe, on };
