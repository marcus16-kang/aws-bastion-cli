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
