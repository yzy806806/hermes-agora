# Docker agent example — Node.js + @agora/agent-sdk
FROM node:20-slim

WORKDIR /app

# Install dependencies
COPY package.json ./
RUN npm install --production

# Copy agent code
COPY agent.js ./

# Agora connection (set at runtime)
ENV AGORA_URL=http://host.docker.internal:8765
ENV AGENT_ID=docker-agent-1
ENV AGENT_NAME="Docker Agent"
ENV AGENT_MODEL=gpt-4

# Non-root user for security
USER node

# Start agent
CMD ["node", "agent.js"]
