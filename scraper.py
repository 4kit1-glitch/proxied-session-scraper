"""
some templated scaper script at 1 Am 
"""


import requests
from pathlib import Path


BASE_PATH = Path.cwd() / "sptemplate"

REQ_DIRS = [BASE_PATH, BASE_PATH / "data", BASE_PATH / "proxies"]
REQ_FILES = [BASE_PATH / "data" / "config.json", BASE_PATH / "proxies" / "proxies.txt"]


def initiation() -> None:
    """
    initialization function
        sets up dir stucture 
    """
    

    for path, file in zip(REQ_DIRS, REQ_FILES):
        path.mkdir(exist_ok=True, parents=True)
        file.touch(exist_ok=True)

    

