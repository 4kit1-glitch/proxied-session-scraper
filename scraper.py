"""
Templated scraper script.
Assumes the target website is not a JS-heavy Single Page Application.
"""

import sys
import json
import random
import time
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


class AuthError(Exception):
    """Raised when login fails due to bad credentials, not a network issue."""
    

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

def _stream_to_file(response: requests.Response, path: Path, is_text: bool = False) -> None:
    """Helper to stream response chunks to a file to save memory."""
    mode = "w" if is_text else "wb"
    encoding = "utf-8" if is_text else None
    
    with path.open(mode, encoding=encoding) as f:
        if is_text:
            for chunk in response.iter_content(chunk_size=8192, decode_unicode=True):
                if chunk:
                    f.write(chunk)
        else:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

def _save_text(response: requests.Response) -> None:
    path = BASE_PATH / "data" / "output.txt"
    _stream_to_file(response, path, is_text=True)
    print(f"  -> Saved Text to {path.name}")


def _save_json(response: requests.Response) -> None:
    path = BASE_PATH / "data" / "output.json"
    _stream_to_file(response, path, is_text=True)
    print(f"  -> Saved JSON to {path.name}")


def _save_html(response: requests.Response) -> None:
    path = BASE_PATH / "data" / "output.html"
    _stream_to_file(response, path, is_text=True)
    print(f"  -> Saved HTML to {path.name}")


def _save_img(response: requests.Response) -> None:
    path = BASE_PATH / "data" / "output.png"
    _stream_to_file(response, path, is_text=False)
    print(f"  -> Saved Image to {path.name}")


def _save_vid(response: requests.Response) -> None:
    path = BASE_PATH / "data" / "output.mp4"
    _stream_to_file(response, path, is_text=False)
    print(f"  -> Saved Video to {path.name}")


def save_response(response: requests.Response) -> None:
    content_type = response.headers.get("content-type", "").lower()
    
    if "application/json" in content_type:
        _save_json(response)
    elif "image" in content_type:
        _save_img(response)
    elif "video" in content_type:
        _save_vid(response)
    elif "text/html" in content_type:
        _save_html(response)
    else:
        _save_text(response)

def main() -> int:
    print("Starting templated scraper...")
    
    print("[1/6] Initializing environment...")
    try:
        initiation()
    except OSError as e:
        print(f"  -> Failed to initialize files: {e}")
        return 1
        
    print("[2/6] Loading configuration...")
    try:
        config = load_config()
        proxies = read_proxies()
    except (OSError, json.JSONDecodeError) as e:
        print(f"  -> Configuration error: {e}")
        return 1
        
    print("[3/6] Setting up session...")
    session = setup_session(config, proxies)
    
    target_url = config.get("target_url")
    if not target_url:
        print("  -> Error: 'target_url' missing from config.")
        return 1
    
    if config.get("username") and config.get("password"):
        print("[4/6] Authenticating...")
        if not login(session, config):
            print("  -> Login failed. Exiting.")
            return 1
        print("  -> Login successful.")
    else:
        print("[4/6] Skipping authentication (no credentials provided).")

    print(f"[5/6] Scraping target: {target_url}...")
    response = scrape(session, target_url)
    if not response:
        return 1
        
    print("[6/6] Saving response...")
    try:
        save_response(response)
    except OSError as e:
        print(f"  -> File save error: {e}")
        return 1
    except KeyboardInterrupt:
        print("    Keyboard interupt")
        
    print("Finished successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())