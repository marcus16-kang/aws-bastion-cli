import re
import boto3
from botocore.exceptions import ClientError


def name_validator(text):
    return len(text) > 0


def instance_type_validator(text, session: boto3.Session, az):
    response = session.client('ec2') \
        .describe_instance_type_offerings(
        LocationType='availability-zone',
        Filters=[
            {'Name': 'location', 'Values': [az]},
            {'Name': 'instance-type', 'Values': [text]}
        ]
    )

    return response['InstanceTypeOfferings']


def port_validator(text):
    return re.match(pattern=r'^[0-9]{1,5}$', string=text)


def stack_name_validator(text, region, profile):
    if not len(text):
        return False

    else:
        try:
            boto3.Session(profile_name=profile, region_name=region).client('cloudformation').describe_stacks(
                StackName=text)

        except ClientError:  # stack doest
            return True

        except Exception as e:
            print(e)

            return False
