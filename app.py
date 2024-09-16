import boto3
import botocore.config
import json
import uuid
import os
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def generate_blog_content(query: str) -> str:
    prompt = f"""
<s>[INST]Human: Write a comprehensive blog post on "{query}" in markdown format. Use appropriate markdown syntax, including:

- Headings (#, ##, ###)
- Bullet points (*, -)
- Numbered lists (1., 2., 3.)
- Code blocks (```) for any code snippets
- Italics (*) and bold (**) for emphasis
- Hyperlinks ([text](URL)) where relevant

Provide an in-depth analysis covering all relevant aspects of the topic, including practical examples, statistics, and real-world applications where appropriate. The style should mirror detailed articles found in respected tech publications like *Wired* or *TechCrunch*, focusing on clarity, depth, and expert insight.

The narrative should be from the perspective of a technology expert, using professional yet accessible language. Organize the blog with clear and logical subheadings that suit the content, ensuring a smooth flow of ideas. Begin with an engaging introduction to set the context and conclude with a thoughtful summary or call to action. Do not include an image.

The tone should be informative, authoritative, and engaging, designed to keep tech enthusiasts informed and captivated throughout the article. Ensure the content is original, free of plagiarism, and optimized for readability.

Assistant:[/INST]</s>
    """

    body = {
        "prompt": prompt,
        "max_gen_len": 1024,
        "temperature": 0.5,
        "top_p": 0.9,
    }

    try:
        bedrock = boto3.client(
            "bedrock-runtime",
            region_name=os.environ.get('REGION', 'us-east-1'),
            config=botocore.config.Config(read_timeout=300, retries={'max_attempts': 3})
        )

        response = bedrock.invoke_model(
            body=json.dumps(body),
            modelId="meta.llama3-70b-instruct-v1:0"
        )

        response_content = response['body'].read().decode('utf-8')
        logger.info(f"Raw response content: {response_content}")

        response_data = json.loads(response_content)
        logger.info(f"Parsed response data: {response_data}")

        # Correctly extract the blog content from the 'generation' key
        blog_content = response_data.get('generation', "")
        logger.info(f"Extracted blog content: {blog_content}")

        return blog_content
    except Exception as e:
        logger.error(f"Error generating the blog: {e}", exc_info=True)
        raise

def save_blog_to_s3(s3_key: str, s3_bucket: str, blog_content: str):
    s3 = boto3.client('s3')

    try:
        s3.put_object(Bucket=s3_bucket, Key=s3_key, Body=blog_content, ContentType='text/markdown')
        logger.info(f"Blog saved to S3 at {s3_key}.")
    except Exception as e:
        logger.error(f"Error saving the blog to S3: {e}", exc_info=True)
        raise

def lambda_handler(event, context):
    """
    AWS Lambda handler to generate a blog based on the input topic and save it to S3,
    or retrieve an existing blog from S3.
    """
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        # Determine the HTTP method
        http_method = event.get('httpMethod')
        if not http_method:
            http_method = event.get('requestContext', {}).get('http', {}).get('method', '')

        logger.info(f"HTTP method determined: {http_method}")

        # Handle GET request for blog retrieval
        if http_method == 'GET':
            s3 = boto3.client('s3')
            # Use 'id' as the query parameter
            blog_id = event.get('queryStringParameters', {}).get('id', '')
            if not blog_id:
                logger.error("Blog ID is missing from the query parameters")
                return {
                    'statusCode': 400,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type',
                        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                    },
                    'body': json.dumps({'error': 'Blog ID is required to retrieve the blog.'})
                }
            s3_key = f"blogs/{blog_id}.md"
            s3_bucket = "blog-gen-app"  # Replace with your actual S3 bucket name
            try:
                response = s3.get_object(Bucket=s3_bucket, Key=s3_key)
                blog_content = response['Body'].read().decode('utf-8')
                return {
                    'statusCode': 200,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type',
                        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                    },
                    'body': json.dumps({
                        'blogContent': blog_content,
                        'blogId': blog_id
                    })
                }
            except Exception as e:
                logger.error(f"Error retrieving blog from S3: {str(e)}", exc_info=True)
                return {
                    'statusCode': 500,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type',
                        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                    },
                    'body': json.dumps({'error': 'Failed to retrieve blog content.', 'blogId': blog_id})
                }

        # Handle POST request for blog generation
        elif http_method == 'POST':
            event_body = json.loads(event.get('body', '{}'))
            blog_topic = event_body.get('blogTopic', "")

            if not blog_topic:
                logger.error("Blog topic is missing from the request body")
                return {
                    'statusCode': 400,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type',
                        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                    },
                    'body': json.dumps({'error': 'Blog topic is required.', 'blogId': None})
                }

            # Generate the blog content
            blog_content = generate_blog_content(query=blog_topic)

            if not blog_content:
                logger.error("Failed to generate blog content")
                return {
                    'statusCode': 500,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type',
                        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                    },
                    'body': json.dumps({'error': 'Error generating the blog content.', 'blogId': None})
                }

            # Generate a unique ID for the blog post
            blog_id = str(uuid.uuid4())

            # Generate a unique key for the S3 object using the blog_id
            s3_key = f"blogs/{blog_id}.md"
            s3_bucket = "blog-gen-app"  # Replace with your actual S3 bucket name

            # Save the generated blog content to S3
            try:
                save_blog_to_s3(s3_key, s3_bucket, blog_content)
            except Exception as e:
                logger.error(f"Failed to save blog content to S3: {str(e)}", exc_info=True)
                return {
                    'statusCode': 500,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type',
                        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                    },
                    'body': json.dumps({'error': 'Failed to save blog content.', 'blogId': None})
                }

            # Return success with the blog ID
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                },
                'body': json.dumps({
                    'message': 'Blog generation and saving are completed!',
                    'blogId': blog_id
                })
            }

        # Handle other HTTP methods
        else:
            logger.error(f"Unsupported HTTP method: {http_method}")
            return {
                'statusCode': 405,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                },
                'body': json.dumps({'error': 'Method Not Allowed'})
            }

    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({'error': 'Internal server error', 'blogId': None})
        }
