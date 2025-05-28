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
        subscription_id = data['SUBSCRIPTION_ID'] 
    logger.info("Azure credentials successfully loaded.")

    monitor_client = MonitorManagementClient(creds, subscription_id)
    logger.info("MonitorManagementClient initialized.")

    now = datetime.utcnow()
    start = now - timedelta(minutes=AZURE_IDLE_MINUTES)  
    logger.info(f"Fetching metrics from {start} to {now} for VM: {vm_resource_id}")

    metrics_data = monitor_client.metrics.list(
        resource_uri=vm_resource_id,
        timespan=f"{start}/{now}",
        interval='PT1M', 
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
