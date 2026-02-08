import os
import socket
import logging
from fastapi import FastAPI
import boto3
from botocore.exceptions import BotoCoreError, ClientError

SERVICE_NAME = "auth-service"

def _configure_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")

_configure_logging()
log = logging.getLogger(SERVICE_NAME)

app = FastAPI(title=SERVICE_NAME)

def _tcp_check(host: str, port: int, timeout_s: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except OSError:
        return False

def _sqs_check(queue_url: str) -> bool:
    try:
        sqs = boto3.client("sqs", region_name=os.getenv("AWS_REGION"))
        sqs.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=["QueueArn"]
        )
        return True
    except (BotoCoreError, ClientError) as e:
        log.warning("SQS check failed: %s", e)
        return False

@app.get("/")
def root():
    return {
        "service": SERVICE_NAME,
        "environment": os.getenv("ENVIRONMENT", "unknown"),
        "log_level": os.getenv("LOG_LEVEL", "INFO")
    }

@app.get("/health")
def health():
    db_host = os.getenv("DB_HOST")
    db_port = int(os.getenv("DB_PORT", "5432"))
    queue_url = os.getenv("SQS_QUEUE_URL")

    checks = {}

    if db_host:
        checks["db_tcp"] = _tcp_check(db_host, db_port)
    else:
        checks["db_tcp"] = "skipped"

    if queue_url:
        checks["sqs_access"] = _sqs_check(queue_url)
    else:
        checks["sqs_access"] = "skipped"

    ok = all(v is True or v == "skipped" for v in checks.values())
    return {"status": "ok" if ok else "degraded", "checks": checks}

