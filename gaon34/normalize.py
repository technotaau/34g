"""URL, text and title normalisation used by dedup and matching."""
import re
import unicodedata
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid",
                   "igshid", "ref", "ref_src", "feature", "si", "mibextid", "_ga", "amp"}
HOST_ALIASES = {"m.facebook.com": "www.facebook.com", "mbasic.facebook.com": "www.facebook.com", "fb.com": "www.facebook.com",
                "m.youtube.com": "www.youtube.com", "youtube.com": "www.youtube.com", "youtu.be": "www.youtube.com",
                "mobile.twitter.com": "x.com", "twitter.com": "x.com", "hi.m.wikipedia.org": "hi.wikipedia.org",
                "en.m.wikipedia.org": "en.wikipedia.org"}


def canonical_url(url: str) -> str:
    """Stable key for a URL: lowercase host, alias hosts, strip tracking params, amp and trailing slash."""
    url = (url or "").strip()
    if not url:
        return ""
    if not re.match(r"^[a-z]+://", url, re.I):
        url = "https://" + url
    p = urlparse(url)
    host = p.netloc.lower().split("@")[-1].split(":")[0]
    path = p.path or "/"
    if host == "youtu.be":
        vid = path.strip("/").split("/")[0]
        return f"https://www.youtube.com/watch?v={vid}"
    host = HOST_ALIASES.get(host, host)
    if host.startswith("www.") and host not in ("www.facebook.com", "www.youtube.com"):
        host = host[4:]
    if host == "www.youtube.com":
        q = parse_qs(p.query)
        if "v" in q:
            return f"https://www.youtube.com/watch?v={q['v'][0]}"
        if path.startswith("/shorts/"):
            return f"https://www.youtube.com/watch?v={path.split('/')[2]}"
    path = re.sub(r"/amp/?$", "/", path)
    path = re.sub(r"^/amp/", "/", path)
    q = {k: v for k, v in parse_qs(p.query, keep_blank_values=False).items() if k.lower() not in TRACKING_PARAMS}
    query = urlencode(sorted((k, v[0]) for k, v in q.items()))
    path = path.rstrip("/") or "/"
    return urlunparse(("https", host, path, "", query, ""))


def host_of(url: str) -> str:
    return urlparse(canonical_url(url)).netloc


def norm_text(s: str) -> str:
    """NFC-normalise, lowercase, strip Devanagari nukta/anusvara variants and punctuation for matching."""
    s = unicodedata.normalize("NFC", s or "").lower()
    s = s.replace("ं", "ँ")  # anusvara -> chandrabindu equivalence
    s = s.replace("़", "")  # drop nukta (ड़ -> ड)
    s = re.sub(r"[‘’“”\"'`|]", " ", s)
    s = re.sub(r"[^\w\sऀ-ॿ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def tokens(s: str) -> set:
    return {t for t in norm_text(s).split() if len(t) > 1}


def title_fingerprint(title: str) -> str:
    return " ".join(sorted(tokens(title)))


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def contains_term(text: str, term: str) -> bool:
    """Term match tolerant to script normalisation; whole-word for Latin, substring for Devanagari."""
    t, n = norm_text(text), norm_text(term)
    if not t or not n:
        return False
    if re.search(r"[ऀ-ॿ]", n):
        return n in t
    return re.search(r"(?<![\w])" + re.escape(n) + r"(?![\w])", t) is not None
