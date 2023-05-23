import boto3
from urllib import request
from pyfiglet import Figlet


def print_figlet() -> None:
    """
    Print figlet ("Bastion Generator")
    :return:
    """

    figlet_title = Figlet(font='slant')

    print(figlet_title.renderText('Bastion Generator'))


def bright_red(text) -> str:
    """
    Print bright red(255, 85, 85 / #ff5555) to console.

    :param text:
    :return:
    """

    return f'\x1b[91m{text}\x1b[0m'


def bright_green(text) -> str:
    """
        Print bright green(85, 255, 85 / #55ff55) to console.

        :param text:
        :return:
    """

    return f'\x1b[92m{text}\x1b[0m'


def bright_cyan(text) -> str:
    """
        Print bright cyan(85, 255, 255 / #55ffff) to console.

        :param text:
        :return:
    """

    return f'\x1b[96m{text}\x1b[0m'


def get_my_ip() -> str:
    """
        Return my ip.

        :return:
    """

    ip = request.urlopen('https://ident.me').read().decode('utf-8')

    return f'{ip}/32'


def modify_instance_attributes(instance_id: str, region: str):
    """
        Update Instance's attiributes.

        - IMDS
        - Stop Protection

        :param instance_id:
        :param region:
        :return:
    """
    client = boto3.client('ec2', region_name=region)
    client.modify_instance_attribute(
        InstanceId=instance_id,
        DisableApiStop={
            'Value': True
        }
    )
    client.modify_instance_metadata_options(
        InstanceId=instance_id,
        HttpTokens='required',
        HttpEndpoint='enabled'
    )
