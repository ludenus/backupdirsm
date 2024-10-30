#!/usr/bin/env python3

import boto3
import sys
import logging
import os
import re
import socket
from datetime import datetime
from datetime import timezone
from botocore.exceptions import ClientError
import argparse
import fnmatch


# This is a placeholder and will be replaced by the version from poetry-dynamic-versioning
VERSION = "0.0.0"

_secretsmanager = None
_hostname = socket.gethostname()


def get_secretsmanager():
    global _secretsmanager
    if _secretsmanager is None:
        _secretsmanager = boto3.client("secretsmanager")
    return _secretsmanager


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: [%(filename)s:%(lineno)s] %(message)s",
)
logger = logging.getLogger(__name__)


def get_iso8601_timestamp(time):
    # Create a naive datetime object in local time
    dt = datetime.fromtimestamp(time)
    # Make it timezone-aware by attaching the local timezone
    dt = dt.astimezone()
    return dt.isoformat()


def validate_directory(path, mode="source"):
    try:
        canonical_path = os.path.abspath(os.path.realpath(path))
    except Exception as e:
        logger.error(f"Failed to resolve the canonical path for '{path}': {e}")
        sys.exit(11)

    if canonical_path == "/":
        logger.error("Root directory '/' is not allowed as a source or destination.")
        sys.exit(12)
    if not os.path.exists(canonical_path):
        logger.error(
            f"{mode.capitalize()} directory '{canonical_path}' does not exist."
        )
        sys.exit(13)
    if mode == "source" and not os.access(canonical_path, os.R_OK):
        logger.error(
            f"{mode.capitalize()} directory '{canonical_path}' is not accessible."
        )
        sys.exit(14)
    if mode == "destination" and not os.access(canonical_path, os.W_OK):
        logger.error(
            f"{mode.capitalize()} directory '{canonical_path}' is not writable."
        )
        sys.exit(15)

    return canonical_path

def upload_to_secrets_manager(secret_name, secret_value, description=None, tags=None):
    client = get_secretsmanager()

    try:
        response = client.create_secret(
            Name=secret_name,
            SecretString=secret_value,
            Description=description or "",
            Tags=tags or [],
        )
        logger.info(f"Secret created: '{secret_name}'")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceExistsException":
            response = client.update_secret(
                SecretId=secret_name,
                SecretString=secret_value,
                Description=description or "",
            )
            logger.info(f"Secret updated: '{secret_name}'.")
            if tags:
                client.untag_resource(
                    SecretId=secret_name, TagKeys=[tag["Key"] for tag in tags]
                )
                client.tag_resource(SecretId=secret_name, Tags=tags)
                logger.info(f"Tags updated: '{secret_name}'.")
        else:
            logger.error(f"Failed to store secret: {e}")
            sys.exit(21)


def upload_directory(directory, include_pattern=None, exclude_pattern=None):
    for root, _, files in os.walk(directory, followlinks=True):
        for file_name in files:
            file_path = os.path.abspath(os.path.join(root, file_name))

            # Apply include and exclude patterns using regular expressions
            if include_pattern and not bool(re.search(include_pattern, file_path)):
                logger.debug(f"Skipping {file_path} because it does not match the include pattern: {include_pattern}")
                continue
            if exclude_pattern and bool(re.search(exclude_pattern, file_path)):
                logger.debug(f"Skipping {file_path} because it matches the exclude pattern: {exclude_pattern}")
                continue

            try:
                with open(file_path, "r") as file:
                    file_content = file.read()

                last_modified_iso = get_iso8601_timestamp(os.path.getmtime(file_path))
                tags = [
                    {"Key": "filename", "Value": file_path},
                    {"Key": "hostname", "Value": _hostname},
                    {"Key": "lastmodified", "Value": last_modified_iso},
                ]
                secret_name = re.sub(r"[^a-zA-Z0-9_\/]", "_", file_path)
                upload_to_secrets_manager(secret_name, file_content, tags=tags)
            except Exception as e:
                logger.error(f"Error uploading file '{file_path}': {e}")


def download_from_secrets_manager(destination, include_pattern=None, exclude_pattern=None):
    client = get_secretsmanager()
    destination = os.path.abspath(os.path.realpath(destination))
    try:
        # Handle pagination for secrets
        paginator = client.get_paginator("list_secrets")
        page_iterator = paginator.paginate(
            Filters=[{"Key": "tag-key", "Values": ["filename"]}]
        )
        for page in page_iterator:
            for secret in page["SecretList"]:
                # Extract filename tag
                filename_tag = next(
                    (
                        tag["Value"]
                        for tag in secret.get("Tags", [])
                        if tag["Key"] == "filename"
                    ),
                    None,
                )
                if not filename_tag:
                    continue

                file_path = filename_tag

                # Apply include and exclude patterns using regular expressions
                if include_pattern and not bool(re.search(include_pattern, file_path)):
                    logger.debug(f"Skipping {file_path} because it does not match the include pattern: {include_pattern}")
                    continue
                if exclude_pattern and bool(re.search(exclude_pattern, file_path)):
                    logger.debug(f"Skipping {file_path} because it matches the exclude pattern: {exclude_pattern}")
                    continue

                # Construct destination path
                dest_path = os.path.abspath(file_path)

                # Ensure that the destination path is within the destination directory
                if not dest_path.startswith(destination):
                    logger.warning(
                        f"Destination path '{dest_path}' is outside the destination directory '{destination}'. Skipping."
                    )
                    continue

                # Download and save the secret
                secret_name = secret["Name"]
                response = client.get_secret_value(SecretId=secret_name)
                secret_value = response["SecretString"]
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                with open(dest_path, "w") as file:
                    file.write(secret_value)
                logger.info(f"Downloaded secret '{secret_name}' to '{dest_path}'.")
    except ClientError as e:
        logger.error(f"Failed to retrieve secrets: {e}")
        sys.exit(31)


def main():
    parser = argparse.ArgumentParser(
        description="Upload or download directory contents to/from AWS Secrets Manager."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-u",
        "--upload",
        type=str,
        help="Source directory to upload to AWS Secrets Manager",
    )
    group.add_argument(
        "-d",
        "--download",
        type=str,
        help="Destination directory where to download from AWS Secrets Manager",
    )
    parser.add_argument(
        "-i",
        "--include",
        metavar="REGEX",
        help="Include only files matching the regex pattern",
    )
    parser.add_argument(
        "-e",
        "--exclude",
        metavar="REGEX",
        help="Exclude files matching the regex pattern",
    )
    args = parser.parse_args()

    if args.upload:
        source_path = validate_directory(args.upload, "source")
        upload_directory(
            source_path, include_pattern=args.include, exclude_pattern=args.exclude
        )
    elif args.download:
        destination_path = validate_directory(args.download, "destination")
        download_from_secrets_manager(
            destination_path, include_pattern=args.include, exclude_pattern=args.exclude
        )


if __name__ == "__main__":
    main()
