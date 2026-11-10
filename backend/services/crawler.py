"""SSRF-safe reference-website analyzer.

Security properties
* Only http/https on ports 80/443, no credentials in URLs.
* Every hostname is resolved and *all* addresses must be public (no private,
  loopback, link-local, multicast, reserved, CGNAT or metadata ranges).
* The TCP connection is pinned to the validated IP (TLS still verifies the
  real hostname), so DNS rebinding between check and connect is not possible.
* Redirects are followed manually (max 3) and every hop is re-validated.
* robots.txt is honoured; responses are size- and time-limited; only text/html
  and XML are parsed. Nothing is executed.

The output is a structural/design summary used as *inspiration*; the AI is
instructed not to copy text, assets or code verbatim.
"""
import ipaddress
import re
import socket
from collections import Counter
from urllib import robotparser
from urllib.parse import urljoin, urlsplit, urlunsplit

import certifi
import urllib3
from bs4 import BeautifulSoup

from config import Config

MAX_BYTES = 1_500_000
ALLOWED_PORTS = {80, 443}
HEX = re.compile(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
FONT_DECL = re.compile(r"font-family\s*:\s*([^;}{]+)", re.IGNORECASE)


class CrawlError(Exception):
    pass


def _ip_allowed(ip_text):
    ip = ipaddress.ip_address(ip_text)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip.is_global and not (ip.is_multicast or ip.is_reserved or ip.is_loopback or
                                 ip.is_link_local or ip.is_private or ip.is_unspecified)


def validate_url(url):
    if not isinstance(url, str) or len(url) > 2048:
        raise CrawlError("Invalid URL")
    url = url.strip()
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "https://" + url
    parts = urlsplit(url)
    if parts.scheme.lower() not in ("http", "https"):
        raise CrawlError("Only http and https URLs are supported")
    if parts.username or parts.password:
        raise CrawlError("URLs with credentials are not allowed")
    host = (parts.hostname or "").rstrip(".").lower()
    if not host or host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise CrawlError("That host is not allowed")
    port = parts.port or (443 if parts.scheme.lower() == "https" else 80)
    if port not in ALLOWED_PORTS:
        raise CrawlError("Only standard web ports (80/443) are allowed")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, "")), host, port


def resolve_public(host, port):
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise CrawlError("Could not resolve that domain") from exc
    addresses = sorted({info[4][0] for info in infos})
    if not addresses:
        raise CrawlError("Could not resolve that domain")
    for addr in addresses:
        if not _ip_allowed(addr):
            raise CrawlError("That address points to a private or reserved network and is blocked")
    return addresses[0]


def safe_fetch(url, accept=("text/html", "application/xhtml", "text/xml", "application/xml", "text/plain"),
               max_bytes=MAX_BYTES):
    timeout = urllib3.Timeout(connect=5, read=Config.CRAWLER_TIMEOUT_SECONDS)
    for _hop in range(4):
        url, host, port = validate_url(url)
        ip = resolve_public(host, port)
        parts = urlsplit(url)
        path = parts.path + (f"?{parts.query}" if parts.query else "")
        if parts.scheme == "https":
            pool = urllib3.HTTPSConnectionPool(ip, port, timeout=timeout, retries=False,
                                               cert_reqs="CERT_REQUIRED", ca_certs=certifi.where(),
                                               server_hostname=host, assert_hostname=host)
        else:
            pool = urllib3.HTTPConnectionPool(ip, port, timeout=timeout, retries=False)
        try:
            resp = pool.urlopen("GET", path, headers={
                "Host": parts.netloc, "User-Agent": Config.CRAWLER_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.5"},
                redirect=False, preload_content=False, retries=False)
        except urllib3.exceptions.HTTPError as exc:
            raise CrawlError(f"Could not fetch {host}") from exc
        try:
            if 300 <= resp.status < 400 and resp.headers.get("Location"):
                url = urljoin(url, resp.headers["Location"])
                continue
            ctype = (resp.headers.get("Content-Type") or "").lower()
            if resp.status >= 400:
                return resp.status, ctype, b"", url
            if accept and not any(a in ctype for a in accept):
                return resp.status, ctype, b"", url
            body = resp.read(max_bytes + 1, decode_content=True)
            return resp.status, ctype, body[:max_bytes], url
        finally:
            resp.release_conn()
            pool.close()
    raise CrawlError("Too many redirects")


def robots_for(base_url):
    parts = urlsplit(base_url)
    rp = robotparser.RobotFileParser()
    try:
        status, _ctype, body, _ = safe_fetch(f"{parts.scheme}://{parts.netloc}/robots.txt", accept=None,
                                             max_bytes=200_000)
        if status >= 400:
            rp.parse([])
        else:
            rp.parse(body.decode("utf-8", "replace").splitlines())
    except CrawlError:
        rp.parse([])
    return rp


def _text(el, limit=200):
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True))[:limit] if el else ""


def analyze_html(html, url):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "noscript", "template", "iframe"]):
        tag.decompose()
    meta_desc = soup.find("meta", attrs={"name": "description"})
    nav = soup.find("nav") or soup.find("header")
    nav_links = []
    if nav:
        for a in nav.find_all("a", href=True)[:15]:
            label = _text(a, 40)
            if label:
                nav_links.append({"label": label, "href": urljoin(url, a["href"])})
    sections = []
    body = soup.body or soup
    candidates = body.find_all(["header", "section", "footer", "main", "article"], recursive=True)
    for el in candidates[:25]:
        heading = el.find(["h1", "h2", "h3"])
        classes = " ".join(el.get("class") or [])[:80]
        sections.append({
            "tag": el.name, "hint": (el.get("id") or classes)[:60], "heading": _text(heading, 120),
            "images": len(el.find_all("img")), "buttons": len(el.find_all(["button"])) +
            len([a for a in el.find_all("a") if "btn" in " ".join(a.get("class") or []).lower()]),
            "forms": len(el.find_all("form")), "inputs": len(el.find_all(["input", "textarea", "select"])),
            "links": len(el.find_all("a")),
        })
    css_text = " ".join(s.get_text() for s in soup.find_all("style"))
    css_text += " ".join(el.get("style", "") for el in soup.find_all(style=True))
    colors = [c.lower() for c in HEX.findall(css_text)]
    fonts = [f.split(",")[0].strip().strip("'\"") for f in FONT_DECL.findall(css_text)]
    for link in soup.find_all("link", href=True):
        if "fonts.googleapis.com" in link["href"]:
            fonts += [m.replace("+", " ") for m in re.findall(r"family=([A-Za-z+]+)", link["href"])]
    return {
        "url": url,
        "title": _text(soup.title, 120),
        "description": (meta_desc.get("content", "") if meta_desc else "")[:300],
        "headings": [_text(h, 120) for h in soup.find_all(["h1", "h2", "h3"])[:20]],
        "nav": nav_links,
        "sections": sections,
        "forms": len(soup.find_all("form")),
        "colors": [c for c, _ in Counter(colors).most_common(8)],
        "fonts": [f for f, _ in Counter(fonts).most_common(4) if f and not f.startswith("var(")],
        "text_sample": [_text(p, 200) for p in soup.find_all("p")[:12] if _text(p, 200)],
        "internal_links": [urljoin(url, a["href"]) for a in soup.find_all("a", href=True)][:200],
    }


def crawl(url, max_pages=None):
    """Analyze up to `max_pages` same-site pages. Returns a structured summary."""
    max_pages = max_pages or Config.CRAWLER_MAX_PAGES
    start, host, _ = validate_url(url)
    robots = robots_for(start)
    if not robots.can_fetch(Config.CRAWLER_USER_AGENT, start):
        raise CrawlError("This website's robots.txt does not allow automated analysis")
    status, ctype, body, final = safe_fetch(start)
    if status >= 400 or not body:
        raise CrawlError(f"The page returned HTTP {status} or was not HTML")
    home = analyze_html(body.decode("utf-8", "replace"), final)
    pages = [home]

    queue, seen = [], {final}
    for link in [n["href"] for n in home["nav"]] + home["internal_links"]:
        parts = urlsplit(link)
        if parts.scheme in ("http", "https") and (parts.hostname or "").lower() == host and \
                not re.search(r"\.(png|jpe?g|gif|svg|pdf|zip|webp|mp4)$", parts.path, re.I):
            clean = urlunsplit((parts.scheme, parts.netloc, parts.path or "/", "", ""))
            if clean not in seen:
                seen.add(clean)
                queue.append(clean)
    for link in queue[: max_pages - 1]:
        if not robots.can_fetch(Config.CRAWLER_USER_AGENT, link):
            continue
        try:
            status, _ctype, body, final = safe_fetch(link)
            if status < 400 and body:
                pages.append(analyze_html(body.decode("utf-8", "replace"), final))
        except CrawlError:
            continue
    for page in pages:
        page.pop("internal_links", None)
    return {"url": start, "pages": pages,
            "notice": "Reference analysis only. Generate an original design and original copy."}
