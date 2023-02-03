import os
import boto3
from botocore.config import Config
from inquirer import prompt, Confirm, Text
from datetime import datetime
from dateutil import tz
from prettytable import PrettyTable
from cfn_visualizer import visualizer

from bastion_cli.validators import stack_name_validator


class DeployCfn:
    client = None
    deploy = False
    name = ''
    region = ''

    def __init__(
            self,
            region,
    ):
        self.region = region
        self.ask_deployment()
        self.input_stack_name()
        self.deployment(self.name, region)

    def ask_deployment(self):
        questions = [
            Confirm(
                name='required',
                message='Do you want to deploy using CloudFormation in here?',
                default=True
            )
        ]

        self.deploy = prompt(questions=questions, raise_keyboard_interrupt=True)['required']

    def input_stack_name(self):
        questions = [
            Text(
                name='name',
                message='Type CloudFormation Stack name',
                validate=lambda _, x: stack_name_validator(x, self.region),
            )
        ]

        self.name = prompt(questions=questions, raise_keyboard_interrupt=True)['name']

    def deployment(self, name, region):
        if self.deploy:  # deploy using cloudformation
            self.client = boto3.client('cloudformation', config=Config(region_name=region))
            response = self.client.create_stack(
                StackName=name,
                TemplateBody=self.get_template(),
                TimeoutInMinutes=5,
                Tags=[{'Key': 'Name', 'Value': name}],
                Capabilities=['CAPABILITY_NAMED_IAM']
            )
            stack_id = response['StackId']

            while True:
                # 1. get stack status
                response = self.client.describe_stacks(
                    StackName=name
                )
                stack_status = response['Stacks'][0]['StackStatus']

                if stack_status in ['CREATE_FAILED', 'ROLLBACK_FAILED',
                                    'ROLLBACK_COMPLETE']:  # create failed
                    print()
                    print('\x1b[31m' + 'Failed!' + '\x1b[0m')
                    print()
                    print('\x1b[31m' + 'Please check CloudFormation at here:' + '\x1b[0m')
                    print()
                    print(
                        '\x1b[31m' +
                        'https://{0}.console.aws.amazon.com/cloudformation/home?region={0}#/stacks/stackinfo?stackId={1}'.format(
                            region, stack_id) +
                        '\x1b[0m')
                    break

                elif stack_status == 'CREATE_COMPLETE':  # create complete successful
                    print()
                    self.print_table()
                    self.create_key_pair()
                    print('\x1b[32m' + 'Success!' + '\x1b[0m')

                    break

                else:
                    visualizer(self.client, self.name)

        else:
            print('Done!\n\n')
            print('You can deploy Bastion EC2 using AWS CLI\n\n\n')
            print(
                'aws cloudformation deploy --stack-name {} --region {} --capabilities CAPABILITY_NAMED_IAM --template-file ./bastion.yaml'.format(
                    name, region))

    def get_template(self):
        with open('bastion.yaml', 'r') as f:
            content = f.read()

        return content

    def get_timestamp(self, timestamp: datetime):
        return timestamp.replace(tzinfo=tz.tzutc()).astimezone(tz.tzlocal()).strftime('%I:%M:%S %p')

    def get_color(self, status: str):
        if 'ROLLBACK' in status or 'FAILED' in status:
            return '31m'

        elif 'PROGRESS' in status:
            return '34m'

        elif 'COMPLETE' in status:
            return '32m'

    def print_table(self):
        table = PrettyTable()
        table.set_style(15)
        table.field_names = ['Logical ID', 'Physical ID', 'Type']
        table.vrules = 0
        table.hrules = 1
        table.align = 'l'
        rows = []

        response = self.client.describe_stack_resources(StackName=self.name)['StackResources']

        for resource in response:
            rows.append([resource['LogicalResourceId'], resource['PhysicalResourceId'], resource['ResourceType']])

        rows = sorted(rows, key=lambda x: (x[2], x[0]))
        table.add_rows(rows)
        print(table)

    def create_key_pair(self):
        home_dir = os.path.expanduser('~')
        key_location = (home_dir + '/Desktop') if os.path.exists(home_dir + '/Desktop') else home_dir

        response = self.client.describe_stacks(StackName=self.name)
        key_id = [item.get('OutputValue') for item in response['Stacks'][0]['Outputs'] if item['OutputKey'] == 'KeyId']
        key_name = [item.get('OutputValue') for item in response['Stacks'][0]['Outputs'] if
                    item['OutputKey'] == 'KeyName']

        if len(key_id):
            response = boto3.client('ssm', config=Config(region_name=self.region)).get_parameter(
                Name='/ec2/keypair/{}'.format(key_id[0]),
                WithDecryption=True
            )
            key_body = response['Parameter']['Value']

            with open(f'{key_location}/{key_name[0]}.pem', 'w') as f:
                f.write(key_body)

        else:
            pass
