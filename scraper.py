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
    "requires_login": True,
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
    "http://2.2.2.2:8080",
    "http://3.3.3.3:8080",
    "http://4.4.4.4:8080"
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

def setup_session(config: dict, proxy: str | None) -> requests.Session:
    session = requests.Session()     # create the ses
    session.headers.update(config.get("headers", {})) # update the seession headers
    
    if proxy:
        session.proxies.update({"http": proxy, "https": proxy}) # update the session prox
        print(f"  -> Using proxy: {proxy}")
    else:
        print("  -> No proxy given. Using direct connection.")
        
    return session

def _verify_login(response: requests.Response, config: dict) -> bool:
    """Helper to evaluate the configurable login success conditions."""
    verify_method = config.get("login_verify_method", "text")

    if verify_method == "redirect":
        if response.status_code in (301, 302, 303, 307, 308):
            redirect_url = response.headers.get("Location", "").lower()
            # Return True if no failure keywords are found in the redirect
            return not any(kw in redirect_url for kw in FAILURE_KEYWORDS)
            
    elif verify_method == "url":
        return config.get("login_success_url", "") in response.url
        
    else: # Default to "text"
        return config.get("login_success_text", "") in response.text

    return False

def login(session: requests.Session, config: dict) -> None:
    login_url = config.get("login_url")
    if not login_url:
        raise ValueError("Config error: 'requires_login' is True, but 'login_url' is missing.")

    is_redirect_allowed = (config.get("login_verify_method") != "redirect")

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
        login_url, data=payload, timeout=10, allow_redirects=is_redirect_allowed
    )
    login_res.raise_for_status()
    
    if not _verify_login(login_res, config):
        raise AuthError("Login verification failed. Check credentials.")


def scrape(session: requests.Session, url: str) -> requests.Response:
    response = session.get(url, timeout=10, stream=True)
    response.raise_for_status()
    return response


def _stream_to_file(response: requests.Response, path: Path, is_text: bool = False) -> None:
    """Helper to stream response chunks to a file to save memory."""
    mode = "w" if is_text else "wb"
    encoding = "utf-8" if is_text else None
    chk = 8192 # chunck num
    
    with path.open(mode, encoding=encoding) as f:
        if is_text:
            for chunk in response.iter_content(chunk_size=chk, decode_unicode=True):
                if chunk:
                    f.write(chunk)
        else:
            for chunk in response.iter_content(chunk_size=chk):
                if chunk:
                    f.write(chunk)
def save_response(response: requests.Response) -> None:
    content_type = response.headers.get("content-type", "").lower()
    
    if "application/json" in content_type:
        path, is_text = BASE_PATH / "data" / "output.json", True
    elif "image" in content_type:
        path, is_text = BASE_PATH / "data" / "output.png", False
    elif "video" in content_type:
        path, is_text = BASE_PATH / "data" / "output.mp4", False
    elif "text/html" in content_type:
        path, is_text = BASE_PATH / "data" / "output.html", True
    else:
        path, is_text = BASE_PATH / "data" / "output.txt", True

    _stream_to_file(response, path, is_text)
    print(f"  -> Saved to {path.name}")


def execute_scrape(config: dict, proxies: tuple) -> int:
    target_url = config.get("target_url")
    if not target_url:
        print("  -> Error: 'target_url' missing from config.")
        return 1

    proxy_list = proxies if proxies else (None,)
    
    for i, proxy in enumerate(proxy_list, 1):
        print(f"\n[Attempt {i}/{len(proxy_list)}]")
        time.sleep(random.randint(1, 3))
        
        session = setup_session(config, proxy)
        
        try:
            if config.get("requires_login"):
                print("  -> Authenticating...")
                login(session, config)
                print("  -> Login successful.")
            
            print(f"  -> Scraping target: {target_url}...")
            response = scrape(session, target_url)
            
            print("  -> Saving response...")
            save_response(response)
            return 0
            
        except AuthError as e:
            print(f"  -> Authentication Error: {e}")
            return 1 # Stop immediately on bad credentials
            
        except ValueError as e:
            print(f"  -> Config Error: {e}")
            return 1
            
        except requests.exceptions.ProxyError:
            print("  -> Proxy Error: Could not connect to proxy.")
        except requests.exceptions.Timeout:
            print("  -> Timeout Error: Request took too long.")
        except requests.exceptions.RequestException as e:
            print(f"  -> Network Error: {e}")
        except OSError as e:
            print(f"  -> File System Error: {e}")
            return 1

    print("\n  -> Max retries reached. All proxies failed.")
    return 1


def main() -> int:
    print("Starting templated scraper...")
    
    print("[1/4] Initializing environment...")
    try:
        initiation()
    except OSError as e:
        print(f"  -> Failed to initialize files: {e}")
        return 1
        
    print("[2/4] Loading configuration...")
    try:
        config = load_config()
        proxies = read_proxies()
    except (OSError, json.JSONDecodeError) as e:
        print(f"  -> Configuration error: {e}")
        return 1
        
    print("[3/4] Starting execution loop...")
    exit_code = execute_scrape(config, proxies)
    
    if exit_code == 0:
        print("\n[4/4] Finished successfully.")
    else:
        print("\n[4/4] Process failed.")
        
    return exit_code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n  -> Process interrupted by user. Exiting safely.")
        sys.exit(130)