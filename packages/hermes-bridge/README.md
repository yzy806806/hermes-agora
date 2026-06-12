# Agora Hermes Bridge

Bridge daemon connecting Hermes agent profiles to Agora Coordinator.

## Installation

```bash
pip install agora-hermes-bridge
```

## Usage

```bash
agora-hermes-bridge --config hermes-bridge.yaml
```

## Configuration

Create a YAML config file:

```yaml
coordinator_url: http://localhost:8765
poll_interval: 10
profiles:
  - name: dev-merger
    capabilities: [coding, testing]
    model: claude-sonnet-4
  - name: reviewer
    agent_id: custom-reviewer-id
    capabilities: [code-review]
```
