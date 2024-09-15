# Blog Generator using AWS Bedrock and S3

This project is an AWS Lambda-based application that generates blog posts using a foundation model from Amazon Bedrock. The generated blogs are saved in an S3 bucket in Markdown format. The application also provides functionality to generate pre-signed URLs for accessing the saved blogs.

## Features

- **Blog Generation**: Generates blog posts in markdown format based on user-specified topics.
- **Amazon Bedrock**: Utilizes the Bedrock foundation model to generate content.
- **S3 Integration**: Saves the generated blog to an S3 bucket and verifies successful upload.
- **Pre-signed URL**: Generates a pre-signed URL to access the blog stored in S3.

## Technologies

- **Amazon Bedrock**: Used for AI-based blog content generation.
- **Amazon S3**: Used for storing generated blogs.
- **AWS Lambda**: Serverless function to handle requests, generate content, and store blogs.
- **boto3**: AWS SDK for Python, used for interacting with Bedrock and S3.

## Setup and Deployment

### Prerequisites

- **AWS Account**: Ensure you have access to Amazon Bedrock and S3 services.
- **IAM Roles and Permissions**: The Lambda function must have the following permissions:
  - `bedrock:InvokeModel`: To invoke the Bedrock model.
  - `s3:PutObject` and `s3:GetObject`: To save and retrieve objects from S3.
  - `s3:GeneratePresignedUrl`: To generate pre-signed URLs for the saved blogs.
  
### Configuration

1. **S3 Bucket**: 
   - Create an S3 bucket where the blog markdown files will be stored. Update the `s3_bucket` variable in the code with your bucket name.

2. **Lambda Function**:
   - Deploy the provided `lambda_handler` function to AWS Lambda.
   - Ensure the Lambda function has the correct IAM role with necessary permissions (Bedrock, S3).

3. **Amazon Bedrock Setup**:
   - Ensure you are using a supported region for Amazon Bedrock (e.g., `us-east-1`).
   - Update the `modelId` in the code to use the appropriate Bedrock model for blog generation.

### Running the Project

#### Input
The Lambda function expects the following input as a JSON body:

```json
{
  "blogTopic": "Enter the blog topic here"
}
