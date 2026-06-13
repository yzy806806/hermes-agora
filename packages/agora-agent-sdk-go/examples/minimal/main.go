package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	agorasdk "github.com/yzy806806/agora-agent-sdk-go"
)

// onTaskAssigned handles TASK_ASSIGNED: reports start, progress, completion.
func onTaskAssigned(client *agorasdk.Client, raw json.RawMessage) {
	var task agorasdk.TaskNode
	if err := json.Unmarshal(raw, &task); err != nil {
		log.Printf("decode task: %v", err)
		return
	}
	log.Printf("[TASK] assigned: %s (id=%s)", task.Title, task.TaskID)
	if err := client.ReportTaskStart(task.TaskID); err != nil {
		log.Printf("report start: %v", err)
		return
	}
	for pct := 25; pct <= 100; pct += 25 {
		time.Sleep(500 * time.Millisecond)
		log.Printf("[TASK] progress: %d%%", pct)
		if err := client.ReportTaskProgress(task.TaskID, pct); err != nil {
			log.Printf("report progress: %v", err)
			return
		}
	}
	if err := client.ReportTaskComplete(task.TaskID, []string{"output.txt"}); err != nil {
		log.Printf("report complete: %v", err)
		return
	}
	log.Printf("[TASK] completed: %s", task.TaskID)
}

func main() {
	coordinatorURL := os.Getenv("AGORA_URL")
	if coordinatorURL == "" {
		coordinatorURL = "http://localhost:8765"
	}
	config := agorasdk.AgentConfig{
		CoordinatorURL: coordinatorURL,
		AgentID:        "minimal-go-agent",
		AgentName:      "minimal-go-agent",
		AgentType:      "custom",
		Capabilities:   []string{"task-execution"},
		Model:          "demo",
	}
	client := agorasdk.NewClient(config)
	client.OnTaskAssigned = func(raw json.RawMessage) {
		onTaskAssigned(client, raw)
	}
	ctx, stop := signal.NotifyContext(context.Background(),
		syscall.SIGINT, syscall.SIGTERM)
	defer stop()
	log.Println("Registering with Agora Coordinator...")
	result, err := client.Register(ctx)
	if err != nil {
		log.Fatalf("register: %v", err)
	}
	log.Printf("Registered: agent_id=%s", result.AgentID)
	log.Println("Connecting via WebSocket...")
	if err := client.Connect(ctx); err != nil {
		log.Fatalf("connect: %v", err)
	}
	defer client.Disconnect()
	log.Println("Connected! Listening for events...")
	fmt.Println("Press Ctrl+C to disconnect.")
	if err := client.Run(ctx); err != nil {
		log.Printf("run: %v", err)
	}
	log.Println("Shutting down...")
}
