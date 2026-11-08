"""
some scraper template written at 1 am
Assumes the web to scrape is not Js heavy
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
    "login_verify_method": "text", # Options: "text", "redirect", "url"
    "login_success_text": "Logout",
    "login_success_url": "", 
    "headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
}

DEFAULT_PROXIES = (
    "http://1.1.1.1:8080",
    "http://2.2.2.2:8080",
    "http://3.3.3.3:8080"
)


def initiation() -> None:
    """Sets up dir structure and creates default files if missing."""
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
    try:
        with PROXIES_FILE.open("r", encoding="utf-8") as f:
            return tuple(line.strip() for line in f if line.strip())
    except OSError:
        return ()


def is_login_req(config: dict) -> bool:
    return bool(config.get("username") and config.get("password"))


def _get_proxy_dict(proxies: tuple) -> dict | None:
    if not proxies:
        return None
    proxy = random.choice(proxies)
    return {"http": proxy, "https": proxy}


def _verify_login(response: requests.Response, config: dict) -> bool:
    """Checks the configured method to confirm if login succeeded."""
    method = config.get("login_verify_method", "text")
    
    if method == "redirect":
        # Check if the server returned a 3xx redirect
        if response.status_code in (301, 302, 303, 307, 308):
            redirect_url = response.headers.get("Location", "")
            if "login" not in redirect_url.lower():
                return True
    elif method == "url":
        success_url = config.get("login_success_url", "")
        if success_url and success_url in response.url:
            return True
    else: # Default to "text"
        success_text = config.get("login_success_text", "")
        if success_text and success_text in response.text:
            return True
            
    return False


def login_and_scrape(config: dict, proxies: tuple) -> requests.Response | None:
    target_url = config.get("target_url")
    login_url = config.get("login_url")
    headers = config.get("headers", {})
    verify_method = config.get("login_verify_method", "text")
    
    # If checking redirects, we must stop requests from auto-following them
    allow_redirects = (verify_method != "redirect")
    
    with requests.Session() as session:
        session.headers.update(headers)
        proxy_dict = _get_proxy_dict(proxies)
        
        print(f"Fetching login page (Proxy: {proxy_dict['http'] if proxy_dict else 'Direct'})...")
        try:
            login_page = session.get(login_url, proxies=proxy_dict, timeout=10)
            login_page.raise_for_status()
        except requests.RequestException as e:
            print(f"Failed to load login page: {e}")
            return None

        soup = BeautifulSoup(login_page.text, "html.parser")
        token_input = soup.find("input", {"name": "csrf_token"})
        csrf_token = token_input["value"] if token_input else ""

        payload = {
            "username": config["username"],
            "password": config["password"],
            "csrf_token": csrf_token
        }
        
        print("Attempting login...")
        try:
            login_res = session.post(
                login_url, 
                data=payload, 
                proxies=proxy_dict, 
                timeout=10, 
                allow_redirects=allow_redirects
            )
            login_res.raise_for_status()
            
            if not _verify_login(login_res, config):
                print("Login failed (Verification condition not met).")
                return None
                
            print("✅ Login successful!")
            
            print(f"Fetching protected target: {target_url}")
            final_res = session.get(target_url, proxies=proxy_dict, timeout=10)
            final_res.raise_for_status()
            return final_res
            
        except requests.RequestException as e:
            print(f"Network error during login/scrape: {e}")
            return None


def direct_scrape(config: dict, proxies: tuple) -> requests.Response | None:
    target_url = config.get("target_url")
    headers = config.get("headers", {})
    proxy_dict = _get_proxy_dict(proxies)
    
    print(f"Direct scraping {target_url} (Proxy: {proxy_dict['http'] if proxy_dict else 'Direct'})...")
    try:
        response = requests.get(target_url, headers=headers, proxies=proxy_dict, timeout=10)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        print(f"Failed to fetch target: {e}")
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
    
    if is_login_req(config):
        response = login_and_scrape(config, proxies)
    else:
        response = direct_scrape(config, proxies)
        
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