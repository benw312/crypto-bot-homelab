#backup.py
import os
import subprocess
import boto3
from botocore.exceptions import NoCredentialsError

BACKUP_DIR = os.getenv("INFLUXDB_BACKUP_DIR", os.path.expanduser("~/influxdb/backup"))

def upload_to_aws(local_file, bucket, s3_file):
    s3 = boto3.client('s3')

    try:
        s3.upload_file(local_file, bucket, s3_file)
        print("Upload Successful")
        return True
    except FileNotFoundError:
        print("The file was not found")
        return False
    except NoCredentialsError:
        print("Credentials not available")
        return False

def backup_data():
    backup_dir = BACKUP_DIR

    # Check if the backup directory exists, if not, create it
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir, exist_ok=True)

    # InfluxDB backup command
    subprocess.run(["influxd", "backup", "-portable", backup_dir], check=True)

    # Define S3 bucket
    bucket_name = os.environ["BACKUP_S3_BUCKET"]

    # List of all files in the backup directory
    files = os.listdir(backup_dir)

    for file in files:
        local_file = os.path.join(backup_dir, file)
        s3_file = file
        uploaded = upload_to_aws(local_file, bucket_name, s3_file)

        if uploaded:
            print(f"{file} uploaded to S3 successfully.")
        else:
            print(f"Failed to upload {file}.")

    print("Backup and upload to S3 completed.")

if __name__ == "__main__":
    backup_data()
