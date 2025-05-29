from datetime import datetime, timedelta
from utils import check_required_tags
from config import AWS_CPU_THRESHOLD, VM_AGE_DAYS, CPU_CHECK_DAYS
import logging

# Configure logging
logger = logging.getLogger(__name__)

def get_instance_creation_time(ec2_client, instance_id):
    try:
        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        launch_time = response['Reservations'][0]['Instances'][0]['LaunchTime']
        return launch_time
    except Exception as e:
        logger.error(f"Error while fetching creation time for instance {instance_id}: {e}")
        return None

def has_low_usage_aws(instance_id, ec2_client, cloudwatch_client):
    logger.info(f"Checking low usage for AWS instance: {instance_id}")
    try:
        if not check_required_tags(ec2_client, instance_id):
            logger.warning(f"Instance {instance_id} does not have required tags.")
            return False

        # Check instance age
        creation_time = get_instance_creation_time(ec2_client, instance_id)
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
        now = datetime.utcnow()
        start = now - timedelta(days=CPU_CHECK_DAYS)
        logger.info(f"Fetching metrics from {start} to {now} for instance: {instance_id}")

        response = cloudwatch_client.get_metric_statistics(
            Namespace='AWS/EC2',
            MetricName='CPUUtilization',
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            StartTime=start,
            EndTime=now,
            Period=300,  # 5-minute granularity
            Statistics=['Maximum']
        )

        # Check if any data point exceeds the threshold
        for dp in response.get('Datapoints', []):
            logger.info(f"CPU utilization data point: {dp['Maximum']}")
            if dp['Maximum'] > AWS_CPU_THRESHOLD:
                logger.warning(f"Instance {instance_id} exceeds CPU threshold with usage: {dp['Maximum']}")
                return False

        logger.info(f"Instance {instance_id} has low CPU usage for the last {CPU_CHECK_DAYS} days.")
        return True

    except Exception as e:
        logger.error(f"Error in has_low_usage_aws: {e}")
        raise
