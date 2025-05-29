from datetime import datetime, timedelta
from azure.mgmt.monitor import MonitorManagementClient
from azure.identity import ClientSecretCredential
from utils import check_required_tags
from config import AZURE_CPU_THRESHOLD, VM_AGE_DAYS, CPU_CHECK_DAYS
import logging
from azure.mgmt.compute import ComputeManagementClient

# Configure logging
logger = logging.getLogger(__name__)

def get_vm_creation_time(compute_client, resource_group, vm_name):
    try:
        vm = compute_client.virtual_machines.get(resource_group, vm_name)
        return vm.time_created
    except Exception as e:
        logger.error(f"Error while fetching creation time for VM {vm_name}: {e}")
        return None

def has_low_usage_azure(vm_resource_id, compute_client, azure_creds):
    logger.info(f"Checking low usage for VM: {vm_resource_id}")
    try:
        parts = vm_resource_id.split('/')
        resource_group = parts[4]
        vm_name = parts[8]
        logger.info(f"Extracted resource group: {resource_group}, VM name: {vm_name}")

        if not check_required_tags(compute_client, vm_resource_id):
            logger.warning(f"VM {vm_resource_id} does not have required tags.")
            return False

        # Check VM age
        creation_time = get_vm_creation_time(compute_client, resource_group, vm_name)
        if not creation_time:
            logger.error(f"Could not determine creation time for VM {vm_name}")
            return False

        instance_age = datetime.now(creation_time.tzinfo) - creation_time
        if instance_age.days < VM_AGE_DAYS:
            logger.info(f"VM {vm_name} is {instance_age.days} days old.")
            logger.info(f"VM {vm_name} is less than {VM_AGE_DAYS} days old. Skipping.")
            return False

        logger.info(f"VM {vm_name} is {instance_age.days} days old. Checking CPU utilization.")

        # Get CPU metrics for the last 2 days
        creds = ClientSecretCredential(
            tenant_id=azure_creds['tenant_id'],
            client_id=azure_creds['client_id'],
            client_secret=azure_creds['client_secret'],
        )
        monitor_client = MonitorManagementClient(creds, azure_creds['subscription_id'])

        now = datetime.utcnow()
        start = now - timedelta(days=CPU_CHECK_DAYS)
        logger.info(f"Fetching metrics from {start} to {now} for VM: {vm_resource_id}")

        metrics_data = monitor_client.metrics.list(
            resource_uri=vm_resource_id,
            timespan=f"{start}/{now}",
            interval='PT5M',  # 5-minute granularity
            metricnames='Percentage CPU',
            aggregation='Maximum'
        )
        logger.info("Metrics data retrieved successfully.")

        for item in metrics_data.value:
            for timeseries in item.timeseries:
                for data in timeseries.data:
                    if data.maximum:
                        logger.info(f"CPU usage data point: {data.maximum}")
                    if data.maximum and data.maximum > AZURE_CPU_THRESHOLD:
                        logger.warning(f"VM {vm_resource_id} exceeds CPU threshold with usage: {data.maximum}")
                        return False

        logger.info(f"VM {vm_resource_id} has low CPU usage for the last {CPU_CHECK_DAYS} days.")
        return True

    except Exception as e:
        logger.error(f"Error in has_low_usage_azure: {e}")
        raise
