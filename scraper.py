"""
Templated scraper script.
Assumes the target website is not a JS-heavy Single Page Application.
"""

import sys
import json
import random
import requests
from bs4 import BeautifulSoup
from pathlib import Path


BASE_PATH = Path.cwd() / "sptemplate"
REQ_DIRS = [BASE_PATH, BASE_PATH / "data", BASE_PATH / "proxies"]
CONFIG_FILE = BASE_PATH / "data" / "config.json"
PROXIES_FILE = BASE_PATH / "proxies" / "proxies.txt"
REQ_FILES = [CONFIG_FILE, PROXIES_FILE]

DEFAULT_CONFIG = {
    "target_url": "https://quotes.toscrape.com/",
    "login_url": "https://quotes.toscrape.com/login",
    "username": "admin",
    "password": "password123",
    "login_verify_method": "text",
    "login_success_text": "Logout",
    "login_success_url": "", 
    "headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
}

DEFAULT_PROXIES = (
    "http://1.1.1.1:8080",
    "http://2.2.2.2:8080"
)

FAILURE_KEYWORDS = ("login", "signin", "sign-in", "signup", "sign-up", "register", "auth")

def initiation() -> None:
    for path in REQ_DIRS:
        path.mkdir(exist_ok=True, parents=True)
        
    for file in REQ_FILES:
        file.touch(exist_ok=True)
        
    if CONFIG_FILE.stat().st_size == 0:
        with CONFIG_FILE.open("w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
            
    if PROXIES_FILE.stat().st_size == 0:
        with PROXIES_FILE.open("w", encoding="utf-8") as f:
            for proxy in DEFAULT_PROXIES:
                f.write(f"{proxy}\n")




def load_config() -> dict:
    with CONFIG_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_proxies() -> tuple:
    with PROXIES_FILE.open("r", encoding="utf-8") as f:
        return tuple(line.strip() for line in f if line.strip())

def setup_session(config: dict, proxies: tuple) -> requests.Session:
    session = requests.Session()
    session.headers.update(config.get("headers", {}))
    
    if proxies:
        proxy = random.choice(proxies)
        session.proxies.update({"http": proxy, "https": proxy})
        print(f"  -> Using proxy: {proxy}")
    else:
        print("  -> No proxies found. Using direct connection.")
        
    return session

def login(session: requests.Session, config: dict) -> bool:
    login_url = config.get("login_url")
    if not login_url:
        print("Error: 'login_url' missing from config.")
        return False

    verify_method = config.get("login_verify_method", "text")
    is_redirect_allowed = (verify_method != "redirect")

    try:
        login_page = session.get(login_url, timeout=10)
        login_page.raise_for_status()
        
        soup = BeautifulSoup(login_page.text, "html.parser")
        token_input = soup.find("input", {"name": "csrf_token"})
        csrf_token = token_input["value"] if token_input else ""

        payload = {
            "username": config.get("username"),
            "password": config.get("password"),
            "csrf_token": csrf_token
        }
        
        login_res = session.post(
            login_url, 
            data=payload, 
            timeout=10, 
            allow_redirects=is_redirect_allowed
        )
        login_res.raise_for_status()
        
        if verify_method == "redirect":
            if login_res.status_code in (301, 302, 303, 307, 308):
                redirect_url = login_res.headers.get("Location", "").lower()
                if not any(kw in redirect_url for kw in FAILURE_KEYWORDS):
                    return True
        elif verify_method == "url":
            if config.get("login_success_url", "") in login_res.url:
                return True
        else:
            if config.get("login_success_text", "") in login_res.text:
                return True
                
        return False

    except requests.RequestException as e:
        print(f"  -> Login network error: {e}")
        return False


def scrape(session: requests.Session, url: str) -> requests.Response | None:
    try:
        response = session.get(url, timeout=10, stream=True)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        print(f"  -> Scrape error: {e}")
        return None

def save_response(response: requests.Response) -> None:
    content_type = response.headers.get("content-type", "").lower()
    data_dir = BASE_PATH / "data"
    
    if "application/json" in content_type:
        path = data_dir / "output.json"
        path.write_text(response.text, encoding="utf-8")
        print(f"Saved JSON to {path.name}")
    elif "image" in content_type:
        path = data_dir / "output.png"
        path.write_bytes(response.content)
        print(f"Saved Image to {path.name}")
    elif "text/html" in content_type:
        path = data_dir / "output.html"
        path.write_text(response.text, encoding="utf-8")
        print(f"Saved HTML to {path.name}")
    else:
        path = data_dir / "output.txt"
        path.write_text(response.text, encoding="utf-8")
        print(f"Saved Text to {path.name}")


def main() -> int:
    print("Starting templated scraper...")
    
    try:
        initiation()
        config = load_config()
    except (OSError, json.JSONDecodeError) as e:
        print(f"Setup/Config Error: {e}")
        return 1
        
    proxies = read_proxies()
    target_url = config.get("target_url")
    headers = config.get("headers", {})
    
    # 1. Main extracts and picks the proxy
    proxy_dict = None
    if proxies:
        chosen_proxy = random.choice(proxies)
        proxy_dict = {"http": chosen_proxy, "https": chosen_proxy}
    
    # 2. Main calls the function with the exact data it needs
    if is_login_req(config):
        response = login_and_scrape(
            login_url=config.get("login_url"),
            target_url=target_url,
            username=config["username"],
            password=config["password"],
            headers=headers,
            proxy_dict=proxy_dict,
            verify_method=config.get("login_verify_method", "text"),
            verify_text=config.get("login_success_text", ""),
            verify_url=config.get("login_success_url", "")
        )
    else:
        response = direct_scrape(target_url, headers, proxy_dict)
        
    if response is None:
        print("Scrape failed. Exiting.")
        return 1
        
    try:
        save_response(response)
    except OSError as e:
        print(f"File save error: {e}")
        return 1
        
    return 0


if __name__ == "__main__":
    sys.exit(main())