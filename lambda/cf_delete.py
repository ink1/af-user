from __future__ import print_function

import json
import urllib
import boto3

# print('Loading function')

s3 = boto3.client('s3')
cf = boto3.client('cloudformation')

def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))

    # Get the object from the event and show its content type
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.unquote_plus(event['Records'][0]['s3']['object']['key'].encode('utf8'))

    splitkey = key.split('/')

    # get user name from the object name
    uid = splitkey[1]
    # get stack name from the file name
    stackname = splitkey[-1][:-10]

    try:
        print('stack ', stackname, ' deleted')
        response = cf.delete_stack(
            StackName = stackname,
            ClientRequestToken = stackname+'stop'
        )

        newkey = key + 'd'
        copy_source = {
            'Bucket': bucket,
            'Key': key
        }

        s3.copy(copy_source, bucket, newkey)
        s3.delete_object(Bucket=bucket, Key=key)

        return response

    except Exception as e:
        print(e)
        print('Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.'.format(key, bucket))
        raise e

