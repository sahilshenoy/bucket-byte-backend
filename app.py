import boto3  # AWS SDK for Python to interact with AWS services
import botocore.config  # To configure boto3 with timeout and retry settings
import json  # To handle JSON data
import datetime  # To manage date and time

# Function to generate a blog using the Amazon Bedrock foundation model
def generate_blog_content(query: str) -> str:
    """
    Generates a comprehensive blog post based on the input query using a foundation model from Amazon Bedrock.
    
    Parameters:
    query (str): The topic for the blog post.

    Returns:
    str: The generated blog content or an empty string in case of an error.
    """
    # Define the prompt that will be sent to the model
    prompt = f"""
    <s>[INST]Human: Write a comprehensive blog post on {query} in markdown format. 
    Use markdown syntax, such as # for headers, * for bullet points, and other appropriate markdown elements.
    Provide an in-depth analysis of the latest advancements and their technological impacts. 
    The style should mirror detailed articles found in respected tech publications like Wired or TechCrunch, focusing on clarity and expert insight. 
    The narrative should be from the perspective of a technology expert, using professional yet understandable language. 
    Organize the blog with clear subheadings: Introduction, Key Technologies, Market Impact, and Future Trends. 
    The tone should be informative, authoritative, and engaging, designed to keep tech enthusiasts informed and captivated throughout the article. 
    Assistant:[/INST]</s>
    """

    # Define the request body with the model parameters
    body = {
        "prompt": prompt,
        "max_gen_len": 1024,
        "temperature": 0.5,  # Controls creativity; higher value increases randomness
        "top_p": 0.9,  # Controls diversity; higher value allows more diverse words
    }

    try:
        # Initialize the Amazon Bedrock client
        bedrock=boto3.client(
            "bedrock-runtime",
            region_name="us-east-1",
            config=botocore.config.Config(read_timeout=300,retries={'max_attempts':3})
        )
        
        # Invoke the model to generate the blog content
        response = bedrock.invoke_model(
            body=json.dumps(body),
            modelId="meta.llama3-70b-instruct-v1:0"
        )
        
        # Read and parse the response
        response_content = response['body'].read()
        response_data = json.loads(response_content)
        blog_content = response_data.get('generation', "")
        
        # Return the generated blog content
        return blog_content
    except Exception as e:
        print(f"Error generating the blog: {e}")  # Log the error to CloudWatch
        return ""

# Function to save the generated blog to an S3 bucket
def save_blog_to_s3(s3_key: str, s3_bucket: str, blog_content: str):
    """
    Saves the generated blog content to an S3 bucket.

    Parameters:
    s3_key (str): The S3 object key where the blog will be saved.
    s3_bucket (str): The S3 bucket name.
    blog_content (str): The generated blog content.
    """
    s3 = boto3.client('s3')

    try:
        # Upload the blog content to the specified S3 bucket
        s3.put_object(Bucket=s3_bucket, Key=s3_key, Body=blog_content)
        print("Blog saved to S3 successfully.")
    except Exception as e:
        print(f"Error saving the blog to S3: {e}")  # Log the error

# Lambda function handler to process events and generate/save blogs
def lambda_handler(event, context):
    """
    AWS Lambda handler to generate a blog based on the input topic and save it to S3.

    Parameters:
    event (dict): The event payload passed to the Lambda function.
    context (dict): The runtime information of the Lambda function.

    Returns:
    dict: The HTTP response indicating the result of the operation.
    """
    # Parse the incoming event and extract the blog topic
    event_body = json.loads(event['body'])
    blog_topic = event_body.get('blogTopic', "")

    if not blog_topic:
        return {
            'statusCode': 400,
            'body': json.dumps('Blog topic is required.')
        }

    # Generate the blog content based on the topic
    blog_content = generate_blog_content(query=blog_topic)

    if blog_content:
        # Generate a unique key for the S3 object using the current timestamp
        current_time = datetime.datetime.now().strftime("%H%M%S")
        s3_key = f"blog_output/{current_time}.md"  # S3 object key (path)
        s3_bucket = "blog-gen-app"  # Your S3 bucket name

        # Save the generated blog content to S3
        save_blog_to_s3(s3_key, s3_bucket, blog_content)
    else:
        print("No blog was generated!")

    # Return a success response
    return {
        'statusCode': 200,
        'body': json.dumps('Blog generation and saving are completed!')
    }
