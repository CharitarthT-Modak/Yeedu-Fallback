import logging
from config import REQUIRED_TAGS
from auth import get_aws_client, get_gcp_client, get_azure_client

# Configure logging
logger = logging.getLogger(__name__)

def check_required_tags(client, *args):
    resource_id = args[0]
    logger.info(f"Checking required tags for resource: {resource_id}")
    try:
        # Add detailed logging to trace the flow
        logger.info(f"Client: {client}, Resource ID: {resource_id}")
        if hasattr(client, 'describe_instances'):  # AWS
            instance_id = args[0]
            ec2_client = get_aws_client('ec2')
            response = ec2_client.describe_instances(InstanceIds=[instance_id])
            tags = response['Reservations'][0]['Instances'][0].get('Tags', [])
            tags_dict = {tag['Key']: tag['Value'] for tag in tags}
            result = all(tags_dict.get(k) == v for k, v in REQUIRED_TAGS.items())
        elif hasattr(client, 'get'):  # GCP
            project_id, zone, instance_id = args
            compute_client = get_gcp_client()
            instance = compute_client.get(project=project_id, zone=zone, instance=instance_id)
            labels = instance.labels
            result = labels and all(labels.get(k) == v for k, v in REQUIRED_TAGS.items())
        else:  # Azure
            vm_resource_id = args[0]
            compute_client = get_azure_client()
            parts = vm_resource_id.split('/')
            resource_group = parts[4]
            vm_name = parts[8]
            vm = compute_client.virtual_machines.get(resource_group, vm_name)
            result = vm.tags and all(vm.tags.get(k) == v for k, v in REQUIRED_TAGS.items())
        logger.info(f"Tags check completed for resource: {resource_id}")
    except Exception as e:
        logger.error(f"Error in check_required_tags: {e}")
        raise
    return result

def remove_vm(client, *args):
    resource_id = args[0]
    logger.info(f"Attempting to remove VM: {resource_id}")
    try:
        if hasattr(client, 'terminate_instances'):  # AWS
            instance_id = args[0]
            ec2_client = get_aws_client('ec2')
            ec2_client.terminate_instances(InstanceIds=[instance_id])
            result = True, f"AWS instance {instance_id} termination initiated"
        elif hasattr(client, 'delete'):  # GCP
            project_id, zone, instance_id = args
            compute_client = get_gcp_client()
            op = compute_client.delete(project=project_id, zone=zone, instance=instance_id)
            op.result()
            result = True, f"GCP instance {instance_id} deleted"
        else:  # Azure
            vm_resource_id = args[0]
            compute_client = get_azure_client()
            parts = vm_resource_id.split('/')
            resource_group = parts[4]
            vm_name = parts[8]
            poller = compute_client.virtual_machines.begin_delete(resource_group, vm_name)
            poller.result()
            result = True, f"Azure VM {vm_name} deleted"
    except Exception as e:
        result = False, f"Failed to remove VM: {e}"
    logger.info(f"VM {resource_id} removed successfully.")
    return result
