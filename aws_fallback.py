from datetime import datetime, timedelta
from utils import check_required_tags, get_aws_client
from auth import get_aws_client
from config import AWS_IDLE_MINUTES, AWS_CPU_THRESHOLD, NETWORK_THRESHOLD
import logging

# Configure logging
logger = logging.getLogger(__name__)

def has_low_usage_aws(instance_id):
    logger.info(f"Checking low usage for AWS instance: {instance_id}")
    ec2 = get_aws_client('ec2')
    cloudwatch = get_aws_client('cloudwatch')

    if not check_required_tags(ec2, instance_id):
        logger.warning(f"Instance {instance_id} does not have required tags.")
        return False

    now = datetime.utcnow()
    start = now - timedelta(minutes=AWS_IDLE_MINUTES)  # Use time-based check
    logger.info(f"Fetching metrics from {start} to {now} for instance: {instance_id}")

    metrics = ['CPUUtilization', 'NetworkIn', 'NetworkOut']
    for metric in metrics:
        logger.info(f"Checking metric: {metric}")
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/EC2',
            MetricName=metric,
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            StartTime=start,
            EndTime=now,
            Period=60,  # 1-minute granularity
            Statistics=['Maximum']  # Check maximum utilization
        )
        for dp in response.get('Datapoints', []):
            logger.info(f"Metric {metric} data point: {dp['Maximum']}")
            if metric == 'CPUUtilization' and dp['Maximum'] > AWS_CPU_THRESHOLD:
                logger.warning(f"Instance {instance_id} exceeds CPU threshold with usage: {dp['Maximum']}")
                return False
            elif metric in ['NetworkIn', 'NetworkOut'] and dp['Maximum'] > NETWORK_THRESHOLD:
                logger.warning(f"Instance {instance_id} exceeds network threshold with usage: {dp['Maximum']}")
                return False

    logger.info(f"Instance {instance_id} has low usage.")
    return True

def list_zombie_vms(aws_client, region):
    try:
        logger.info(f"Fetching instances in region: {region}")
        instances = aws_client.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])
        zombie_vms = []

        for reservation in instances.get("Reservations", []):
# Path to the GCP credentials file used for authentication
            for instance in reservation.get("Instances", []):
                instance_id = instance["InstanceId"]
                instance_name = next(
                    (tag["Value"] for tag in instance.get("Tags", []) if tag["Key"] == "Name"), "Unnamed"
                )
                logger.info(f"Checking instance: {instance_name} (ID: {instance_id})")

                if not check_required_tags(instance):
                    logger.info(f"Instance {instance_name} (ID: {instance_id}) does not have required tags.")
                    continue

                # Simulate low usage check (replace with actual logic)
                if is_low_usage(instance):
                    logger.info(f"Instance {instance_name} (ID: {instance_id}) is a zombie VM.")
                    zombie_vms.append(instance_name)

        logger.info(f"Zombie VMs in region {region}: {zombie_vms}")
        return zombie_vms
    except Exception as e:
        logger.error(f"Error listing zombie VMs: {e}")
        raise

def is_low_usage(instance):
    # Placeholder for actual low usage logic
    return True  # Simulate all instances as low usage for now
