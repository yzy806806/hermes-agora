/** AgoraAgentClient — discussion and task execution methods.
 *
 * Mixed into AgoraAgentClient prototype at import time.
 * Split from client.ts to keep each file under 80 lines.
 */
import { AgoraAgentClient } from './client';
import { MessageType } from './protocol';

// -- Discussion --

AgoraAgentClient.prototype.createMotion = function(this: AgoraAgentClient, title: string, desc = ''): void {
  this['_send'](MessageType.SPEAK, { title, description: desc });
};

AgoraAgentClient.prototype.speak = function(this: AgoraAgentClient, motionId: string, content: string): void {
  this['_send'](MessageType.SPEAK, { motion_id: motionId, content });
};

AgoraAgentClient.prototype.vote = function(this: AgoraAgentClient, motionId: string, choice: string): void {
  this['_send'](MessageType.VOTE, { motion_id: motionId, choice });
};

// -- Task Execution --

AgoraAgentClient.prototype.reportTaskStart = function(this: AgoraAgentClient, taskId: string): void {
  this['_send'](MessageType.TASK_STATUS, { task_id: taskId, status: 'running' });
};

AgoraAgentClient.prototype.reportTaskComplete = function(this: AgoraAgentClient, taskId: string, artifacts?: string[]): void {
  this['_send'](MessageType.TASK_COMPLETED, { task_id: taskId, artifacts });
};

AgoraAgentClient.prototype.reportTaskFailed = function(this: AgoraAgentClient, taskId: string, error = ''): void {
  this['_send'](MessageType.TASK_FAILED, { task_id: taskId, error });
};

// Type augmentation so TypeScript knows about these methods
declare module './client' {
  interface AgoraAgentClient {
    createMotion(title: string, desc?: string): void;
    speak(motionId: string, content: string): void;
    vote(motionId: string, choice: string): void;
    reportTaskStart(taskId: string): void;
    reportTaskComplete(taskId: string, artifacts?: string[]): void;
    reportTaskFailed(taskId: string, error?: string): void;
  }
}
