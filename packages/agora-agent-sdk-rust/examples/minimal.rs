//! Minimal Agora agent example.
//!
//! Run with: cargo run --example minimal

use agora_agent_sdk::{AgentConfig, AgoraClient, AgoraError, EventHandler, TaskNode};
use async_trait::async_trait;

struct MinimalHandler;

#[async_trait]
impl EventHandler for MinimalHandler {
    async fn on_task_assigned(&self, task: TaskNode) {
        println!("[task] assigned: {} — {}", task.id, task.title);
    }

    async fn on_discussion_message(&self, motion_id: &str, content: &str) {
        println!("[discussion] {}: {}", motion_id, content);
    }

    async fn on_error(&self, error: AgoraError) {
        eprintln!("[error] {}", error);
    }
}

#[tokio::main]
async fn main() -> Result<(), AgoraError> {
    env_logger::init();

    let config = AgentConfig::new("ws://localhost:8000", "minimal-agent")
        .with_agent_type("custom")
        .with_capabilities(vec!["example".into()])
        .with_model("demo");

    let mut client = AgoraClient::new(config);

    println!("Registering with Coordinator...");
    let reg = client.register().await?;
    println!("Registered: agent_id={}", reg.agent_id);

    println!("Connecting WebSocket...");
    client.connect().await?;
    println!("Connected! Entering event loop (Ctrl-C to stop).");

    client.run(MinimalHandler).await?;

    client.disconnect().await?;
    println!("Disconnected.");
    Ok(())
}
