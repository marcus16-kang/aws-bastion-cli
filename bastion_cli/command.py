import boto3
from inquirer import prompt, List, Text

from botocore.config import Config
from botocore import session

from bastion_cli.create_yaml import CreateYAML
from bastion_cli.utils import print_figlet
from bastion_cli.validators import name_validator, instance_type_validator, port_validator
from bastion_cli.deploy_cfn import DeployCfn


class Command:
    # variables
    project = None
    region = None
    vpc = None
    subnet = None
    az = None
    instance_name = None
    instance_type = None
    eip = None
    sg = None
    role = None
    port = None
    new_key_name = None
    key_name = None
    password = None

    def __init__(self):
        print_figlet()

        self.set_project_name()
        self.choose_region()

        self.choose_vpc()
        if not self.vpc:  # no vpc found in that region
            return

        self.choose_subnet()
        if not self.subnet:
            return

        self.get_instance_name()

        self.get_instance_type()
        if not self.instance_type:
            return

        self.get_eip_name()
        self.get_sg_name()
        self.get_role_name()
        self.get_ssh_port()
        self.get_authentication()

        # create template yaml file
        yaml_file = CreateYAML(
            project=self.project,
            region=self.region,
            vpc=self.vpc,
            subnet=self.subnet,
            instance_name=self.instance_name,
            instance_type=self.instance_type,
            eip=self.eip,
            sg=self.sg,
            role=self.role,
            port=self.port,
            new_key_name=self.new_key_name,
            key_name=self.key_name,
            password=self.password,
        )
        yaml_file.create_yaml()

        DeployCfn(region=self.region)

    def set_project_name(self):
        questions = [
            Text(
                name='name',
                message='Project name',
                validate=lambda _, x: name_validator(x)
            )
        ]

        answer = prompt(questions=questions, raise_keyboard_interrupt=True)
        self.project = answer['name']

    def choose_region(self):
        questions = [
            List(
                name='region',
                message='Choose region',
                choices=[
                    ('us-east-1      (N. Virginia)', 'us-east-1'),
                    ('us-east-2      (Ohio)', 'us-east-2'),
                    ('us-west-1      (N. California)', 'us-west-1'),
                    ('us-west-2      (Oregon)', 'us-west-2'),
                    ('ap-south-1     (Mumbai)', 'ap-south-1'),
                    ('ap-northeast-3 (Osaka)', 'ap-northeast-3'),
                    ('ap-northeast-2 (Seoul)', 'ap-northeast-2'),
                    ('ap-southeast-1 (Singapore)', 'ap-southeast-1'),
                    ('ap-southeast-2 (Sydney)', 'ap-southeast-2'),
                    ('ap-northeast-1 (Tokyo)', 'ap-northeast-1'),
                    ('ca-central-1   (Canada Central)', 'ca-central-1'),
                    ('eu-central-1   (Frankfurt)', 'eu-central-1'),
                    ('eu-west-1      (Ireland)', 'eu-west-1'),
                    ('eu-west-2      (London)', 'eu-west-2'),
                    ('eu-west-3      (Paris)', 'eu-west-3'),
                    ('eu-north-1     (Stockholm)', 'eu-north-1'),
                    ('sa-east-1      (Sao Paulo)', 'sa-east-1')
                ]
            )
        ]

        answer = prompt(questions=questions, raise_keyboard_interrupt=True)
        self.region = answer.get('region')

    def choose_vpc(self):
        response = session.get_session().create_client('ec2', config=Config(region_name=self.region)).describe_vpcs()

        if not response['Vpcs']:  # no vpc found in that region
            print('There\'s no any vpcs. Try another region.')

            return

        else:
            vpc_list = []

            for vpc in response['Vpcs']:
                vpc_id = vpc['VpcId']
                cidr = vpc['CidrBlock']
                name = next((item['Value'] for item in vpc.get('Tags', {}) if item['Key'] == 'Name'), None)

                vpc_show_data = f'{vpc_id} ({cidr}{f", {name}" if name else ""})'
                vpc_list.append((vpc_show_data, vpc_id))

            questions = [
                List(
                    name='vpc',
                    message='Choose vpc',
                    choices=vpc_list
                )
            ]

            answer = prompt(questions=questions, raise_keyboard_interrupt=True)
            self.vpc = answer.get('vpc')

    def choose_subnet(self):
        response = session.get_session().create_client('ec2', config=Config(region_name=self.region)).describe_subnets(
            Filters=[{'Name': 'vpc-id', 'Values': [self.vpc]}]
        )

        if not response['Subnets']:  # no vpc found in that region
            print('There\'s no any subnets. Try another vpc.')

            return

        else:
            subnet_list = []

            for subnet in response['Subnets']:
                subnet_id = subnet['SubnetId']
                az = subnet['AvailabilityZone']
                cidr = subnet['CidrBlock']
                name = next((item['Value'] for item in subnet.get('Tags', {}) if item['Key'] == 'Name'), None)

                subnet_show_data = f'{subnet_id} ({cidr}, {az}{f", {name}" if name else ""})'
                subnet_list.append((subnet_show_data, (subnet_id, az)))

            questions = [
                List(
                    name='subnet',
                    message='Choose subnet',
                    choices=subnet_list
                )
            ]

            answer = prompt(questions=questions, raise_keyboard_interrupt=True)
            self.subnet = answer.get('subnet')[0]
            self.az = answer.get('subnet')[1]
            # print(answer, self.subnet, self.az)

    def get_instance_name(self):
        questions = [
            Text(
                name='name',
                message='Enter the instance name',
                validate=lambda _, x: name_validator(x)
            )
        ]

        answer = prompt(questions=questions, raise_keyboard_interrupt=True)
        self.instance_name = answer.get('name')

    def get_instance_type(self):
        questions = [
            Text(
                name='type',
                message='Enter the instance type',
                validate=lambda _, x: instance_type_validator(x, self.region, self.az)
            )
        ]

        answer = prompt(questions=questions, raise_keyboard_interrupt=True)
        instance_type = answer.get('type')

        self.instance_type = instance_type

    def get_eip_name(self):
        questions = [
            Text(
                name='name',
                message='Enter the elastic ip name',
                validate=lambda _, x: name_validator(x)
            )
        ]

        answer = prompt(questions=questions, raise_keyboard_interrupt=True)
        self.eip = answer.get('name')

    def get_sg_name(self):
        questions = [
            Text(
                name='name',
                message='Enter the security group name',
                validate=lambda _, x: name_validator(x)
            )
        ]

        answer = prompt(questions=questions, raise_keyboard_interrupt=True)
        self.sg = answer.get('name')

    def get_role_name(self):
        questions = [
            Text(
                name='name',
                message='Enter the IAM role name',
                validate=lambda _, x: name_validator(x)
            )
        ]

        answer = prompt(questions=questions, raise_keyboard_interrupt=True)
        self.role = answer.get('name')

    def get_ssh_port(self):
        questions = [
            Text(
                name='port',
                message='Enter the SSH port number',
                validate=lambda _, x: port_validator(x),
                default='22'
            )
        ]

        answer = prompt(questions=questions, raise_keyboard_interrupt=True)
        self.port = int(answer.get('port'))

    def get_authentication(self):
        choices = [item['KeyName'] for item in
                   boto3.client('ec2', config=Config(region_name=self.region)).describe_key_pairs()['KeyPairs']]
        choices.append(('Create a new key pair', 'new'))
        choices.append(('Use a password', 'password'))

        question = [
            List(
                name='method',
                message='What method do you want to access EC2 instance?',
                choices=choices
            )
        ]
        answer = prompt(questions=question)
        if answer.get('method') == 'new':
            questions = [
                Text(
                    name='keyname',
                    message='Enter the new key name',
                    validate=lambda _, x: name_validator(x)
                )
            ]
            answer = prompt(questions=questions, raise_keyboard_interrupt=True)
            self.new_key_name = answer.get('keyname')

        elif answer.get('method') == 'password':
            questions = [
                Text(
                    name='password',
                    message='Enter the SSH password',
                    validate=lambda _, x: name_validator(x)
                )
            ]

            answer = prompt(questions=questions, raise_keyboard_interrupt=True)
            self.password = answer.get('password')

        else:
            self.key_name = answer.get('method')
