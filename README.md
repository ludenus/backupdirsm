# backupdirsm

This Python script uploads or downloads the contents of a specified directory to/from AWS Secrets Manager. It provides a secure way to store or retrieve sensitive data from a directory using AWS Secrets Manager.

## Features

- **Upload directory**: Uploads all files within a specified directory to AWS Secrets Manager as secrets.
- **Download directory**: Retrieves and writes secrets from AWS Secrets Manager to a specified directory.
- **Pattern-based inclusion/exclusion**: Filters files for upload or download based on regular expressions.
- **Metadata tags**: Attaches tags to each secret, such as the filename, hostname, and last modified timestamp.

## Prerequisites

- **Python 3.6+**: Ensure you have Python installed.
- **AWS IAM permissions**: Ensure the user has permissions to use AWS Secrets Manager.

## Installation
```
pip install backupdirsm
```


## Usage
```
usage: backupdirsm [-h] (-u UPLOAD | -d DOWNLOAD) [-i REGEX] [-e REGEX]

Upload or download directory contents to/from AWS Secrets Manager.

options:
  -h, --help            show this help message and exit
  -u UPLOAD, --upload UPLOAD
                        Source directory to upload to AWS Secrets Manager
  -d DOWNLOAD, --download DOWNLOAD
                        Destination directory where to download from AWS Secrets Manager
  -i REGEX, --include REGEX
                        Include only files matching the regex pattern
  -e REGEX, --exclude REGEX
                        Exclude files matching the regex pattern
```

## Examples

### Upload Files

To upload all src files in a directory to AWS Secrets Manager:

```bash
backupdirsm --upload /path/to/directory --include ".*/src/.*" --exclude ".*\.log$"
```

### Download Files
Download only *.conf files from the AWS Secrets Manager:
```bash
backupdirsm --download /path/to/directory --include ".*\.conf$"
```

