from datetime import datetime, timedelta
from azure.mgmt.monitor import MonitorManagementClient
from azure.identity import ClientSecretCredential
from auth import get_azure_client
from utils import check_required_tags
from config import AZURE_CREDS_PATH,AZURE_IDLE_MINUTES, AZURE_CPU_THRESHOLD
import logging
from azure.mgmt.compute import ComputeManagementClient
from azure.identity import DefaultAzureCredential
import json

# Configure logging
logger = logging.getLogger(__name__)

def has_low_usage_azure(vm_resource_id):
    logger.info(f"Checking low usage for VM: {vm_resource_id}")
    compute_client = get_azure_client()
    parts = vm_resource_id.split('/')
    resource_group = parts[4]
    vm_name = parts[8]
    logger.info(f"Extracted resource group: {resource_group}, VM name: {vm_name}")

    if not check_required_tags(compute_client, vm_resource_id):
        logger.warning(f"VM {vm_resource_id} does not have required tags.")
        return False

    logger.info("VM has required tags. Proceeding with Azure credentials setup.")
    import json
    with open(AZURE_CREDS_PATH, 'r') as f:
        data = json.load(f)
        creds = ClientSecretCredential(
            tenant_id=data['TENANT_ID'],
            client_id=data['CLIENT_ID'],
            client_secret=data['CLIENT_SECRET'],
        )
        subscription_id = data['SUBSCRIPTION_ID'] # Read subscription ID from credentials
    logger.info("Azure credentials successfully loaded.")

    monitor_client = MonitorManagementClient(creds, subscription_id)
    logger.info("MonitorManagementClient initialized.")

    now = datetime.utcnow()
    start = now - timedelta(minutes=AZURE_IDLE_MINUTES)  # Use time-based check
    logger.info(f"Fetching metrics from {start} to {now} for VM: {vm_resource_id}")

    metrics_data = monitor_client.metrics.list(
        resource_uri=vm_resource_id,
        timespan=f"{start}/{now}",
        interval='PT1M',  # 1-minute granularity
        metricnames='Percentage CPU',
        aggregation='Maximum'  # Check maximum utilization
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

    logger.info(f"VM {vm_resource_id} has low CPU usage.")
    return True

def get_azure_clients():
    with open(AZURE_CREDS_PATH, 'r') as f:
        data = json.load(f)
        subscription_id = data['SUBSCRIPTION_ID']  # Read subscription ID from credentials

    credential = DefaultAzureCredential()
    compute_client = ComputeManagementClient(credential, subscription_id)
    monitor_client = MonitorManagementClient(credential, subscription_id)
    return compute_client, monitor_client

def list_idle_vms(compute_client, monitor_client):
    try:
        logger.info("Fetching Azure VMs...")
        idle_vms = []
        for vm in compute_client.virtual_machines.list_all():
            vm_name = vm.name
            resource_group = vm.id.split("/")[4]
            logger.info(f"Checking VM: {vm_name} in resource group: {resource_group}")

            # Fetch CPU utilization metrics
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=AZURE_IDLE_MINUTES)
            metrics_data = monitor_client.metrics.list(
                resource_uri=vm.id,
                timespan=f"{start_time}/{end_time}",
                interval="PT1M",
                metricnames="Percentage CPU",
                aggregation="Average"
            )

            # Check if CPU usage is below the threshold
            for metric in metrics_data.value:
                for timeseries in metric.timeseries:
                    for data in timeseries.data:
                        if data.average is not None and data.average < AZURE_CPU_THRESHOLD:
                            logger.info(f"VM {vm_name} is idle with CPU usage: {data.average}%")
                            idle_vms.append(vm_name)
                            break

        logger.info(f"Idle VMs: {idle_vms}")
        return idle_vms
    except Exception as e:
        logger.error(f"Error listing idle VMs: {e}")
        raise
