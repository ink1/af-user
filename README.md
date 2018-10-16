Update: As of 10 Oct 2018, AWS Lambda can run up to 15 min (Hooray!) and therefore this max value should be used when setting 
up cf-create lambda below instead of 5 min as before:
```
Basic settings - Timeout: 15 mins
```

# Quick start guide

[Further details and background](https://www.slideshare.net/IgorKozin/running-hpc-workloads-on-aws-using-alces-flight)

This quick start guide is for setting up an unprivileged AWS user for running Alces Flight (AF) clusters on Amazon cloud.
Instead of giving the privileges required to start a cluster to a user, we will give them to AWS Lambdas and use trigers to activate them.

* AWS trigger: watch for *.cf-create and *.cf-delete files in S3 bucket belonging to users
* CLUSTERNAME.cf-create triggers AWS Lambda which
  1. Extracts the user name from the file path
  1. Starts CloudFormation stack merging the short JSON configuration into a larger default CloudFormation template
  1. The stack is associated with the user and tagged with USER tag
  1. Deletes CLUSTERNAME.cf-create and puts login IP address into CLUSTERNAME.cf-created
  1. Sends an email notification to the administrator
* CLUSTERNAME.cf-delete triggers AWS Lambda which
  1. Kills the CloudFormation stack
  1. Deletes CLUSTERNAME.cf-delete and creates CLUSTERNAME.cf-deleted
* Unfortunately Lambda is currently limited to 5 mins and therefore the configuration file has to be re-issued; this does not lead to a problem because the stack name is unique (it has to be)

The cluster configuration exposed to the users is really simple and allows them to get on with their job quickly.
Here is an example of a cluster configuration file (.cf-create is a JSON file):
```
{
    "ComputeInstanceType": "other", 
    "ComputeSpotPrice": "0.03", 
    "ComputeInstanceTypeOther": "r4.large-2C-15.25GB", 
    "MasterSystemVolumeSize": "16", 
    "MasterInstanceType": "other", 
    "ComputeMaxNodes": "25", 
    "MasterInstanceTypeOther": "r4.large-2C-15.25GB", 
    "ComputeInitialNodes": "0", 
    "AutoscalingPolicy": "enabled"
}
```

The content of cf-delete file is not read and it can be blank.

Cluster image customisation scripts are located in a special bucket in ```customizer/default/configure.d``` (see examples in this repo).
They may be adapted as necessary. 
Furthermore, user specific customisation can be created in ```customizer/<USERID>/configure.d``` and, in fact, it has to be provided for [cf-create.py lambda to work](https://github.com/ink1/af-user/blob/master/lambda/cf_create.py#L34). 
There is nothing preventing you to expose these configuration scripts to the users if necessary.

# Installation

## Create S3 bucket

Create a bucket which will be used by your users. We create "AF-users-eu-west-2" in eu-west-2 region.
The region in our name is simply reflective of where the bucket is.
You should use a different name and any region.
Obviously it makes sense to create the bucket in the region you are planning to run clusters.

## Create IAM Policy for user access to S3

Edit AFS3UserAccess.json and replace all occurences of "AF-users-eu-west-2" with your own bucket name. E.g.
```
"arn:aws:s3:::AF-users-eu-west-2"
```
will become
```
"arn:aws:s3:::my-bucket"
```
Note that multiple buckets can be given as a list.

Go to AIM console, select Policies and then Create policy called AFS3UserAccess. Paste the content of your json file and save.

We assume you already have at least one user (if not, create a test user). Select Users, then a particular user or group.
Click Add permision, select Attach existing policies directly and attach the policy AFS3UserAccess you just created.

Check that as this user you have access to files and folders below "/home/${aws:username}/"

## Create lambda rule and related policy

Edit AFClusterManager.json and 
* replace all occurences of "AF-users-eu-west-2" with your own bucket name.
* replace 123456789012 with your own AWS account number
* optionally change the region where the logs are created

Go to AIM console, select Policies and then Create policy called AFClusterManager.
Paste the content of AFClusterManager.json there.

While still in AIM console, go to Roles and create 'lambda-cloudformation-role'. 
Add the policy AFClusterManager you just created.

## Start Alces Flight cluster

When AF cluster starts for the first time, it creates a special bucket to keep all its configuration files.
Unfortunately it is hard to predict the bucket's name because it contains a hash.
In order to proceed further you need to have this bucket.
If you have already run an AF cluster before, you should have this bucket already.
Just inspect your S3 buckets.
The easiest way to create this bucket is to start AF cluster at least once.
If you are unfamiliar with Alces Flight [go here](https://alces-flight.com/start).
Or go straight to [Alces Flight Solo on AWS](https://aws.amazon.com/marketplace/pp/B01GC9E3OG).

We will assume that our AF bucket is called "alces-flight-abcdefghijklnmop"

## Cluster customization

Your AF bucket probably contains the following folders "/customizer/default/configure.d/".
Folder "alces-flight-abcdefghijklnmop" in this repo contains customization scripts which you need to adapt to your user needs.
Each AF cluster user we are going to setup needs a directory under "/customizer/".
We use "default" folder to contain essential templates but not to provide behaviour for users who don't have user folders.
Firstly, having a user folder is one extra security mechanism which restricts who can start an AF cluster.
Secondly, the scripts there perform ssh key injection specific to the user.

Create a directory under "/customizer/" using the user name you are setting up.
Copy the files from "/customizer/default/".
Edit file "configure.d/user.sh" and put correct user id and ssh key.

Other user specific customisation scripts can be also added to "configure.d".

## Register for SES (Optional)

[Amazon Simple Email Service](https://aws.amazon.com/ses/) (SES) provides simple notification mechanism via emails.
It can be used to notify administrators (and users) of actions being performed.
You need to register either your domain or specific email addresses before using them.
If you want to use SES notifications, open lambda/cf_create.py and replace 'admin@ac.uk' with your email address.
If not, comment out the 'try' block related to SES.

## Lambda customisation and setup

Two Python 2.7 lambda functions are provided in folder lambda: one for creation of CloudFormation stack and one for deletion.
You need to adapt 'cf_create.py' to your needs.

1. Change 'ec2' variable to reflect the region you want to start your clusters in; 'ses' region can be changed too but needs to be a region with SES service.
1. Replace 'template' variable with your own customised template (optional)
1. Set 'custom_bucket' to your own bucket replacing "alces-flight-abcdefghijklnmop"
1. Set 'addr' to your own email notification address

### cf-create lambda

Go to AWS Lambda console and create 'cf-create' function with S3 trigger monitoring your user bucket ("AF-users-eu-west-2" in our case) for 'cf-create' suffix.

* Suffix: cf-create
* Prefix: home/
* Event type: ObjectCreated
* Runtime - Python 2.7.
* Add the code from cf-create.py (leave handler as lambda_function.lambda_handler).
* Execution role - Existing role: lambda-cloudformation-role
* Basic settings - Timeout: 15 mins
* Save

### cf-delete lambda

Similarly create 'cf-delete' function with S3 trigger monitoring your user bucket for 'cf-delete' suffix.

* Suffix: cf-delete
* Prefix: home/
* Event type: ObjectCreated
* Runtime - Python 2.7
* Add the code from cf-delete.py (leave handler as lambda_function.lambda_handler)
* Execution role - Existing role: lambda-cloudformation-role
* Basic settings - Timeout: 1 min
* Save
