# Internal Architecture

This document follows the execution path in `scraper.py`, from startup through response persistence.

## 1. Initialization: `initiation()`

`BASE_PATH` is set to `Path.cwd() / "sptemplate"`, so the data location is relative to the directory from which the script is launched. `initiation()` creates the base directory plus `data/` and `proxies/`, using parent creation and `exist_ok=True` so repeat runs are safe.

It then touches `data/config.json` and `proxies/proxies.txt`. If either file is empty, the function populates it from `DEFAULT_CONFIG` or `DEFAULT_PROXIES`; non-empty files are left untouched. This lets the script initialize itself once without overwriting user configuration on later runs.

## 2. Loading and Session Setup: `load_config()`, `read_proxies()`, `setup_session()`

`load_config()` parses the active JSON config. `read_proxies()` reads non-empty lines from the proxy file, strips surrounding whitespace, and returns them as a tuple.

For each attempt, `setup_session()` creates a persistent `requests.Session` and adds the configured `headers`. When a proxy URL is supplied, the same URL is assigned to the session's `http` and `https` proxy settings; with `None`, the session connects directly. A session is created per attempt, so cookies from a failed proxy attempt are not reused by the next one.

## 3. Login Flow: `login()` and `_verify_login()`

When `requires_login` is true, `login()` first requests `login_url` and checks the HTTP status. It parses the returned HTML with BeautifulSoup and looks for an input whose `name` is `csrf_token`. If found, its `value` is included in the POST payload alongside the configured username and password. If no such input exists, the token is sent as an empty string.

The login POST uses the same session, preserving cookies established by the login-page request. The payload field names are fixed in the script and may need to be adapted for other sites.

`_verify_login()` checks the response according to `login_verify_method`:

- `text`: succeeds when `login_success_text` occurs in the response body. This is also the fallback for an unrecognized method value.
- `url`: succeeds when `login_success_url` occurs in the response URL.
- `redirect`: automatic redirect following is disabled for the POST. Verification requires a 301, 302, 303, 307, or 308 response and a `Location` header that contains none of the known failure keywords (`login`, `signin`, `signup`, `register`, or `auth`).

If the selected check fails, `login()` raises `AuthError`. The execution loop treats that as a terminal authentication failure rather than retrying other proxies.

## 4. Execution Loop: `execute_scrape()`

The function validates that `target_url` exists, then walks through the configured proxies in order. If no proxies were loaded, it substitutes a single `None` entry for a direct attempt. Before every attempt it sleeps for a random 1–3 seconds. This is a fixed-range randomized delay, not an exponential backoff.

Each attempt creates a session, optionally logs in, fetches the target with streaming enabled, and saves the response. The first successful save returns exit code `0`.

Errors are handled according to whether another network attempt could help:

- `AuthError` and configuration `ValueError` stop immediately and return `1`.
- `requests.exceptions.ProxyError`, `Timeout`, and other `RequestException` errors are reported and allow the loop to try the next proxy.
- `OSError` while writing to disk stops immediately and returns `1`.

When all attempts have been exhausted, the function reports that the proxies failed and returns `1`.

## 5. Fetching and Streaming: `scrape()`, `save_response()`, `_stream_to_file()`

`scrape()` requests the target with a 10-second timeout and `stream=True`, then checks the HTTP status. `save_response()` selects an output name and text/binary mode based on the response `Content-Type`: JSON goes to `output.json`, images to `output.png`, video to `output.mp4`, HTML to `output.html`, and other content to `output.txt`.

`_stream_to_file()` consumes `response.iter_content()` in 8 KiB chunks and writes each non-empty chunk immediately. This avoids loading the entire response body into memory, which is useful for large downloads. Text-like responses are opened in UTF-8 text mode and request decoded chunks; image and video responses are written unchanged in binary mode. The extension selection is intentionally simple and does not infer a specific image or video format from the MIME subtype.