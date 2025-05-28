import logging
from auth import get_aws_client, get_gcp_client, get_azure_client
from utils import check_required_tags, remove_vm
from aws_fallback import has_low_usage_aws
from gcp_fallback import has_low_usage_gcp
from azure_fallback import has_low_usage_azure
# from config import AZURE_SUBSCRIPTION_ID

logger = logging.getLogger(__name__)

class FallbackController:
    def __init__(self):
        logger.info("Initializing FallbackController")
        self.ec2 = get_aws_client('ec2')
        self.gcp_compute = get_gcp_client()
        self.azure_compute = get_azure_client()

    def get_aws_machines(self):
        logger.info("Fetching AWS candidates for fallback")
        results = []
        instances = self.ec2.describe_instances()
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                logger.info(f"Checking AWS instance: {instance_id}")
                if has_low_usage_aws(instance_id):
                    logger.info(f"Instance {instance_id} has low usage. Attempting to remove.")
                    success, message = remove_vm(self.ec2, instance_id)
                    results.append((instance_id, success, message))
        logger.info("AWS candidate evaluation completed")
        return results

    def get_gcp_machines(self, project_id):
        logger.info("Fetching GCP candidates for fallback")
        results = []
        request = {"project": project_id}
        agg_list = self.gcp_compute.aggregated_list(request=request)

        for zone_result in agg_list:
            zone = zone_result[0].split("/")[-1]
            instances = zone_result[1].instances if zone_result[1].instances else []
            for instance in instances:
                instance_id = instance.id
                instance_name = instance.name
                logger.info(f"Checking GCP instance: {instance_id} in zone: {zone}")

                if has_low_usage_gcp(project_id, instance_id, zone):
                    logger.info(f"Instance {instance_id} has low usage. Attempting to remove.")
                    success, message = remove_vm(self.gcp_compute, project_id, zone, instance_name)
                    results.append((instance_id, success, message))
        logger.info("GCP candidate evaluation completed")
        return results


    def get_azure_machines(self):
        logger.info("Fetching Azure candidates for fallback")
        results = []
        for vm in self.azure_compute.virtual_machines.list_all():
            logger.info(f"Checking Azure VM: {vm.id}")
            if has_low_usage_azure(vm.id):
                logger.info(f"VM {vm.id} has low usage. Attempting to remove.")
                success, message = remove_vm(self.azure_compute, vm.id)
                results.append((vm.name, success, message))
        logger.info("Azure candidate evaluation completed")
        return results

    def execute_fallback(self, project_id):
        logger.info("Executing fallback detection")
        results = {"aws": [], "gcp": [], "azure": []}
        try:
            results["aws"] = self.get_aws_machines()  
            pass
        except Exception as e:
            logger.error(f"AWS fallback failed: {e}")
        try:
            results["gcp"] = self.get_gcp_machines(project_id)
            pass
        except Exception as e:
            logger.error(f"GCP fallback failed: {e}")
        try:
            results["azure"] = self.get_azure_machines()  
            pass
        except Exception as e:
            logger.error(f"Azure fallback failed: {e}")
        logger.info("Fallback detection completed")
        return results
