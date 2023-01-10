from pyfiglet import Figlet


def print_figlet():
    figlet_title = Figlet(font='slant')

    print(figlet_title.renderText('Bastion Generator'))
