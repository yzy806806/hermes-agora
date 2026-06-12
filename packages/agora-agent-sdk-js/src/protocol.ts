/** Protocol types for Agora Agent SDK — no server-side dependencies.
 *
 * Subset of coordinator-side models needed by agents.
 * Mirrors the Python SDK's protocol.py exactly.
 */

// -- WS Message Types --

export enum MessageType {
  // Agent → Coordinator
  REGISTER = 'REGISTER',
  SPEAK = 'SPEAK',
  VOTE = 'VOTE',
  HEARTBEAT = 'HEARTBEAT',
  TASK_STATUS = 'TASK_STATUS',
  TASK_COMPLETED = 'TASK_COMPLETED',
  TASK_FAILED = 'TASK_FAILED',
  // Coordinator → Agent
  WELCOME = 'WELCOME',
  SPEECH_ADDED = 'SPEECH_ADDED',
  VOTE_CONFIRMED = 'VOTE_CONFIRMED',
  TASK_ASSIGNED = 'TASK_ASSIGNED',
  HEARTBEAT_ACK = 'HEARTBEAT_ACK',
  ERROR = 'ERROR',
  DEVILS_ADVOCATE_REQUEST = 'DEVILS_ADVOCATE_REQUEST',
  DEVILS_ADVOCATE_RESPONSE = 'DEVILS_ADVOCATE_RESPONSE',
}

// -- Message Envelope --

export interface WSMessage {
  type: MessageType;
  payload: Record<string, unknown>;
}

// -- Result Types --

export interface RegistrationResult {
  agent_id: string;
  token: string;
  status: string;
  message?: string;
}

export interface MotionResult {
  motion_id: string;
  status: string;
}

export interface SpeechResult {
  speech_id: string;
  status: string;
}

export interface VoteResult {
  status: string;
}

// -- Task --

export interface TaskNode {
  task_id: string;
  title: string;
  description: string;
  parent_id?: string | null;
}

// -- Agent Config (from WELCOME) --

export interface AgentConfig {
  agent_id: string;
  capabilities: string[];
  model: string;
  [key: string]: unknown;
}
