import logging
import json
import argparse
from datetime import datetime
from controller import FallbackController
from config import GCP_CREDS_PATH

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f'fallback_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def get_gcp_project_id():
    with open(GCP_CREDS_PATH, 'r') as f:
        creds = json.load(f)
        return creds.get("project_id")

# def parse_args():
#     parser = argparse.ArgumentParser(description="Run VM fallback detection across clouds")
#     return parser.parse_args()

def format_results(results):
    summary = {k: {"success": 0, "failed": 0, "total": 0} for k in results}
    for cloud, vms in results.items():
        print(f"\n{cloud.upper()} Results:")
        for vm_id, success, msg in vms:
            status = "SUCCESS" if success else "FAILED"
            print(f"{vm_id}: {status} - {msg}")
            summary[cloud]["total"] += 1
            summary[cloud]["success" if success else "failed"] += 1
    print("\nSummary:")
    for cloud, stats in summary.items():
        print(f"{cloud.upper()}: Total={stats['total']}, Success={stats['success']}, Failed={stats['failed']}")

def main():
    try:
        logger.info("Parsing arguments")
        # args = parse_args()
        logger.info("Starting fallback detection")

        project_id = get_gcp_project_id()
        logger.info(f"Using GCP project ID: {project_id}")

        controller = FallbackController()
        results = controller.execute_fallback(project_id)

        format_results(results)
        logger.info("Fallback detection completed")

    except Exception as e:
        logger.error(f"Failed to execute fallback detection: {str(e)}")
        raise

if __name__ == "__main__":
    main()
