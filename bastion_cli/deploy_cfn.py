import boto3
from botocore.config import Config
from inquirer import prompt, Confirm, Text
from datetime import datetime
from dateutil import tz
from prettytable import PrettyTable
from cfn_visualizer import visualizer

from bastion_cli.validators import stack_name_validator
from bastion_cli.utils import bright_green, bright_red, modify_instance_attributes


class DeployCfn:
    client = None
    deploy = False
    name = ''
    region = ''
    profile = ''

    def __init__(
            self,
            region,
            profile,
    ):
        self.region = region
        self.profile = profile
        self.ask_deployment()
        self.input_stack_name()
        self.deployment(self.name, region, profile)

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
                validate=lambda _, x: stack_name_validator(x, self.region, self.profile),
            )
        ]

        self.name = prompt(questions=questions, raise_keyboard_interrupt=True)['name']

    def deployment(self, name, region, profile):
        if self.deploy:  # deploy using cloudformation
            self.client = boto3.Session(profile_name=profile, region_name=region).client('cloudformation')
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
                    print(f'\n{bright_red("Failed!")}\n')
                    print(f'{bright_red("Please check CloudFormation at here:")}\n')
                    print(
                        f'{bright_red(f"https://{region}.console.aws.amazon.com/cloudformation/home?region={region}#/stacks/stackinfo?stackId={stack_id}")}\n')
                    break

                elif stack_status == 'CREATE_COMPLETE':  # create complete successful
                    modify_instance_attributes(self.get_instance_id(), region)
                    self.print_table()
                    self.create_key_pair()
                    print(bright_green('Success!'))

                    break

                else:
                    visualizer(self.client, self.name)

        else:
            print(f'{bright_green("Done!")}\n\n')
            print(f'{bright_green("You can deploy Bastion EC2 using AWS CLI")}')
            print(
                f'{bright_green(f"aws cloudformation deploy --stack-name {name} --region {region} --capabilities CAPABILITY_NAMED_IAM --template-file ./bastion.yaml")}')

    def get_template(self):
        with open('bastion.yaml', 'r') as f:
            content = f.read()

        return content

    def get_timestamp(self, timestamp: datetime):
        return timestamp.replace(tzinfo=tz.tzutc()).astimezone(tz.tzlocal()).strftime('%I:%M:%S %p')

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

            with open(f'{key_name[0]}.pem', 'w') as f:
                f.write(key_body)

        else:
            pass

    def get_instance_id(self):
        response = self.client.describe_stacks(StackName=self.name)
        instance_id = [item.get('OutputValue') for item in response['Stacks'][0]['Outputs'] if
                       item['OutputKey'] == 'InstanceId'][0]

        return instance_id
