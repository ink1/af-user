from __future__ import print_function

import json
import urllib
import boto3
import time

# print('Loading function')

s3 = boto3.client('s3')
cf = boto3.client('cloudformation')
s = boto3.Session()
ec2 = s.resource('ec2', region_name='eu-west-2')
ses = boto3.client('ses', region_name='eu-west-1')

# location of CF template
template = 'https://s3.amazonaws.com/awsmp-fulfillment-cf-templates-prod/42f67df5-e57c-4db2-b31a-6723f002b99d.56f61d1d-38ff-40a7-9588-89b4af16a621.template'

def lambda_handler(event, context):
    print('Received event: ' + json.dumps(event, indent=2))

    # Get the object from the event and show its content type
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.unquote_plus(event['Records'][0]['s3']['object']['key'].encode('utf8'))

    splitkey = key.split('/')
    # get user name from the object name
    uid = splitkey[1]
    # get stack name from the file name
    stackname = splitkey[-1][:-10]

    # check if customization scripts are present
    custom_bucket = 'alces-flight-abcdefghijklnmop'
    custom_key = 'customizer/' + uid + '/configure.d/user.sh'
    try:
        response = s3.get_object(Bucket=custom_bucket, Key=custom_key)
    except Exception as e:
        print(e)
        print('Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.'.format(custom_key, custom_bucket))
        raise e

    # get the configuration
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
    except Exception as e:
        print(e)
        print('Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.'.format(key, bucket))
        raise e

    # parse json config
    try:
        data = json.load(response['Body'])
    except Exception as e:
        print(e)
        print('Error loading json configuration')
        raise e

    params = [
        {'ParameterKey': 'ComputeInstanceType',       'ParameterValue': 'other'},
        {'ParameterKey': 'ComputeInstanceTypeOther',  'ParameterValue': 'c4.large-2C-3.75GB'},
        {'ParameterKey': 'MasterInstanceType',        'ParameterValue': 'other'},
        {'ParameterKey': 'MasterInstanceTypeOther',   'ParameterValue': 'c4.large-2C-3.75GB'},
        {'ParameterKey': 'ComputeSpotPrice',          'ParameterValue': '0.03'},
        {'ParameterKey': 'AutoscalingPolicy',         'ParameterValue': 'enabled'},
        {'ParameterKey': 'ComputeInitialNodes',       'ParameterValue': '1'},
        {'ParameterKey': 'ComputeMaxNodes',           'ParameterValue': '4'},
        {'ParameterKey': 'MasterSystemVolumeSize',    'ParameterValue': '16'},
        {'ParameterKey': 'AccessUsername',            'ParameterValue': uid},
        {'ParameterKey': 'FlightProfiles',            'ParameterValue': uid}
    ]

    # update params according to proposed changes
    for i in params:
        k = i['ParameterKey']
        if k in data:
            i['ParameterValue'] = data[k]

    # now that we are almost ready, send email
    addr = 'admin@ac.uk'
    toEmail = addr
    fromEmail = addr
    replyTo = addr
    subject = 'AWS ' + uid + ' started ' + stackname
    message = 'key ' + key

    try:
        response = ses.send_email(
            Source=fromEmail,
            Destination={'ToAddresses': [toEmail]},
            Message={
                'Subject': {
                    'Data': subject,
                    'Charset': 'utf8'
                },
                'Body': {
                    'Text': {
                        'Data': message,
                        'Charset': 'utf8'
                    }
                }
            },
            ReplyToAddresses=[replyTo]
        )
    except Exception as e:
        print(e)
        print('Error sending email notification')
        raise e

    try:
        response = cf.create_stack(
            StackName=stackname,
            TemplateURL=template,
            Parameters=params,
            Capabilities=['CAPABILITY_IAM' ],
            Tags=[
                {'Key': 'project',   'Value': uid},
            ],
            ClientRequestToken=(stackname + 'start')
        )
    except Exception as e:
        print(e)
        print('Error starting the cluster')
        raise e

    stack_not_ready = True
    while stack_not_ready:
        time.sleep(2)
        x = cf.list_stacks(StackStatusFilter=['CREATE_COMPLETE'])
        if len(x['StackSummaries']):
            for i in x['StackSummaries']:
                if stackname in i.values():
                    stack_not_ready = False
                    break

    #  if we are here, we have the stack
    x = cf.list_stack_resources(StackName=stackname)

    for i in x['StackResourceSummaries']:
        if 'AWS::EC2::Instance' in i.values():
             instance_id = i['PhysicalResourceId']

    instance = ec2.Instance(id=instance_id)
    f = open('/tmp/' + stackname + '.txt', 'wb')
    f.write(instance.public_ip_address)
    f.close()

    f = open('/tmp/' + stackname + '.txt', 'rb')
    newkey = key + 'd'
    copy_source = {
        'Bucket': bucket,
        'Key': key
    }

    s3.put_object(Bucket=bucket, Key=newkey, Body=f)
    f.close()
    s3.delete_object(Bucket=bucket, Key=key)
    print('stack ', stackname, ' created')

