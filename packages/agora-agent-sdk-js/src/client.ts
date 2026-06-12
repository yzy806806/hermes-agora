/** AgoraAgentClient — lifecycle methods (register, connect, disconnect, run).
 *
 * Split from client.ts to keep each file under 80 lines.
 */
import { EventEmitter } from 'events';
import WebSocket from 'ws';
import { MessageType, WSMessage, RegistrationResult, TaskNode, AgentConfig } from './protocol';

export interface AgentClientOptions {
  coordinatorUrl: string;
  agentId: string;
  agentName: string;
  agentType?: string;
  capabilities?: string[];
  model?: string;
  agentToken?: string;
  heartbeatInterval?: number;
}

export class AgoraAgentClient extends EventEmitter {
  private _opts: Required<Omit<AgentClientOptions, 'agentToken'>> & { agentToken?: string };
  private _ws: WebSocket | null = null;
  private _connected = false;
  private _hbTimer: ReturnType<typeof setInterval> | null = null;
  private _agentConfig: AgentConfig | null = null;
  private _token = '';

  constructor(opts: AgentClientOptions) {
    super();
    this._opts = { agentType: 'docker', capabilities: [], model: 'unknown', heartbeatInterval: 30, ...opts };
    this._token = opts.agentToken ?? '';
  }

  get connected(): boolean { return this._connected; }
  get agentConfig(): AgentConfig | null { return this._agentConfig; }

  private get _wsUrl(): string {
    const base = this._opts.coordinatorUrl.replace(/^http/, 'ws');
    const q = this._token ? `?token=${this._token}` : '';
    return `${base}/ws/${this._opts.agentId}${q}`;
  }

  private _send(type: MessageType, payload: Record<string, unknown>): void {
    if (!this._ws || this._ws.readyState !== WebSocket.OPEN) return;
    this._ws.send(JSON.stringify({ type, payload }));
  }

  async register(): Promise<RegistrationResult> {
    const url = `${this._opts.coordinatorUrl}/api/v1/agents/register`;
    const body = { agent_id: this._opts.agentId, name: this._opts.agentName,
      agent_type: this._opts.agentType, capabilities: this._opts.capabilities, model: this._opts.model };
    const resp = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (!resp.ok) return { agent_id: this._opts.agentId, token: '', status: 'error', message: resp.statusText };
    const data = await resp.json() as Record<string, unknown>;
    this._token = (data.agent_token ?? '') as string;
    return { agent_id: data.agent_id as string, token: this._token, status: 'ok' };
  }

  connect(): void {
    this._ws = new WebSocket(this._wsUrl);
    this._ws.on('open', () => { this._connected = true; this._startHb(); this.emit('connected'); });
    this._ws.on('message', (raw: WebSocket.Data) => this._onMsg(raw));
    this._ws.on('close', () => { this._connected = false; this._stopHb(); this.emit('disconnected'); });
    this._ws.on('error', (err: Error) => this.emit('error', err));
  }
  private _onMsg(raw: WebSocket.Data): void {
    const msg = JSON.parse(raw.toString()) as WSMessage;
    if (msg.type === MessageType.TASK_ASSIGNED) this.emit('task_assigned', msg.payload as unknown as TaskNode);
    else if (msg.type === MessageType.SPEECH_ADDED) this.emit('discussion_message', msg.payload);
    else if (msg.type === MessageType.DEVILS_ADVOCATE_REQUEST) this.emit('devils_advocate_request', msg.payload);
    else if (msg.type === MessageType.WELCOME) this._agentConfig = msg.payload as unknown as AgentConfig;
    else if (msg.type === MessageType.ERROR) this.emit('error', msg.payload);
  }
  disconnect(): void { this._stopHb(); this._ws?.close(); this._ws = null; this._connected = false; }
  private _startHb(): void { this._hbTimer = setInterval(() => this._send(MessageType.HEARTBEAT, {}), this._opts.heartbeatInterval * 1000); }
  private _stopHb(): void { if (this._hbTimer) { clearInterval(this._hbTimer); this._hbTimer = null; } }
  run(): void { if (!this._connected) this.connect(); }

  // Discussion & task methods are in client_methods.ts (mixed in via prototype)
}
