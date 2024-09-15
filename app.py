import boto3
import botocore.config
import json
import datetime
import uuid

# Function to generate a blog using the Amazon Bedrock foundation model
def generate_blog_content(query: str) -> str:
    """
    Generates a comprehensive blog post based on the input query using a foundation model from Amazon Bedrock.
    """
    prompt = f"""
    <s>[INST]Human: Write a comprehensive blog post on "{query}" in markdown format. Use appropriate markdown syntax, including:

    - Headings (#, ##, ###)
    - Bullet points (*, -)
    - Numbered lists (1., 2., 3.)
    - Code blocks (```) for any code snippets
    - Italics (*) and bold (**) for emphasis
    - Hyperlinks ([text](URL)) where relevant
    - Image placeholders (![alt text](image-url-placeholder)) if applicable
    
    Provide an in-depth analysis covering all relevant aspects of the topic, including practical examples, statistics, and real-world applications where appropriate. The style should mirror detailed articles found in respected tech publications like *Wired* or *TechCrunch*, focusing on clarity, depth, and expert insight.
    
    The narrative should be from the perspective of a technology expert, using professional yet accessible language. Organize the blog with clear and logical subheadings that suit the content, ensuring a smooth flow of ideas. Begin with an engaging introduction to set the context and conclude with a thoughtful summary or call to action.
    
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
        # Initialize the Amazon Bedrock client
        bedrock = boto3.client(
            "bedrock-runtime",
            region_name="us-east-1",  # Ensure you're in a supported region for Bedrock
            config=botocore.config.Config(read_timeout=300, retries={'max_attempts': 3})
        )
        
        # Invoke the model to generate the blog content
        response = bedrock.invoke_model(
            body=json.dumps(body),
            modelId="meta.llama3-70b-instruct-v1:0"
        )
        
        # Parse the response
        response_content = response['body'].read()
        response_data = json.loads(response_content)
        blog_content = response_data.get('generation', "")
        
        return blog_content
    except Exception as e:
        print(f"Error generating the blog: {e}")
        return ""

# Function to save the generated blog to an S3 bucket
def save_blog_to_s3(s3_key: str, s3_bucket: str, blog_content: str):
    """
    Saves the generated blog content to an S3 bucket.
    """
    s3 = boto3.client('s3')

    try:
        # Attempt to upload the blog content to the S3 bucket
        s3.put_object(Bucket=s3_bucket, Key=s3_key, Body=blog_content)
        print(f"Blog saved to S3 at {s3_key}.")

        # Verify if the object exists in the S3 bucket
        head_response = s3.head_object(Bucket=s3_bucket, Key=s3_key)
        print(f"HeadObject response: {head_response}")  # This should print metadata of the object if it exists

    except Exception as e:
        print(f"Error saving the blog to S3: {e}")  # Log any issues with the S3 put_object

def generate_presigned_url(s3_bucket: str, s3_key: str, expiration: int = 3600) -> str:
    """
    Generate a pre-signed URL for the S3 object.
    """
    s3 = boto3.client('s3')

    try:
        presigned_url = s3.generate_presigned_url(
            'get_object',  # Ensure this is 'get_object'
            Params={'Bucket': s3_bucket, 'Key': s3_key},
            ExpiresIn=expiration
        )
        print(f"Generated pre-signed URL: {presigned_url}")
        return presigned_url
    except Exception as e:
        print(f"Error generating pre-signed URL: {e}")
        return ""



# Lambda function handler to process events and generate/save blogs
def lambda_handler(event, context):
    """
    AWS Lambda handler to generate a blog based on the input topic and save it to S3.
    """
    try:
        # Parse the incoming event
        event_body = json.loads(event.get('body', '{}'))
        blog_topic = event_body.get('blogTopic', "")

        if not blog_topic:
            return {
                'statusCode': 400,
                'body': json.dumps('Blog topic is required.')
            }

        # Generate the blog content
        blog_content = generate_blog_content(query=blog_topic)

        if not blog_content:
            return {
                'statusCode': 500,
                'body': json.dumps('Error generating the blog content.')
            }

        # Generate a unique ID for the blog post
        blog_id = str(uuid.uuid4())

        # Generate a unique key for the S3 object using the blog_id
        s3_key = f"blogs/{blog_id}.md"
        s3_bucket = "blog-gen-app"  # Ensure this bucket exists and Lambda has permissions

        # Save the generated blog content to S3
        save_blog_to_s3(s3_key, s3_bucket, blog_content)

        # Return success with the blog ID
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Blog generation and saving are completed!',
                'blogId': blog_id
            })
        }
    except Exception as e:
        print(f"Error processing the request: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps('Internal server error.')
        }