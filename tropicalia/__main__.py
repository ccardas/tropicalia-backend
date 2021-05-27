from tropicalia.app import run_server
from tropicalia import __author__, __version__

HEADER = "\n".join(
    [
        r" _____ ______  _____ ______  _____  _____   ___   _         _____  ___   ",
        r"|_   _|| ___ \|  _  || ___ \|_   _|/  __ \ / _ \ | |       |_   _|/ _ \  ",
        r"  | |  | |_/ /| | | || |_/ /  | |  | /  \// /_\ \| |  ______ | | / /_\ \ ",
        r"  | |  |    / | | | ||  __/   | |  | |    |  _  || | |______|| | |  _  | ",
        r"  | |  | |\ \ \ \_/ /| |     _| |_ | \__/\| | | || |____    _| |_| | | | ",
        r"  \_/  \_| \_| \___/ \_|     \___/  \____/\_| |_/\_____/    \___/\_| |_/ ",
        "                                                                          ",
        f"ver.{__version__}          author: {__author__}                          ",
    ]
)


def cli():
    print(HEADER)
    run_server()


if __name__ == "__main__":
    cli()
