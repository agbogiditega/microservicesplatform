# syntax=docker/dockerfile:1.5
# AWS-maintained Node.js 20 runtime image (multi-arch), reliable for ECS builds
FROM public.ecr.aws/docker/library/node:20-bookworm-slim

ENV NODE_ENV=production \
    PORT=8080

WORKDIR /app

# Create non-root user
RUN useradd -m appuser

# Copy package manifests first for caching
COPY package*.json ./

# Install prod deps only
RUN npm ci --omit=dev

# Copy app
COPY . .

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

CMD ["npm", "start"]

