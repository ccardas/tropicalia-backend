from tropicalia.app import run_server
from tropicalia import __author__, __version__

def cli():
    print(f"ver.{__version__}   author {__author__}")
    run_server()

if __name__ == "__main__":
    cli()