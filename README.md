# Finding Mt. Fuji with GPT and Soracom Cloud Camera Service

This project aims to detect Mt. Fuji in images using OpenAI's GPT model. The application is deployed as an AWS Lambda function, which exports images from the Soracom Cloud Camera Service, processes them with OpenAI's GPT model to detect Mt. Fuji, and posts the results to a specified Slack channel.

## Project Structure

- [app.py](src/finding_fuji/app.py)` contains the core logic for image processing and Slack integration.
- [requirements.txt](src/finding_fuji/requirements.txt) lists all the necessary Python packages.
- [template.yaml](template.yaml) defines the AWS SAM template for deploying the Lambda function.

## Prerequisites

- AWS CLI
- AWS SAM CLI
- Python 3.9
- SORACOM Account and API keys
- The camera of Soracom Cloud Camera Services (As of 2023-12-01, only sold in Japan)
- Slack Bot Token and Channel ID
- OpenAI API Key

## Setup and Deployment

1. **Configure AWS Credentials**:
   Ensure that your AWS CLI is configured with the appropriate credentials.

2. **Build and deploy with AWS SAM**:
In the root directory, run:

```
sam build
sam deploy --guided
```

You will be asked for the followings.

- Soracom Account and API keys
- Soracom Cloud Camera device ID
- Slack Bot Token and Channel ID
- OpenAI API Key

## Schedule Execution

The Lambda function is scheduled to run daily at 6:30 AM JST. This can be adjusted in the [template.yaml](template.yaml) file under the `Events` section.

## Usage

The Lambda function will automatically execute based on the schedule defined in [template.yaml](template.yaml). It will:

1. Export an image from the Soracom Cloud Camera Service.
2. Analyze the image using OpenAI's GPT model to detect Mt. Fuji.
3. Post the results to the specified Slack channel.

## Security

Ensure that all sensitive keys and tokens are stored securely and not exposed publicly. If possible, use AWS Secrets Manager instead of environment variables.
