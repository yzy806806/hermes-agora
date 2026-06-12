/** @agora/agent-sdk — Node.js SDK for connecting agents to Agora Coordinator.
 *
 * Public API surface — re-exports from client.ts, protocol.ts.
 * Importing client_methods.ts registers discussion/task methods on the prototype.
 */
import './client_methods'; // side-effect: adds methods to AgoraAgentClient.prototype

export { AgoraAgentClient, type AgentClientOptions } from './client';
export {
  MessageType,
  type WSMessage,
  type RegistrationResult,
  type MotionResult,
  type SpeechResult,
  type VoteResult,
  type TaskNode,
  type AgentConfig,
} from './protocol';

export const VERSION = '0.1.0';
