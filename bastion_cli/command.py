import sys

import boto3
import ipaddress
from inquirer import prompt, List, Text

from botocore.exceptions import ProfileNotFound

from bastion_cli.create_yaml import CreateYAML
from bastion_cli.utils import print_figlet, bright_cyan, get_my_ip
from bastion_cli.validators import name_validator, instance_type_validator, port_validator
from bastion_cli.deploy_cfn import DeployCfn


class Command:
    """
    Get values from cli.
    """
    # variables
    session: boto3.Session = None
    profile: str = None
    project: str = None
    region: str = None
    vpc = None
    subnet = None
    az = None
    instance_name = None
    instance_type = None
    eip = None
    sg = None
    role = {
        'name': None,
        'create': False
    }
    host = None
    port = None
    new_key_name = None
    key_name = None
    password = None

    def __init__(self, profile):
        print_figlet()

        self.create_boto3_session(profile)
        self.print_profile(profile)

        self.set_project_name()
        self.choose_region(profile)

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
        self.get_ssh_host()
        self.get_ssh_port()
        self.get_authentication()
        self.get_role_name()

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
            host=self.host,
            port=self.port,
            new_key_name=self.new_key_name,
            key_name=self.key_name,
            password=self.password,
        )
        yaml_file.create_yaml()

        DeployCfn(region=self.region, profile=profile)

    def create_boto3_session(self, profile='default') -> None:
        """
        Create boto3 session before query using profile argument.

        :param profile:
        :return:
        """

        try:
            self.session = boto3.session.Session(profile_name=profile)

        except ProfileNotFound as e:
            print(e)

            sys.exit(1)

    def print_profile(self, profile='default') -> None:
        """
        Print profile to console.

        :param profile:
        :return:
        """

        print(f'Using AWS Profile {bright_cyan(profile)}')

    def set_project_name(self) -> None:
        """
        Set project name.

        :return:
        """

        questions = [
            Text(
                name='name',
                message='Project name',
                validate=lambda _, x: name_validator(x)
            )
        ]

        answer = prompt(questions=questions, raise_keyboard_interrupt=True)
        self.project = answer['name']

    def choose_region(self, profile) -> None:
        """
        Choose region and create a new session using region name in hard-coded region list.

        :param profile:
        :return:
        """

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
        self.session = boto3.Session(profile_name=profile, region_name=self.region)

    def choose_vpc(self) -> None:
        """
        Choose vpc from chosen region's vpcs.

        It shows sorted vpc list (cidr, id, name).

        :return:
        """

        response = self.session.client('ec2').describe_vpcs()

        if not response['Vpcs']:  # no vpc found in that region
            print("There's no any vpcs. Try another region.")

            return

        else:
            vpc_list = []
            vpc_show_list = []

            for vpc in response['Vpcs']:
                vpc_id = vpc['VpcId']
                cidr = vpc['CidrBlock']
                name = next((item['Value'] for item in vpc.get('Tags', {}) if item['Key'] == 'Name'), None)

                vpc_list.append((vpc_id, cidr, name))

            for vpc in sorted(vpc_list, key=lambda x: (x[1], x[0], x[2])):
                vpc_show_data = f'''{vpc[0]} ({vpc[1]}{f", {vpc[2]}" if vpc[2] else ""})'''
                vpc_show_list.append((vpc_show_data, vpc[0]))

            questions = [
                List(
                    name='vpc',
                    message='Choose vpc',
                    choices=vpc_show_list
                )
            ]

            answer = prompt(questions=questions, raise_keyboard_interrupt=True)
            self.vpc = answer.get('vpc')

    def choose_subnet(self) -> None:
        """
        Choose subnet from chosen region's subnets.

        It shows sorted subnet list (cidr, az, name, id).

        :return:
        """

        response = self.session.client('ec2').describe_subnets(
            Filters=[{'Name': 'vpc-id', 'Values': [self.vpc]}]
        )

        if not response['Subnets']:  # no vpc found in that region
            print("There's no any subnets. Try another vpc.")

            return

        else:
            subnet_list = []
            subnet_show_list = []

            for subnet in response['Subnets']:
                subnet_id = subnet['SubnetId']
                az = subnet['AvailabilityZone']
                cidr = subnet['CidrBlock']
                name = next((item['Value'] for item in subnet.get('Tags', {}) if item['Key'] == 'Name'), None)

                subnet_list.append((subnet_id, az, cidr, name))

            subnet_list = sorted(subnet_list,
                                 key=lambda x: (list(ipaddress.IPv4Network(x[2]).hosts())[0]._ip, x[1], x[3], x[0]),
                                 reverse=False)

            # for subnet in sorted(subnet_list, key=lambda x: (x[0])):
            for subnet in subnet_list:
                subnet_show_data = f'''{subnet[0]} ({subnet[2]}, {subnet[1]}{f", {subnet[3]}" if subnet[3] else ""})'''
                subnet_show_list.append((subnet_show_data, (subnet[0], subnet[1])))

            questions = [
                List(
                    name='subnet',
                    message='Choose subnet',
                    choices=subnet_show_list
                )
            ]

            answer = prompt(questions=questions, raise_keyboard_interrupt=True)
            self.subnet = answer.get('subnet')[0]
            self.az = answer.get('subnet')[1]

    def get_instance_name(self) -> None:
        """
        Type the EC2 instance's name.

        :return:
        """

        questions = [
            Text(
                name='name',
                message='Enter the instance name',
                validate=lambda _, x: name_validator(x)
            )
        ]

        answer = prompt(questions=questions, raise_keyboard_interrupt=True)
        self.instance_name = answer.get('name')

    def get_instance_type(self) -> None:
        """
        Type the EC2 instance's instance type.

        Validate the instance type using AWS SDK.

        :return:
        """

        questions = [
            Text(
                name='type',
                message='Enter the instance type',
                validate=lambda _, x: instance_type_validator(x, self.session, self.az)
            )
        ]

        answer = prompt(questions=questions, raise_keyboard_interrupt=True)
        instance_type = answer.get('type')

        self.instance_type = instance_type

    def get_eip_name(self) -> None:
        """
        Type the Elastic IP name.

        :return:
        """

        questions = [
            Text(
                name='name',
                message='Enter the elastic ip name',
                validate=lambda _, x: name_validator(x)
            )
        ]

        answer = prompt(questions=questions, raise_keyboard_interrupt=True)
        self.eip = answer.get('name')

    def get_sg_name(self) -> None:
        """
        Type the Security Group name.

        :return:
        """

        questions = [
            Text(
                name='name',
                message='Enter the security group name',
                validate=lambda _, x: name_validator(x)
            )
        ]

        answer = prompt(questions=questions, raise_keyboard_interrupt=True)
        self.sg = answer.get('name')

    def get_role_name(self) -> None:
        """
        Choose the IAM role in list, or get a role name for creating a new role.

        :return:
        """

        response = self.session.client('iam').list_instance_profiles()
        instance_profile_list = ['None', 'Create a new role']

        for profile in response['InstanceProfiles']:
            for role in profile['Roles']:
                instance_profile_list.append(
                    (f"{profile['InstanceProfileName']} ({role['RoleName']})", f"{profile['InstanceProfileName']}"))

        questions = [
            List(
                name='name',
                message='Choose the IAM role',
                carousel=False,
                choices=instance_profile_list,
                other=False
            )
        ]
        answer = prompt(questions=questions, raise_keyboard_interrupt=True)

        if answer['name'] == 'None':
            self.role = {
                'name': None,
                'create': False
            }

        elif answer['name'] == 'Create a new role':
            questions = [
                Text(
                    name='name',
                    message='Enter the IAM role name',
                    validate=lambda _, x: name_validator(x)
                )
            ]

            answer = prompt(questions=questions, raise_keyboard_interrupt=True)

            self.role = {
                'name': answer.get('name'),
                'create': True
            }

        else:
            self.role = {
                'name': answer.get('name'),
                'create': False
            }

    def get_ssh_host(self) -> None:
        """
        Choose the SSH host (my ip, any open, or type any cidr format.)

        :return:
        """

        questions = [
            List(
                name='host',
                message='Choose the SSH inbound source',
                choices=[
                    get_my_ip(),
                    '0.0.0.0/0',
                ],
                carousel=True,
                other=True
            )
        ]
        answer = prompt(questions=questions, raise_keyboard_interrupt=True)
        self.host = answer.get('host').replace(' ', '').split(',')

    def get_ssh_port(self):
        # TODO: Create JSDoc.
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
                   self.session.client('ec2').describe_key_pairs()['KeyPairs']]
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
