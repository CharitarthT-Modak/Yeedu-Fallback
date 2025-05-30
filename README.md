# Cloud VM Fallback Detection

A Python-based tool for detecting and managing underutilized virtual machines across multiple cloud providers (AWS, GCP, and Azure). The tool identifies VMs that have been running for a specified period with low CPU utilization and removes them.

## Features

- Multi-cloud support (AWS, GCP, Azure)
- CPU utilization monitoring
- VM age verification
- Required tag validation
- Automated VM removal
- Detailed logging
- Configurable thresholds

## Prerequisites

- Python 3.6+
- Cloud provider credentials:
  - AWS: Access key and secret key
  - GCP: Service account credentials
  - Azure: Service principal credentials

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd fallback
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up credentials:
   - Update the credentials directory path in config.py `BASE_CRED_PATH`:
     - `yeedu-aws-creds.json`
     - `yeedu-gcp-creds.json`
     - `yeedu-azure-creds.json`

## Configuration

The tool's behavior can be configured in `config.py`:

- `VM_AGE_DAYS`: Minimum age of VMs to consider (default: 30 days)
- `CPU_CHECK_DAYS`: Duration to check CPU utilization (default: 2 days)
- `AWS_CPU_THRESHOLD`: CPU utilization threshold for AWS (default: 5.0%)
- `GCP_CPU_THRESHOLD`: CPU utilization threshold for GCP (default: 5.0%)
- `AZURE_CPU_THRESHOLD`: CPU utilization threshold for Azure (default: 5.0%)
- `REQUIRED_TAGS`: Tags that must be present on VMs

## Usage

Run the tool using:

```bash
python3 main.py
```

The tool will:
1. Scan VMs across all configured cloud providers
2. Check for required tags
3. Verify VM age
4. Monitor CPU utilization
5. Remove VMs that meet the criteria
6. Generate a detailed log file

## Logging

Logs are written to both:
- Console output
- A timestamped log file in the `logs` directory (e.g., `logs/fallback_20240321_123456.log`)

The `logs` directory is automatically created if it doesn't exist.

## Project Structure

- `main.py`: Entry point
- `controller.py`: Main controller class
- `aws_fallback.py`: AWS-specific logic
- `gcp_fallback.py`: GCP-specific logic
- `azure_fallback.py`: Azure-specific logic
- `utils.py`: Shared utilities
- `auth.py`: Authentication handling
- `config.py`: Configuration settings

## Error Handling

The tool includes comprehensive error handling and logging:
- Cloud provider API errors
- Authentication failures
- Resource access issues
- VM removal failures