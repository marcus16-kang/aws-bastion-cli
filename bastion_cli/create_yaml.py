import os
import yaml

from botocore import session
from botocore.config import Config


class CreateYAML:
    template = {}
    resources = {}
    outputs = {}
    project = ''
    ami = None

    def __init__(
            self,
            project,
            region,
            vpc,
            subnet,
            instance_name,
            instance_type,
            eip,
            sg,
            role,
            port,
            new_key_name=None,
            key_name=None,
            password=None,
    ):
        self.project = project
        self.get_ami(region=region, instance_type=instance_type)
        self.create_role(role=role)
        self.create_sg(vpc=vpc, sg=sg, port=port)
        self.create_instance(subnet=subnet, instance_name=instance_name, instance_type=instance_type, port=port,
                             new_key_name=new_key_name, key_name=key_name, password=password)
        self.create_eip(eip=eip)
        self.create_outputs(port=port, password=password, new_key_name=new_key_name, key_name=key_name)
        self.create_yaml()

    def get_ami(self, region, instance_type):
        arch = session.get_session().create_client('ec2', config=Config(region_name='us-east-1')) \
            .describe_instance_types(
            InstanceTypes=[instance_type]
        )['InstanceTypes'][0]['ProcessorInfo']['SupportedArchitectures'][-1]
        ami = session.get_session().create_client('ssm', config=Config(region_name=region)).get_parameter(
            Name=f'/aws/service/ami-amazon-linux-latest/amzn2-ami-kernel-5.10-hvm-{arch}-gp2'
        )['Parameter']['Value']

        self.ami = ami

    def create_role(self, role):
        self.resources['Role'] = {
            'Type': 'AWS::IAM::Role',
            'Properties': {
                'AssumeRolePolicyDocument': {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Principal': {
                                'Service': [
                                    'ec2.amazonaws.com'
                                ]
                            },
                            'Action': [
                                'sts:AssumeRole'
                            ]
                        }
                    ]
                },
                'Description': 'Bastion EC2 Role',
                'ManagedPolicyArns': [
                    'arn:aws:iam::aws:policy/AdministratorAccess'
                ],
                'Path': '/',
                'RoleName': role,
                'Tags': [{'Key': 'Name', 'Value': role}, {'Key': 'project', 'Value': self.project}]
            }
        }

        self.resources['InstanceProfile'] = {
            'Type': 'AWS::IAM::InstanceProfile',
            'Properties': {
                'InstanceProfileName': role,
                'Path': '/',
                'Roles': [{'Ref': 'Role'}]
            }
        }

    def create_sg(self, vpc, sg, port):
        self.resources['SG'] = {
            'Type': 'AWS::EC2::SecurityGroup',
            'Properties': {
                'GroupDescription': sg,
                'GroupName': sg,
                'SecurityGroupEgress': [{
                    'IpProtocol': '-1',
                    'CidrIp': '0.0.0.0/0'
                }],
                'SecurityGroupIngress': [{
                    'IpProtocol': 'tcp',
                    'FromPort': port,
                    'ToPort': port,
                    'CidrIp': '0.0.0.0/0',
                    'Description': 'SSH'
                }],
                'Tags': [{'Key': 'Name', 'Value': sg}, {'Key': 'project', 'Value': self.project}],
                'VpcId': vpc
            }
        }

    def create_instance(self, subnet, instance_name, instance_type, port, new_key_name, key_name, password):
        self.resources['Instance'] = {
            'Type': 'AWS::EC2::Instance',
            'Properties': {
                'IamInstanceProfile': {
                    'Ref': 'InstanceProfile'
                },
                'ImageId': self.ami,
                'SecurityGroupIds': [
                    {
                        'Fn::GetAtt': 'SG.GroupId'
                    }
                ],
                'SubnetId': subnet,
                'InstanceType': instance_type,
                'DisableApiTermination': True,
                'Tags': [{'Key': 'Name', 'Value': instance_name}, {'Key': 'project', 'Value': self.project}],
            }
        }

        if new_key_name:  # use new key
            self.resources['Key'] = {
                'Type': 'AWS::EC2::KeyPair',
                'Properties': {
                    'KeyName': new_key_name,
                    'Tags': [{'Key': 'Name', 'Value': new_key_name}, {'Key': 'project', 'Value': self.project}],
                }
            }
            self.resources['Instance']['Properties']['KeyName'] = {
                'Ref': 'Key'
            }
            self.outputs['KeyId'] = {
                'Value': {
                    'Fn::GetAtt': 'Key.KeyPairId'
                }
            }
            self.outputs['KeyName'] = {
                'Value': {
                    'Ref': 'Key'
                }
            }
            self.resources['Instance']['Properties']['UserData'] = {
                'Fn::Base64': {
                    'Fn::Join': [
                        "", [
                            "#!/bin/bash\n",
                            f"echo Port {port} >> /etc/ssh/sshd_config\n",
                            "systemctl restart sshd\n"
                        ]
                    ]
                }
            }

        elif key_name:  # use already exists key
            self.resources['Instance']['Properties']['KeyName'] = key_name
            self.resources['Instance']['Properties']['UserData'] = {
                'Fn::Base64': {
                    'Fn::Join': [
                        "", [
                            "#!/bin/bash\n",
                            f"echo Port {port} >> /etc/ssh/sshd_config\n",
                            "systemctl restart sshd\n"
                        ]
                    ]
                }
            }

        elif password:  # use password
            self.resources['Instance']['Properties']['UserData'] = {
                'Fn::Base64': {
                    'Fn::Join': [
                        "", [
                            "#!/bin/bash\n",
                            "sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config\n",
                            f"echo {password} | passwd --stdin ec2-user\n",
                            f"echo Port {port} >> /etc/ssh/sshd_config\n",
                            "systemctl restart sshd\n"
                        ]
                    ]
                }
            }

    def create_eip(self, eip):
        self.resources['EIP'] = {
            'Type': 'AWS::EC2::EIP',
            'Properties': {
                'Tags': [{'Key': 'Name', 'Value': eip}, {'Key': 'project', 'Value': self.project}]
            }
        }

        self.resources['EIPAssociation'] = {
            'Type': 'AWS::EC2::EIPAssociation',
            'Properties': {
                'AllocationId': {
                    'Fn::GetAtt': 'EIP.AllocationId'
                },
                'InstanceId': {
                    'Ref': 'Instance'
                }
            }
        }

    def create_outputs(self, port, password, new_key_name, key_name):
        home_dir = os.path.expanduser('~')
        key_location = (home_dir + '/Desktop') if os.path.exists(home_dir + '/Desktop') else home_dir

        self.outputs['SSHCommand'] = {
            'Value': {
                'Fn::Sub': [
                    '',
                    {
                        'IP': {
                            'Ref': 'EIP'
                        }
                    }
                ]
            }
        }
        self.outputs['PuttyCommand'] = {
            'Value': {
                'Fn::Sub': [
                    '',
                    {
                        'IP': {
                            'Ref': 'EIP'
                        }
                    }
                ]
            }
        }
        self.outputs['SSHPassword'] = {}

        if new_key_name:
            key_name = new_key_name

        if key_name:
            self.outputs['SSHCommand']['Value']['Fn::Sub'][0] = \
                f'ssh -i {key_location}/{key_name}.pem -p {port} ec2-user@${{IP}}'
            self.outputs['PuttyCommand']['Value']['Fn::Sub'][0] = \
                f'ssh -i {key_location}/{key_name}.ppk -p {port} ec2-user@${{IP}}'
            self.outputs.pop('SSHPassword', None)

        elif password:
            self.outputs['SSHCommand']['Value']['Fn::Sub'][0] = \
                f'ssh -p {port} ec2-user@${{IP}}'
            self.outputs['PuttyCommand']['Value']['Fn::Sub'][0] = \
                f'ssh -pw {password} -p {port} ec2-user@${{IP}}'
            self.outputs['SSHPassword']['Value'] = password

    def create_yaml(self):
        template = {
            'AWSTemplateFormatVersion': '2010-09-09',
            'Description': 'Bastion Generator CLI',
            'Resources': self.resources,
            'Outputs': self.outputs
        }

        try:
            with open('bastion.yaml', 'w') as f:
                yaml.dump(template, f)

            self.template = template

        except Exception as e:
            print(e)

    def get_template_body(self):
        return self.template
