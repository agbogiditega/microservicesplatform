'use strict';
const express = require('express');

const SERVICE_NAME = process.env.SERVICE_NAME || 'auth-service';
const ENVIRONMENT = process.env.ENVIRONMENT || 'unknown';
const LOG_LEVEL = process.env.LOG_LEVEL || 'INFO';
const DB_ENDPOINT = process.env.DB_ENDPOINT || '';
const SQS_QUEUE_URL = process.env.SQS_QUEUE_URL || '';

// Must match ALB listener rules (e.g., /auth/*, /users/*, /billing/*, /notify/*)
const PREFIX = process.env.SERVICE_PREFIX || 'auth';

const app = express();

function healthPayload() {
  return {
    status: 'ok',
    service: SERVICE_NAME,
    environment: ENVIRONMENT,
    config: {
      hasDbEndpoint: Boolean(DB_ENDPOINT),
      hasSqsQueueUrl: Boolean(SQS_QUEUE_URL),
      logLevel: LOG_LEVEL
    }
  };
}

app.get('/', (_req, res) => {
  res.json({
    service: SERVICE_NAME,
    environment: ENVIRONMENT,
    prefix: `/${PREFIX}`,
    endpoints: ['/', '/health', `/${PREFIX}`, `/${PREFIX}/health`]
  });
});

app.get('/health', (_req, res) => {
  res.status(200).json(healthPayload());
});

app.get(`/${PREFIX}`, (_req, res) => {
  res.json({ service: SERVICE_NAME, environment: ENVIRONMENT, message: `Hello from ${SERVICE_NAME}` });
});

app.get(`/${PREFIX}/health`, (_req, res) => {
  res.status(200).json(healthPayload());
});

const port = parseInt(process.env.PORT || '8080', 10);
app.listen(port, '0.0.0.0', () => {
  console.log(`[${SERVICE_NAME}] listening on 0.0.0.0:${port} (env=${ENVIRONMENT}, prefix=/${PREFIX})`);
});
