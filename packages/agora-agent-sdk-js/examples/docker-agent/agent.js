/**
 * Example Docker agent using @agora/agent-sdk.
 *
 * Connects to Agora Coordinator, receives task assignments,
 * executes them, and reports results back.
 */
import { AgoraAgentClient } from '@agora/agent-sdk';

const client = new AgoraAgentClient({
  coordinatorUrl: process.env.AGORA_URL || 'http://localhost:8765',
  agentId: process.env.AGENT_ID || 'docker-agent-1',
  agentName: process.env.AGENT_NAME || 'Docker Agent',
  agentType: 'docker',
  capabilities: ['task-execution', 'code-review'],
  model: process.env.AGENT_MODEL || 'gpt-4',
});

// Handle task assignments from coordinator
client.on('task_assigned', async (task) => {
  console.log(`Task assigned: ${task.task_id} — ${task.title}`);
  await client.reportTaskStart(task.task_id);
  try {
    // Replace with real task execution logic
    const result = await executeTask(task);
    await client.reportTaskComplete(task.task_id, result);
    console.log(`Task ${task.task_id} completed`);
  } catch (err) {
    await client.reportTaskFailed(task.task_id, err.message);
    console.error(`Task ${task.task_id} failed:`, err.message);
  }
});

// Handle discussion messages
client.on('speech_added', (msg) => {
  console.log(`Discussion [${msg.motion_id}]: ${msg.content}`);
});

async function executeTask(task) {
  // Placeholder — implement your agent logic here
  return { artifacts: [], summary: `Completed: ${task.title}` };
}

// Start: register → connect → run event loop
try {
  await client.register();
  await client.connect();
  console.log('Docker agent connected to Agora');
  await client.run();
} catch (err) {
  console.error('Agent failed:', err);
  process.exit(1);
}
