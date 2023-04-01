import socket
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

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('1.1.1.1', 443))

    return sock.getsockname()[0] + '/32'
