import socket
from pyfiglet import Figlet


def print_figlet():
    figlet_title = Figlet(font='slant')

    print(figlet_title.renderText('Bastion Generator'))


def bright_red(text):
    return f'\x1b[91m{text}\x1b[0m'


def bright_green(text):
    return f'\x1b[92m{text}\x1b[0m'


def bright_cyan(text):
    return f'\x1b[96m{text}\x1b[0m'


def get_my_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('1.1.1.1', 443))

    return sock.getsockname()[0] + '/32'
