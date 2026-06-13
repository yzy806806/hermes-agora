package agorasdk

import "fmt"

// ReportTaskStart notifies the coordinator that task execution has begun.
func (c *Client) ReportTaskStart(taskID string) error {
	msg := NewWSMessage(TaskStarted, map[string]any{
		"task_id": taskID,
	})
	if err := c.sendWS(msg); err != nil {
		return fmt.Errorf("report_task_start: %w", err)
	}
	return nil
}

// ReportTaskProgress reports task progress (0–100 percent).
func (c *Client) ReportTaskProgress(taskID string, pct int) error {
	msg := NewWSMessage(TaskProgress, map[string]any{
		"task_id":  taskID,
		"progress": pct,
	})
	if err := c.sendWS(msg); err != nil {
		return fmt.Errorf("report_task_progress: %w", err)
	}
	return nil
}

// ReportTaskComplete notifies the coordinator that a task finished successfully.
func (c *Client) ReportTaskComplete(taskID string, artifacts []string) error {
	msg := NewWSMessage(TaskCompleted, map[string]any{
		"task_id":   taskID,
		"artifacts": artifacts,
	})
	if err := c.sendWS(msg); err != nil {
		return fmt.Errorf("report_task_complete: %w", err)
	}
	return nil
}

// ReportTaskFailed notifies the coordinator that a task execution failed.
func (c *Client) ReportTaskFailed(taskID string, errMsg string) error {
	msg := NewWSMessage(TaskFailed, map[string]any{
		"task_id": taskID,
		"error":   errMsg,
	})
	if err := c.sendWS(msg); err != nil {
		return fmt.Errorf("report_task_failed: %w", err)
	}
	return nil
}
