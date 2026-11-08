"""
some templated scaper script at 1 Am 
assumes the website to give not be a js heavy page 
"""

import os
import sys
import requests
from pathlib import Path


BASE_PATH = Path.cwd() / "sptemplate"

REQ_DIRS = [BASE_PATH, BASE_PATH / "data", BASE_PATH / "proxies"]
REQ_FILES = [BASE_PATH / "data" / "config.json", BASE_PATH / "proxies" / "proxies.txt"]

DEFAULT_CONFIG = {
    "target_url": "https://quotes.toscrape.com/login",
    "login_url": "https://quotes.toscrape.com/login",
    "username": "admin",
    "password": "password123",
    "headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
}



def initiation() -> None:
    """
    initialization function
        sets up dir stucture 
    """
    

    for path, file in zip(REQ_DIRS, REQ_FILES):
        path.mkdir(exist_ok=True, parents=True)
        file.touch(exist_ok=True)


def load_config() -> dict:
    pass

def read_proxies() -> tuple:
    pass


def is_login_req() -> bool:
    """ check if a page needs a login of some sort """
    pass


def login_and_scrape(url: str, proxies: tuple, payload: dict) -> requests.Response | None:
    """ runs if sytem detects a login page
        returns the direct response
        only if a status code is 1**, 2** or 3**
    """
    pass

def direct_scrape(proxies: dict) -> requests.Response | None:
    pass



def save_response(response: requests.Response):
    """ checks the response content type and performs the right save method
    using helpers like _save_vid, _save_json _save_text , _save_img , save_html
    in the data path
    """


def main() -> int:
    pass


if __name__ == "__main__":
    pass