from datetime import datetime, timedelta
import time
from google.cloud import monitoring_v3
from utils import check_required_tags
from config import GCP_IDLE_MINUTES, GCP_CPU_THRESHOLD, GCP_CREDS_PATH
from auth import get_gcp_client
import logging
import os

# Configure logging
logger = logging.getLogger(__name__)

def get_instance_name(compute, project_id, zone, target_instance_id):
    try:
        request = compute.instances().list(project=project_id, zone=zone)
        response = request.execute()
        for instance in response.get("items", []):
            if str(instance.get("id")) == str(target_instance_id):
                return instance.get("name")
    except Exception as e:
        logger.error(f"Error while fetching instance name for ID {target_instance_id}: {e}")
    return None

def has_low_usage_gcp(project_id, instance_id, zone):
    logger.info(f"Checking low usage for GCP instance: {instance_id} in zone: {zone}")
    try:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GCP_CREDS_PATH
        logger.info(f"Using GCP credentials from: {GCP_CREDS_PATH}")

        compute = get_gcp_client()
        instance_id_str = str(instance_id)

        if not check_required_tags(compute, project_id, zone, instance_id_str):
            logger.info(f"Instance {instance_id} does not have all required tags.")
            return False

        logger.info(f"Instance {instance_id} has all required tags.")

        client = monitoring_v3.MetricServiceClient()
        now = time.time()
        interval = monitoring_v3.TimeInterval({
            "end_time": {"seconds": int(now)},
            "start_time": {"seconds": int(now - GCP_IDLE_MINUTES * 60)},  # Use time-based check
        })

        cpu_filter = (
            f'metric.type="compute.googleapis.com/instance/cpu/utilization" '
            f'AND resource.labels.instance_id="{instance_id}"'
        )

        results = client.list_time_series(
            request={
                "name": f"projects/{project_id}",
                "filter": cpu_filter,
                "interval": interval,
                "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                "aggregation": {
                    "alignment_period": {"seconds": 60},
                    "per_series_aligner": monitoring_v3.Aggregation.Aligner.ALIGN_MAX,  # Check maximum utilization
                }
            }
        )

        points = [p for r in results for p in r.points]
        if not points or all(p.value.double_value < GCP_CPU_THRESHOLD / 100.0 for p in points):
            logger.info(f"Instance {instance_id} has low usage.")
            return True
    except Exception as e:
        logger.error(f"Error in has_low_usage_gcp: {e}")
        raise
    return False


# def delete_vm(compute, project_id, zone, instance_name):
#     try:
#         logger.info(f"Attempting to delete VM: {instance_name} in zone: {zone}, project: {project_id}")
#         operation = compute.instances().delete(
#             project=project_id,
#             zone=zone,
#             instance=instance_name
#         ).execute()
#         logger.info(f"Delete operation for VM {instance_name} started: {operation}")
#         return True
#     except Exception as e:
#         logger.error(f"Failed to delete VM {instance_name}: {e}")
#         return False
