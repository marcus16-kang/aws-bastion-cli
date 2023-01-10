import re
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
from botocore import session


def name_validator(text):
    return len(text) > 0


def instance_type_validator(text, region, az):
    response = session.get_session().create_client('ec2', config=Config(region_name=region)) \
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


def stack_name_validator(text, region):
    if not len(text):
        return False

    else:
        try:
            boto3.client('cloudformation', config=Config(region_name=region)).describe_stacks(StackName=text)

        except ClientError:  # stack doest
            return True

        except Exception as e:
            print(e)

            return False
