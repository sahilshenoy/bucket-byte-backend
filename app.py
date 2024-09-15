import boto3  # AWS SDK for Python
import botocore.config  # For configuring AWS client with retries, timeouts, etc.
import json  # For handling JSON data (requests and responses)
import uuid  # To generate unique identifiers for S3 object keys
import os  # To access environment variables (for bucket name, region, etc.)

def generate_blog_content(query: str) -> str:
    """
    Generates a comprehensive blog post based on the input query using the Amazon Bedrock model.

    Args:
        query (str): The blog topic input by the user.
    
    Returns:
        str: The generated blog content in markdown format.
    """
    # Define the prompt to be sent to the model, using markdown syntax.
    prompt = f"""
    <s>[INST]Human: Write a comprehensive blog post on "{query}" in markdown format. Use appropriate markdown syntax, including:

    - Headings (#, ##, ###)
    - Bullet points (*, -)
    - Numbered lists (1., 2., 3.)
    - Code blocks (```) for any code snippets
    - Italics (*) and bold (**) for emphasis
    - Hyperlinks ([text](URL)) where relevant
    - Image placeholders (![alt text](image-url-placeholder)) if applicable
    
    Provide an in-depth analysis covering all relevant aspects of the topic, including practical examples, statistics, and real-world applications where appropriate.
    The narrative should be expert yet accessible, engaging for tech enthusiasts. 
    Assistant:[/INST]</s>
    """

    # Model parameters for the AI text generation
    body = {
        "prompt": prompt,
        "max_gen_len": 1024,  # Max characters to generate
        "temperature": 0.5,  # Creativity level (higher is more creative)
        "top_p": 0.9  # Sampling parameter for diverse output
    }

    try:
        # Initialize the Amazon Bedrock client
        bedrock = boto3.client(
            "bedrock-runtime",
            region_name=os.environ.get('REGION', 'us-east-1'),  # AWS Region from environment
            config=botocore.config.Config(read_timeout=300, retries={'max_attempts': 3})  # Retry and timeout configuration
        )
        
        # Send the request to Bedrock to generate the content
        response = bedrock.invoke_model(
            body=json.dumps(body),
            modelId="meta.llama3-70b-instruct-v1:0"  # Model ID for the Llama 3 model
        )
        
        # Extract the generated content from the response
        response_content = response['body'].read()
        response_data = json.loads(response_content)
        blog_content = response_data.get('generation', "")  # Get the generated markdown content

        return blog_content
    except Exception as e:
        print(f"Error generating the blog: {e}")
        raise  # Re-raise the exception for error handling in lambda_handler

def save_blog_to_s3(s3_key: str, s3_bucket: str, blog_content: str):
    """
    Saves the generated blog content to an S3 bucket.

    Args:
        s3_key (str): The key (filename) to store the blog in S3.
        s3_bucket (str): The name of the S3 bucket.
        blog_content (str): The blog content in markdown format.
    """
    s3 = boto3.client('s3')  # Initialize S3 client

    try:
        # Upload the blog content to S3
        s3.put_object(Bucket=s3_bucket, Key=s3_key, Body=blog_content, ContentType='text/markdown')
        print(f"Blog saved to S3 at {s3_key}.")
    except Exception as e:
        print(f"Error saving the blog to S3: {e}")
        raise  # Re-raise exception for error handling in lambda_handler

def lambda_handler(event, context):
    """
    AWS Lambda handler to process incoming API requests, generate a blog, and save it to S3.

    Args:
        event (dict): The event data passed to the Lambda function (API Gateway request).
        context (dict): The runtime context of the Lambda function.

    Returns:
        dict: HTTP response with a success or error message.
    """
    try:
        print(f"Received event: {event}")  # Log the incoming event for debugging
        event_body = json.loads(event.get('body', '{}'))  # Parse the JSON request body
        blog_topic = event_body.get('blogTopic', "")  # Extract the 'blogTopic' from the request

        # If no blog topic is provided, return a 400 error
        if not blog_topic:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                },
                'body': json.dumps({'error': 'Blog topic is required.'})
            }

        # Generate blog content using the Bedrock model
        blog_content = generate_blog_content(query=blog_topic)

        if not blog_content:
            raise Exception("Failed to generate blog content")  # Raise an error if blog content is empty

        # Create a unique ID for the blog file
        blog_id = str(uuid.uuid4())
        s3_key = f"blogs/{blog_id}.md"  # Key (filename) for the blog in S3
        s3_bucket = os.environ.get('S3_BUCKET_NAME', 'blog-gen-app')  # S3 bucket name from environment

        # Save the blog content to S3
        save_blog_to_s3(s3_key, s3_bucket, blog_content)

        # Respond with success and the blog ID
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({
                'message': 'Blog generation and saving are completed!',
                'blogId': blog_id  # Return the blog ID for future use
            })
        }
    except Exception as e:
        # Handle any errors during the process
        print(f"Error processing the request: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({'error': str(e)})
        }
