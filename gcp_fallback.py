from datetime import datetime, timedelta
import time
from google.cloud import monitoring_v3
from utils import check_required_tags
from config import GCP_CPU_THRESHOLD, GCP_CREDS_PATH, VM_AGE_DAYS, CPU_CHECK_DAYS
import logging
import os

# Configure logging
logger = logging.getLogger(__name__)

def get_instance_creation_time(compute_client, project_id, zone, instance_id):
    try:
        # Use the correct method to get instance details
        request = compute_client.get(
            project=project_id,
            zone=zone,
            instance=instance_id
        )
        response = request
        creation_time = datetime.fromisoformat(response.creation_timestamp.replace('Z', '+00:00'))
        return creation_time
    except Exception as e:
        logger.error(f"Error while fetching creation time for instance {instance_id}: {e}")
        return None

def has_low_usage_gcp(project_id, instance_id, zone, compute_client):
    logger.info(f"Checking low usage for GCP instance: {instance_id} in zone: {zone}")
    try:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GCP_CREDS_PATH
        logger.info(f"Using GCP credentials from: {GCP_CREDS_PATH}")

        instance_id_str = str(instance_id)

        if not check_required_tags(compute_client, project_id, zone, instance_id_str):
            logger.info(f"Instance {instance_id} does not have all required tags.")
            return False

        # Check instance age
        creation_time = get_instance_creation_time(compute_client, project_id, zone, instance_id_str)
        if not creation_time:
            logger.error(f"Could not determine creation time for instance {instance_id}")
            return False

        instance_age = datetime.now(creation_time.tzinfo) - creation_time
        if instance_age.days < VM_AGE_DAYS:
            logger.info(f"Instance {instance_id} is {instance_age.days} days old.")
            logger.info(f"Instance {instance_id} is less than {VM_AGE_DAYS} days old. Skipping.")
            return False

        logger.info(f"Instance {instance_id} is {instance_age.days} days old. Checking CPU utilization.")

        # Get CPU metrics for the last 2 days
        client = monitoring_v3.MetricServiceClient()
        now = time.time()
        interval = monitoring_v3.TimeInterval({
            "end_time": {"seconds": int(now)},
            "start_time": {"seconds": int(now - CPU_CHECK_DAYS * 24 * 3600)},
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
                    "alignment_period": {"seconds": 300},  # 5-minute granularity
                    "per_series_aligner": monitoring_v3.Aggregation.Aligner.ALIGN_MAX,
                }
            }
        )

        points = [p for r in results for p in r.points]
        if not points or all(p.value.double_value < GCP_CPU_THRESHOLD / 100.0 for p in points):
            logger.info(f"Instance {instance_id} has low CPU usage for the last {CPU_CHECK_DAYS} days.")
            return True

        return False

    except Exception as e:
        logger.error(f"Error in has_low_usage_gcp: {e}")
        raise
