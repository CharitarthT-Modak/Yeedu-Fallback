import os
import logging

# Configure logging
logger = logging.getLogger(__name__)

logger.info("Configuration module loaded.")

REQUIRED_TAGS = {
    "resource": "yeedu",
    "test": "fallback"
}

BASE_CRED_PATH = os.getenv("YEEDU_CRED_PATH", os.path.expanduser("~/Yeedu/creds"))
AWS_CREDS_PATH = os.path.join(BASE_CRED_PATH, "yeedu-aws-creds.json")
GCP_CREDS_PATH = os.path.join(BASE_CRED_PATH, "yeedu-gcp-creds.json")
AZURE_CREDS_PATH = os.path.join(BASE_CRED_PATH, "yeedu-azure-creds.json")

GCP_IDLE_MINUTES = 5
GCP_CPU_THRESHOLD = 5.0

AWS_IDLE_MINUTES = 5
AWS_CPU_THRESHOLD = 5.0

AZURE_IDLE_MINUTES = 5
AZURE_CPU_THRESHOLD = 5.0
