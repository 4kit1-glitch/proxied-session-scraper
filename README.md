# Proxied Session Scraper

A reusable Python template for fetching public pages or authenticated resources with `requests` and BeautifulSoup. It supports session-based login with CSRF token extraction, proxy rotation after request failures, and streamed response downloads to disk.

## Why I Built This

This project is a reusable, fault-tolerant starting point for developers who want to plug in their own target URLs, login details, and success checks. It keeps common scraping plumbing such as session setup, configuration, proxy retries, and file output in one small script so that target-specific changes can stay focused.

## Directory Structure

Running the script from a working directory creates this structure if it does not already exist:

```text
sptemplate/
├── data/
│   ├── config.json
│   └── output.*
└── proxies/
	└── proxies.txt
```

The checked-in `config.example.json` and `proxies.example.txt` are examples to copy or use as references. The script reads its active configuration and proxy list from `sptemplate/data/config.json` and `sptemplate/proxies/proxies.txt`.

## Setup & Usage

Use Python 3.10 or newer, then install the dependencies and run the script from the project directory:

```bash
python -m pip install -r requirements.txt
python scraper.py
```

On the first run, the script creates `sptemplate/`, writes a default config and proxy list if those files are empty, and then starts scraping. Replace the sample credentials and proxy addresses with values you are authorized to use. The default target is the public Quotes to Scrape example site.

## How to Configure

Edit `sptemplate/data/config.json`, which is generated from the defaults in `scraper.py`. `config.example.json` shows those defaults.

- `target_url`: page or resource to fetch.
- `requires_login`: set to `true` to log in before fetching the target, or `false` for a public target.
- `login_url`, `username`, and `password`: login endpoint and credentials used when login is enabled.
- `login_verify_method`: select `text`, `url`, or `redirect` to verify login success.
- `login_success_text`: for `text`, the response body must contain this value.
- `login_success_url`: for `url`, this value must occur in the final response URL.
- `headers`: headers applied to the persistent Requests session.

The `redirect` method disables automatic redirects on the login POST and checks the redirect response's `Location` for common authentication-failure words. For a `text` or `url` check, redirects are followed by Requests before verification. The login form payload currently uses the field names `username`, `password`, and `csrf_token`; adapt `login()` in `scraper.py` if the target uses different form fields or token markup.

Put one proxy URL per line in `sptemplate/proxies/proxies.txt`. The script assigns the selected proxy to both HTTP and HTTPS traffic. It tries proxies in file order and waits a randomized 1–3 seconds before each attempt. If the file is empty, it makes one direct-connection attempt.

## Limitations

This template assumes the target is not a JavaScript-heavy Single Page Application (SPA). It uses only HTTP requests and BeautifulSoup; it does not run a browser or execute JavaScript. It cannot bypass Cloudflare, Turnstile, or similar access challenges. Use it only with sites and accounts you are authorized to access, and follow the target site's terms and applicable laws.

## License & Author

MIT License; see [LICENSE](LICENSE). Author: **Kengah Ireneaus**.
