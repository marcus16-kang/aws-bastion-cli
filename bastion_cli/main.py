import sys
import argparse

from bastion_cli.command import Command
from bastion_cli import VERSION


def get_arguments() -> dict:
    """
    Get arguments for cli.

    :return: dict
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--profile', dest='profile', action='store', default='default',
                        help='use aws credential profile.')
    parser.add_argument('-v', '--version', action='version', version=f'bastion-cli v{VERSION}')

    args = parser.parse_args()
    profile = args.profile

    return {'profile': profile}


def main():
    """
    Main function.

    :return:
    """
    try:
        options = get_arguments()

        Command(options['profile'])

    except KeyboardInterrupt:
        print('Cancelled by user.')
        sys.exit()


if __name__ == '__main__':
    main()
