import boto3
import requests
import json

# Set your AWS region and account ID
AWS_REGION = 'us-west-1'
AWS_ACCOUNT_ID = '1234567890'

# Set the names for your SQS queue, Lambda function, and DynamoDB table
QUEUE_NAME = 'my-sqs-queue'
LAMBDA_FUNCTION_NAME = 'my-lambda-function'
DYNAMODB_TABLE_NAME = 'my-dynamodb-table'

# Create an SQS FIFO queue
sqs = boto3.client('sqs', region_name=AWS_REGION)
response = sqs.create_queue(QueueName=QUEUE_NAME + '.fifo',
                            Attributes={'FifoQueue': 'true'})

queue_url = response['QueueUrl']

# Create a Lambda function
lambda_client = boto3.client('lambda', region_name=AWS_REGION)
response = lambda_client.create_function(
  FunctionName=LAMBDA_FUNCTION_NAME,
  Runtime='python3.8',
  Role=f'arn:aws:iam::{AWS_ACCOUNT_ID}:role/lambda-role',
  Handler='lambda_function.lambda_handler',
  Layers=[
    f'arn:aws:lambda:{AWS_REGION}:{AWS_ACCOUNT_ID}:layer:requests-layer'
  ],
  Code={
    'S3Bucket': 'my-lambda-bucket',
    'S3Key': 'lambda_function.zip'
  })

# Configure the Lambda function to trigger on SQS queue messages
response = lambda_client.create_event_source_mapping(
  FunctionName=LAMBDA_FUNCTION_NAME,
  EventSourceArn=f'arn:aws:sqs:{AWS_REGION}:{AWS_ACCOUNT_ID}:{QUEUE_NAME}.fifo',
  BatchSize=1)

# Create a DynamoDB table
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
table = dynamodb.create_table(TableName=DYNAMODB_TABLE_NAME,
                              KeySchema=[{
                                'AttributeName': 'imageLink',
                                'KeyType': 'HASH'
                              }],
                              AttributeDefinitions=[{
                                'AttributeName': 'imageLink',
                                'AttributeType': 'S'
                              }],
                              BillingMode='PAY_PER_REQUEST')

# Create a Lambda function handler
lambda_code = '''
import json
import requests
import boto3

dynamodb = boto3.resource('dynamodb', region_name=''' + repr(AWS_REGION) + ''')
table = dynamodb.Table(''' + repr(DYNAMODB_TABLE_NAME) + ''')

def lambda_handler(event, context):
    for record in event['Records']:
        message = json.loads(record['body'])
        image_link = message['link']
        
        # Send the image link to the API
        response = requests.post('https://cloud.eyedea.cz/api/anonymizer', json={'link': image_link})
        
        # Store the response in DynamoDB
        item = {
            'imageLink': image_link,
            'response': response.json()
        }
        table.put_item(Item=item)
'''

# Save the Lambda function handler to a file
with open('lambda_function.py', 'w') as file:
  file.write(lambda_code)

print("Script execution completed!")
