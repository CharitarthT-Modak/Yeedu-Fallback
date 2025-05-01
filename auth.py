import json
from google.oauth2 import service_account
import boto3
from azure.identity import ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient
from config import AWS_CREDS_PATH, GCP_CREDS_PATH, AZURE_CREDS_PATH, AZURE_SUBSCRIPTION_ID

def load_credentials(creds_path):
    with open(creds_path, 'r') as f:
        return json.load(f)

def get_aws_client(service):
    creds = load_credentials(AWS_CREDS_PATH)
    return boto3.client(
        service,
        aws_access_key_id=creds['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=creds['AWS_SECRET_ACCESS_KEY'],
        region_name=creds['AWS_DEFAULT_REGION']
    )

def get_gcp_client():
    credentials = service_account.Credentials.from_service_account_file(GCP_CREDS_PATH)
    from google.cloud import compute_v1
    return compute_v1.InstancesClient(credentials=credentials)

def get_azure_client():
    creds = load_credentials(AZURE_CREDS_PATH)
    credential = ClientSecretCredential(
        tenant_id=creds['TENANT_ID'],
        client_id=creds['CLIENT_ID'],
        client_secret=creds['CLIENT_SECRET']
    )
    return ComputeManagementClient(credential, AZURE_SUBSCRIPTION_ID)
