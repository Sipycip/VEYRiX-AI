import base64
import html
import json
import re

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from urllib.parse import unquote, urlparse

import requests


# ============================================================
# CONFIGURATION
# ============================================================

BING_URL = "https://www.bing.com/search"

REQUEST_TIMEOUT = 12
PAGE_TIMEOUT = 15

MAX_SEARCH_RESULTS = 10
MAX_SOURCES = 4

CURRENT_YEAR = datetime.now().year


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# ============================================================
# SOURCE AUTHORITY
# ============================================================

TRUSTED_WEALTH_DOMAINS = {
    "forbes.com",
    "www.forbes.com",
    "bloomberg.com",
    "www.bloomberg.com",
}


DOMAIN_AUTHORITY = {
    "forbes.com": 100,
    "www.forbes.com": 100,

    "bloomberg.com": 100,
    "www.bloomberg.com": 100,

    "reuters.com": 95,
    "www.reuters.com": 95,

    "apnews.com": 95,
    "www.apnews.com": 95,

    "bbc.com": 90,
    "www.bbc.com": 90,

    "cnbc.com": 90,
    "www.cnbc.com": 90,

    "nytimes.com": 90,
    "www.nytimes.com": 90,

    "wsj.com": 90,
    "www.wsj.com": 90,
}


# ============================================================
# KNOWN PEOPLE
# ============================================================

KNOWN_PEOPLE = [
    "Elon Musk",
    "Larry Ellison",
    "Jeff Bezos",
    "Mark Zuckerberg",
    "Bernard Arnault",
    "Larry Page",
    "Sergey Brin",
    "Jensen Huang",
    "Warren Buffett",
    "Steve Ballmer",
    "Bill Gates",
]


# ============================================================
# TERMS
# ============================================================

WEALTH_TERMS = [
    "current net worth",
    "net worth",
    "networth",
    "fortune",
    "wealth",
    "worth",
]


RICHEST_TERMS = [
    "richest person",
    "richest man",
    "richest woman",
    "world's richest",
    "worlds richest",
    "wealthiest person",
    "wealthiest man",
    "wealthiest woman",
    "top billionaire",
    "richest billionaire",
]


CURRENT_TERMS = [
    "real-time",
    "real time",
    "realtime",
    "current",
    "currently",
    "right now",
    "today",
    str(CURRENT_YEAR),
]


# ============================================================
# HARD REJECTION TERMS
#
# These values may be financially related but are NOT
# someone's personal net worth.
# ============================================================

NET_WORTH_REJECT_TERMS = [
    "valuation",
    "valued at",
    "valued the",
    "company value",
    "market cap",
    "market capitalization",
    "revenue",
    "sales",
    "funding",
    "funding round",
    "investment",
    "acquisition",
    "purchase price",
    "deal value",
    "deal valued",
    "compensation",
    "salary",
    "stock award",
    "stock options",
    "ceo package",
]


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text):

    if not text:
        return ""

    text = html.unescape(
        str(text)
    )

    text = re.sub(
        r"<script\b[^>]*>.*?</script>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    text = re.sub(
        r"<style\b[^>]*>.*?</style>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    text = text.replace(
        "\xa0",
        " ",
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


# ============================================================
# BING URL DECODING
# ============================================================

def decode_bing_url(url):

    if not url:
        return ""

    url = html.unescape(
        url
    )

    match = re.search(
        r"[?&]u=([^&]+)",
        url,
        re.IGNORECASE,
    )

    if not match:
        return url

    encoded = unquote(
        match.group(1)
    )

    if encoded.startswith("a1"):
        encoded = encoded[2:]

    try:

        padding = "=" * (
            -len(encoded) % 4
        )

        decoded = base64.urlsafe_b64decode(
            encoded + padding
        ).decode(
            "utf-8",
            errors="ignore",
        )

        if decoded.startswith("http"):
            return decoded

    except Exception:
        pass

    return url


# ============================================================
# DOMAIN HELPERS
# ============================================================

def domain_from_url(url):

    if not url:
        return ""

    try:

        return urlparse(
            url
        ).netloc.lower()

    except Exception:

        return ""


def source_authority(url):

    domain = domain_from_url(
        url
    )

    return DOMAIN_AUTHORITY.get(
        domain,
        0,
    )


def is_trusted_wealth_domain(url):

    domain = domain_from_url(
        url
    )

    return domain in TRUSTED_WEALTH_DOMAINS


# ============================================================
# BING SEARCH
# ============================================================

def search_bing(
    query,
    trusted_only=False,
):

    print(
        f"[Research][Bing] Searching: {query}"
    )

    try:

        response = requests.get(
            BING_URL,
            params={
                "q": query,
                "count": MAX_SEARCH_RESULTS,
            },
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

    except Exception as error:

        print(
            f"[Research][Bing] ERROR: {error}"
        )

        return []

    matches = re.findall(
        r'<li[^>]*class="[^"]*b_algo[^"]*"[^>]*>'
        r'(.*?)'
        r'</li>',
        response.text,
        re.IGNORECASE | re.DOTALL,
    )

    results = []

    for match in matches:

        title_match = re.search(
            r'<h2[^>]*>\s*'
            r'<a[^>]*href="([^"]+)"[^>]*>'
            r'(.*?)'
            r'</a>',
            match,
            re.IGNORECASE | re.DOTALL,
        )

        if not title_match:
            continue

        raw_url = html.unescape(
            title_match.group(1)
        )

        url = decode_bing_url(
            raw_url
        )

        if not url:
            continue

        domain = domain_from_url(
            url
        )

        if trusted_only:

            if not is_trusted_wealth_domain(
                url
            ):
                continue

        title = clean_text(
            title_match.group(2)
        )

        snippet_match = re.search(
            r"<p[^>]*>(.*?)</p>",
            match,
            re.IGNORECASE | re.DOTALL,
        )

        snippet = ""

        if snippet_match:

            snippet = clean_text(
                snippet_match.group(1)
            )

        results.append(
            {
                "title": title,
                "url": url,
                "snippet": snippet,
                "domain": domain,
                "query": query,
            }
        )

    print(
        "[Research][Bing] Accepted results: "
        f"{len(results)}"
    )

    return results


# ============================================================
# URL NORMALIZATION
# ============================================================

def normalize_url(url):

    if not url:
        return ""

    url = decode_bing_url(
        url
    )

    parsed = urlparse(
        url
    )

    domain = parsed.netloc.lower()

    path = parsed.path.rstrip("/")

    if domain.startswith("www."):
        domain = domain[4:]

    return (
        domain
        + path
    ).lower()


# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate_results(results):

    unique = []

    seen = set()

    for result in results:

        normalized = normalize_url(
            result.get(
                "url",
                "",
            )
        )

        if not normalized:
            continue

        if normalized in seen:
            continue

        seen.add(
            normalized
        )

        unique.append(
            result
        )

    return unique


# ============================================================
# MONEY EXTRACTION
# ============================================================

def extract_money_values(text):

    if not text:
        return []

    text = clean_text(
        text
    )

    pattern = re.compile(
        r"(?P<currency>"
        r"US\$|USD|\$|C\$"
        r")?"
        r"\s*"
        r"(?P<number>"
        r"\d+(?:,\d{3})*(?:\.\d+)?"
        r")"
        r"\s*"
        r"(?P<unit>"
        r"trillion|billion|million|T|B|M"
        r")\b",
        re.IGNORECASE,
    )

    values = []

    for match in pattern.finditer(
        text
    ):

        try:

            number = float(
                match.group(
                    "number"
                ).replace(
                    ",",
                    "",
                )
            )

        except ValueError:
            continue

        unit = match.group(
            "unit"
        ).lower()

        if unit in {
            "trillion",
            "t",
        }:

            multiplier = (
                1_000_000_000_000
            )

        elif unit in {
            "billion",
            "b",
        }:

            multiplier = (
                1_000_000_000
            )

        elif unit in {
            "million",
            "m",
        }:

            multiplier = (
                1_000_000
            )

        else:
            continue

        values.append(
            {
                "raw": match.group(0),
                "value": (
                    number
                    * multiplier
                ),
                "currency": (
                    match.group(
                        "currency"
                    )
                    or ""
                ),
                "unit": match.group(
                    "unit"
                ),
                "position": match.start(),
            }
        )

    return values


# ============================================================
# PERSON EXTRACTION
# ============================================================

def extract_known_person(text):

    if not text:
        return None

    lowered = text.lower()

    for person in KNOWN_PEOPLE:

        if person.lower() in lowered:
            return person

    return None


def extract_person_near_wealth(text):

    if not text:
        return None

    for person in KNOWN_PEOPLE:

        person_pattern = re.escape(
            person
        )

        wealth_pattern = (
            r"(?:current net worth|net worth|"
            r"fortune|wealth|worth|"
            r"billionaire|trillionaire)"
        )

        pattern_a = re.compile(
            person_pattern
            + r".{0,500}?"
            + wealth_pattern,
            re.IGNORECASE | re.DOTALL,
        )

        pattern_b = re.compile(
            wealth_pattern
            + r".{0,500}?"
            + person_pattern,
            re.IGNORECASE | re.DOTALL,
        )

        if pattern_a.search(
            text
        ):
            return person

        if pattern_b.search(
            text
        ):
            return person

    return None


# ============================================================
# TERM DETECTION
# ============================================================

def contains_wealth_term(text):

    if not text:
        return False

    lowered = text.lower()

    return any(
        term in lowered
        for term in WEALTH_TERMS
    )


def contains_richest_term(text):

    if not text:
        return False

    lowered = text.lower()

    return any(
        term in lowered
        for term in RICHEST_TERMS
    )


def contains_current_term(text):

    if not text:
        return False

    lowered = text.lower()

    return any(
        term in lowered
        for term in CURRENT_TERMS
    )


# ============================================================
# PAGE FETCHING
# ============================================================

def fetch_source_page(url):

    if not url:
        return None

    print(
        f"[Research][Page] Fetching: {url}"
    )

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=PAGE_TIMEOUT,
            allow_redirects=True,
        )

        response.raise_for_status()

        if not response.text:
            return None

        print(
            "[Research][Page] Readable: "
            f"{response.status_code}"
        )

        return {
            "url": response.url,
            "status": (
                response.status_code
            ),
            "html": response.text,
        }

    except Exception as error:

        print(
            "[Research][Page] FAILED: "
            f"{error}"
        )

        return None


# ============================================================
# PAGE TEXT EXTRACTION
# ============================================================

def extract_page_text(page_html):

    if not page_html:
        return ""

    text = page_html

    text = re.sub(
        r"<script\b[^>]*>.*?</script>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    text = re.sub(
        r"<style\b[^>]*>.*?</style>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    text = re.sub(
        r"<noscript\b[^>]*>.*?</noscript>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    return clean_text(
        text
    )


# ============================================================
# PAGE METADATA / EMBEDDED JSON
# ============================================================

def extract_page_metadata(page_html):

    if not page_html:
        return []

    pieces = []

    # --------------------------------------------------------
    # META
    # --------------------------------------------------------

    meta_matches = re.findall(
        r'<meta[^>]+'
        r'(?:name|property)="[^"]*"'
        r'[^>]+content="([^"]+)"',
        page_html,
        re.IGNORECASE | re.DOTALL,
    )

    for value in meta_matches:

        value = clean_text(
            value
        )

        if value:
            pieces.append(
                value
            )

    # --------------------------------------------------------
    # JSON-LD
    # --------------------------------------------------------

    json_matches = re.findall(
        r'<script[^>]+'
        r'type=["\']application/ld\+json["\']'
        r'[^>]*>'
        r'(.*?)'
        r'</script>',
        page_html,
        re.IGNORECASE | re.DOTALL,
    )

    for raw_json in json_matches:

        raw_json = html.unescape(
            raw_json
        ).strip()

        if not raw_json:
            continue

        try:

            parsed = json.loads(
                raw_json
            )

            pieces.append(
                json.dumps(
                    parsed,
                    ensure_ascii=False,
                )
            )

        except Exception:

            pieces.append(
                clean_text(
                    raw_json
                )
            )

    # --------------------------------------------------------
    # NEXT.JS / EMBEDDED JSON
    # --------------------------------------------------------

    state_patterns = [
        (
            r'<script[^>]+'
            r'id=["\']__NEXT_DATA__["\']'
            r'[^>]*>'
            r'(.*?)'
            r'</script>'
        ),
        (
            r'<script[^>]+'
            r'type=["\']application/json["\']'
            r'[^>]*>'
            r'(.*?)'
            r'</script>'
        ),
    ]

    for pattern in state_patterns:

        matches = re.findall(
            pattern,
            page_html,
            re.IGNORECASE | re.DOTALL,
        )

        for raw_state in matches:

            raw_state = html.unescape(
                raw_state
            ).strip()

            if not raw_state:
                continue

            try:

                parsed = json.loads(
                    raw_state
                )

                pieces.append(
                    json.dumps(
                        parsed,
                        ensure_ascii=False,
                    )
                )

            except Exception:

                pieces.append(
                    clean_text(
                        raw_state
                    )
                )

    return pieces


# ============================================================
# MONEY CONTEXT
# ============================================================

def get_money_context(
    text,
    position,
    radius=350,
):

    start = max(
        0,
        position - radius,
    )

    end = min(
        len(text),
        position + radius,
    )

    return text[
        start:end
    ]


# ============================================================
# NET-WORTH EVIDENCE EXTRACTION
# ============================================================

def extract_money_evidence(
    text,
    person=None,
):

    if not text:
        return []

    text = clean_text(
        text
    )

    values = extract_money_values(
        text
    )

    if not values:
        return []

    evidence = []

    for money in values:

        context = get_money_context(
            text,
            money.get(
                "position",
                0,
            ),
        )

        context_lower = (
            context.lower()
        )

        score = 0

        rejected = False

        rejection_reason = ""

        # ====================================================
        # HARD REJECTION
        # ====================================================

        for term in NET_WORTH_REJECT_TERMS:

            if term in context_lower:

                rejected = True

                rejection_reason = (
                    "Context contains non-net-worth "
                    f"financial term: {term}"
                )

                break

        # ====================================================
        # EXPLICIT NET WORTH
        # ====================================================

        if "current net worth" in context_lower:
            score += 500

        elif "net worth" in context_lower:
            score += 350

        # ====================================================
        # OTHER WEALTH LANGUAGE
        # ====================================================

        if "fortune" in context_lower:
            score += 120

        if "wealth" in context_lower:
            score += 80

        # Plain "worth" is weak unless it's
        # actually part of "net worth".
        if (
            "worth" in context_lower
            and "net worth"
            not in context_lower
        ):
            score += 30

        # ====================================================
        # PERSON
        # ====================================================

        if person:

            if (
                person.lower()
                in context_lower
            ):

                score += 150

        # ====================================================
        # RICHEST LANGUAGE
        # ====================================================

        if contains_richest_term(
            context
        ):

            score += 80

        # ====================================================
        # CURRENT LANGUAGE
        # ====================================================

        if contains_current_term(
            context
        ):

            score += 60

        # ====================================================
        # VERY STRONG FORBES PATTERN
        # ====================================================

        if (
            person
            and person.lower()
            in context_lower
            and "current net worth"
            in context_lower
        ):

            score += 500

        # ====================================================
        # HARD REJECTION OVERRIDES EVERYTHING
        # ====================================================

        if rejected:
            score = -1000

        item = {
            **money,
            "context": context,
            "net_worth_score": score,
            "rejected": rejected,
            "rejection_reason": (
                rejection_reason
            ),
        }

        evidence.append(
            item
        )

    # ========================================================
    # DEBUG MONEY CANDIDATES
    # ========================================================

    for item in evidence:

        print()
        print(
            "[Research] Money candidate:"
        )

        print(
            f"  Value: "
            f"{item.get('raw')}"
        )

        print(
            f"  Score: "
            f"{item.get('net_worth_score')}"
        )

        print(
            f"  Rejected: "
            f"{item.get('rejected')}"
        )

        if item.get(
            "rejection_reason"
        ):

            print(
                f"  Reason: "
                f"{item.get('rejection_reason')}"
            )

        print(
            f"  Context: "
            f"{item.get('context', '')[:450]}"
        )

    # ========================================================
    # REMOVE REJECTED VALUES
    # ========================================================

    evidence = [
        item
        for item in evidence
        if not item.get(
            "rejected",
            False,
        )
    ]

    evidence.sort(
        key=lambda item: (
            item.get(
                "net_worth_score",
                0,
            ),
            item.get(
                "value",
                0,
            ),
        ),
        reverse=True,
    )

    return evidence


# ============================================================
# PAGE FACT EXTRACTION
# ============================================================

def extract_page_fact(
    result,
    page,
):

    if not result or not page:
        return None

    url = result.get(
        "url",
        "",
    )

    if not is_trusted_wealth_domain(
        url
    ):
        return None

    title = clean_text(
        result.get(
            "title",
            "",
        )
    )

    snippet = clean_text(
        result.get(
            "snippet",
            "",
        )
    )

    page_html = page.get(
        "html",
        "",
    )

    page_text = extract_page_text(
        page_html
    )

    metadata = extract_page_metadata(
        page_html
    )

    combined = clean_text(
        " ".join(
            [
                title,
                snippet,
                page_text,
                *metadata,
            ]
        )
    )

    if not combined:
        return None

    # ========================================================
    # PERSON
    # ========================================================

    person = extract_person_near_wealth(
        combined
    )

    if not person:

        person = extract_known_person(
            combined
        )

    if not person:
        return None

    # ========================================================
    # MONEY
    # ========================================================

    evidence_candidates = []

    # Page content
    evidence_candidates.extend(
        extract_money_evidence(
            page_text,
            person,
        )
    )

    # Metadata / embedded JSON
    for metadata_text in metadata:

        evidence_candidates.extend(
            extract_money_evidence(
                metadata_text,
                person,
            )
        )

    # Search snippet fallback
    evidence_candidates.extend(
        extract_money_evidence(
            (
                title
                + ". "
                + snippet
            ),
            person,
        )
    )

    if not evidence_candidates:
        return None

    # ========================================================
    # CRITICAL:
    #
    # Strongest net-worth context wins.
    # Largest amount DOES NOT automatically win.
    # ========================================================

    evidence_candidates.sort(
        key=lambda item: (
            item.get(
                "net_worth_score",
                0,
            ),
            item.get(
                "value",
                0,
            ),
        ),
        reverse=True,
    )

    best = evidence_candidates[0]

    # Must have strong evidence.
    if best.get(
        "net_worth_score",
        0,
    ) < 200:

        print(
            "[Research] No strong explicit "
            "net-worth monetary evidence "
            "found on this page."
        )

        return None

    combined_lower = (
        combined.lower()
    )

    return {
        "person": person,

        "amount": best.get(
            "value"
        ),

        "amount_raw": best.get(
            "raw"
        ),

        "currency": best.get(
            "currency",
            "",
        ),

        "unit": best.get(
            "unit",
            "",
        ),

        "title": title,

        "snippet": snippet,

        "url": page.get(
            "url",
            url,
        ),

        "domain": domain_from_url(
            page.get(
                "url",
                url,
            )
        ),

        "authority": source_authority(
            url
        ),

        "current": any(
            term in combined_lower
            for term in CURRENT_TERMS
        ),

        "richest": any(
            term in combined_lower
            for term in RICHEST_TERMS
        ),

        "evidence_excerpt": best.get(
            "context",
            "",
        ),

        "net_worth_score": best.get(
            "net_worth_score",
            0,
        ),
    }


# ============================================================
# PERSON-ONLY EVIDENCE
# ============================================================

def extract_person_evidence(
    result,
    page,
):

    if not result or not page:
        return None

    url = result.get(
        "url",
        "",
    )

    if not is_trusted_wealth_domain(
        url
    ):
        return None

    page_html = page.get(
        "html",
        "",
    )

    page_text = extract_page_text(
        page_html
    )

    metadata = extract_page_metadata(
        page_html
    )

    title = clean_text(
        result.get(
            "title",
            "",
        )
    )

    snippet = clean_text(
        result.get(
            "snippet",
            "",
        )
    )

    combined = clean_text(
        " ".join(
            [
                title,
                snippet,
                page_text,
                *metadata,
            ]
        )
    )

    person = extract_known_person(
        combined
    )

    if not person:
        return None

    if not (
        contains_wealth_term(
            combined
        )
        or contains_richest_term(
            combined
        )
    ):

        return None

    return {
        "person": person,

        "title": title,

        "snippet": snippet,

        "url": page.get(
            "url",
            url,
        ),

        "domain": domain_from_url(
            page.get(
                "url",
                url,
            )
        ),

        "authority": source_authority(
            url
        ),

        "current": contains_current_term(
            combined
        ),

        "richest": contains_richest_term(
            combined
        ),
    }


# ============================================================
# VERIFIED FACT FROM SEARCH SNIPPET
# ============================================================

def extract_verified_fact(result):

    title = clean_text(
        result.get(
            "title",
            "",
        )
    )

    snippet = clean_text(
        result.get(
            "snippet",
            "",
        )
    )

    url = result.get(
        "url",
        "",
    )

    combined = clean_text(
        title
        + ". "
        + snippet
    )

    if not combined:
        return None

    if not is_trusted_wealth_domain(
        url
    ):
        return None

    person = extract_person_near_wealth(
        combined
    )

    if not person:

        person = extract_known_person(
            combined
        )

    if not person:
        return None

    evidence = extract_money_evidence(
        combined,
        person,
    )

    if not evidence:
        return None

    best = evidence[0]

    if best.get(
        "net_worth_score",
        0,
    ) < 200:

        return None

    return {
        "person": person,

        "amount": best.get(
            "value"
        ),

        "amount_raw": best.get(
            "raw"
        ),

        "currency": best.get(
            "currency",
            "",
        ),

        "unit": best.get(
            "unit",
            "",
        ),

        "title": title,

        "snippet": snippet,

        "url": url,

        "domain": domain_from_url(
            url
        ),

        "authority": source_authority(
            url
        ),

        "current": contains_current_term(
            combined
        ),

        "richest": contains_richest_term(
            combined
        ),

        "evidence_excerpt": best.get(
            "context",
            "",
        ),

        "net_worth_score": best.get(
            "net_worth_score",
            0,
        ),
    }


# ============================================================
# SEARCH QUERIES
# ============================================================

def build_richest_queries():

    return [
        (
            'site:forbes.com '
            '"richest person" '
            f'"{CURRENT_YEAR}" '
            '"net worth"'
        ),
        (
            'site:forbes.com '
            '"richest person" '
            '"right now"'
        ),
        (
            'site:forbes.com '
            '"real-time billionaires"'
        ),
        (
            'site:bloomberg.com '
            '"richest person" '
            f'"{CURRENT_YEAR}"'
        ),
        (
            'site:forbes.com '
            '"Elon Musk" '
            '"net worth" '
            f'"{CURRENT_YEAR}"'
        ),
        (
            'site:bloomberg.com '
            '"Elon Musk" '
            '"net worth"'
        ),
    ]


def build_value_queries():

    return [
        (
            'site:forbes.com '
            '"Elon Musk" '
            '"current net worth"'
        ),
        (
            'site:forbes.com '
            '"Elon Musk" '
            '"net worth"'
        ),
        (
            'site:forbes.com '
            '"Elon Musk" '
            '"real-time"'
        ),
        (
            'site:bloomberg.com '
            '"Elon Musk" '
            '"net worth"'
        ),
    ]


def build_general_queries(question):

    return [
        f'"{question}"',
        f'"{question}" Reuters',
        f'"{question}" AP',
        f'"{question}" BBC',
        f'"{question}" official',
    ]


# ============================================================
# RICHEST QUERY DETECTION
# ============================================================

def is_richest_query(question):

    if not question:
        return False

    lowered = question.lower()

    patterns = [
        r"\brichest person\b",
        r"\brichest man\b",
        r"\brichest woman\b",
        r"\bwho is the richest\b",
        r"\bwho is richest\b",
        r"\bwealthiest person\b",
        r"\bworld'?s richest\b",
    ]

    return any(
        re.search(
            pattern,
            lowered,
        )
        for pattern in patterns
    )


# ============================================================
# PAGE RESEARCH
# ============================================================

def research_source_page(result):

    url = result.get(
        "url",
        "",
    )

    if not is_trusted_wealth_domain(
        url
    ):

        return {
            "result": result,
            "page": None,
            "fact": None,
            "person_evidence": None,
        }

    page = fetch_source_page(
        url
    )

    if not page:

        return {
            "result": result,
            "page": None,
            "fact": None,
            "person_evidence": None,
        }

    fact = extract_page_fact(
        result,
        page,
    )

    person_evidence = None

    if not fact:

        person_evidence = (
            extract_person_evidence(
                result,
                page,
            )
        )

    return {
        "result": result,
        "page": page,
        "fact": fact,
        "person_evidence": (
            person_evidence
        ),
    }


# ============================================================
# CROSS-CHECK FACTS
# ============================================================

def cross_check_facts(facts):

    if not facts:
        return []

    grouped = {}

    for fact in facts:

        person = fact.get(
            "person"
        )

        amount = fact.get(
            "amount"
        )

        if not person:
            continue

        if not isinstance(
            amount,
            (int, float),
        ):
            continue

        key = (
            person.lower(),
            round(
                amount,
                -6,
            ),
        )

        grouped.setdefault(
            key,
            [],
        ).append(
            fact
        )

    verified = []

    for group in grouped.values():

        if not group:
            continue

        best = max(
            group,
            key=lambda fact: (
                fact.get(
                    "net_worth_score",
                    0,
                ),
                fact.get(
                    "authority",
                    0,
                ),
                int(
                    fact.get(
                        "current",
                        False,
                    )
                ),
            ),
        )

        copy = dict(
            best
        )

        copy[
            "supporting_sources"
        ] = len(group)

        verified.append(
            copy
        )

    return verified


# ============================================================
# RICHEST-PERSON RESEARCH
# ============================================================

def fast_richest_research(results):

    print(
        "[Research] Richest-person "
        "query detected."
    )

    candidates = []

    # ========================================================
    # SEARCH SNIPPETS
    # ========================================================

    for result in results:

        fact = extract_verified_fact(
            result
        )

        if fact:
            candidates.append(
                fact
            )

    # ========================================================
    # TARGETED SEARCH
    # ========================================================

    value_results = []

    if not candidates:

        print()
        print(
            "[Research] No verified "
            "net-worth value found in "
            "first-pass snippets."
        )

        print(
            "[Research] Starting targeted "
            "wealth-value search."
        )

        queries = build_value_queries()

        with ThreadPoolExecutor(
            max_workers=len(
                queries
            )
        ) as executor:

            futures = [
                executor.submit(
                    search_bing,
                    query,
                    True,
                )
                for query in queries
            ]

            for future in as_completed(
                futures
            ):

                try:

                    value_results.extend(
                        future.result()
                    )

                except Exception as error:

                    print(
                        "[Research] Targeted "
                        f"search error: {error}"
                    )

        print(
            "[Research] Targeted raw results: "
            f"{len(value_results)}"
        )

        value_results = (
            deduplicate_results(
                value_results
            )
        )

        print(
            "[Research] Targeted unique results: "
            f"{len(value_results)}"
        )

        for result in value_results:

            fact = extract_verified_fact(
                result
            )

            if fact:
                candidates.append(
                    fact
                )

    # ========================================================
    # PAGE QUEUE
    # ========================================================

    combined_results = (
        results
        + value_results
    )

    combined_results = (
        deduplicate_results(
            combined_results
        )
    )

    # ========================================================
    # AUTHORITATIVE PAGE EXTRACTION
    # ========================================================

    print()
    print(
        "[Research] Starting authoritative "
        "page extraction."
    )

    page_facts = []

    person_evidence = []

    if combined_results:

        with ThreadPoolExecutor(
            max_workers=min(
                8,
                len(combined_results),
            )
        ) as executor:

            futures = [
                executor.submit(
                    research_source_page,
                    result,
                )
                for result in combined_results
            ]

            for future in as_completed(
                futures
            ):

                try:

                    researched = (
                        future.result()
                    )

                except Exception as error:

                    print(
                        "[Research] Page worker "
                        f"error: {error}"
                    )

                    continue

                fact = researched.get(
                    "fact"
                )

                if fact:

                    page_facts.append(
                        fact
                    )

                person = researched.get(
                    "person_evidence"
                )

                if person:

                    person_evidence.append(
                        person
                    )

    print()
    print(
        f"[Research] Page facts found: "
        f"{len(page_facts)}"
    )

    print(
        f"[Research] Person evidence found: "
        f"{len(person_evidence)}"
    )

    candidates.extend(
        page_facts
    )

    # ========================================================
    # CROSS-CHECK
    # ========================================================

    verified = cross_check_facts(
        candidates
    )

    # ========================================================
    # DEBUG SEARCH RESULTS
    # ========================================================

    print()
    print(
        "=" * 70
    )

    print(
        "[Research] TRUSTED SEARCH RESULTS"
    )

    print(
        "=" * 70
    )

    for index, result in enumerate(
        combined_results[:20],
        start=1,
    ):

        print()
        print(
            f"RESULT {index}"
        )

        print(
            f"Domain: "
            f"{result.get('domain', '')}"
        )

        print(
            f"Title: "
            f"{result.get('title', '')}"
        )

        print(
            f"Snippet: "
            f"{result.get('snippet', '')}"
        )

        print(
            f"URL: "
            f"{result.get('url', '')}"
        )

    print()
    print(
        "=" * 70
    )

    # ========================================================
    # VERIFIED FACT
    # ========================================================

    if verified:

        verified.sort(
            key=lambda fact: (
                fact.get(
                    "net_worth_score",
                    0,
                ),
                fact.get(
                    "authority",
                    0,
                ),
                int(
                    fact.get(
                        "current",
                        False,
                    )
                ),
                fact.get(
                    "supporting_sources",
                    0,
                ),
            ),
            reverse=True,
        )

        best = verified[0]

        print()
        print(
            "=" * 70
        )

        print(
            "[Research] VERIFIED FACT"
        )

        print(
            "=" * 70
        )

        print(
            f"Person: "
            f"{best.get('person')}"
        )

        print(
            f"Amount: "
            f"{best.get('amount_raw')}"
        )

        print(
            f"Net-worth score: "
            f"{best.get('net_worth_score')}"
        )

        print(
            f"Supporting sources: "
            f"{best.get('supporting_sources', 1)}"
        )

        print(
            f"Source: "
            f"{best.get('url')}"
        )

        print(
            f"Evidence: "
            f"{best.get('evidence_excerpt', '')}"
        )

        print(
            "=" * 70
        )

        return [
            {
                "title": best.get(
                    "title",
                    "",
                ),

                "url": best.get(
                    "url",
                    "",
                ),

                "domain": best.get(
                    "domain",
                    "",
                ),

                "snippet": best.get(
                    "snippet",
                    "",
                ),

                "evidence_excerpt": best.get(
                    "evidence_excerpt",
                    "",
                ),

                "authority": best.get(
                    "authority",
                    0,
                ),

                "verified_fact": {
                    "person": best.get(
                        "person"
                    ),

                    "amount": best.get(
                        "amount"
                    ),

                    "amount_raw": best.get(
                        "amount_raw"
                    ),

                    "currency": best.get(
                        "currency"
                    ),

                    "unit": best.get(
                        "unit"
                    ),

                    "supporting_sources": (
                        best.get(
                            "supporting_sources",
                            1,
                        )
                    ),
                },
            }
        ]

    # ========================================================
    # PERSON ONLY
    # ========================================================

    if person_evidence:

        person_evidence.sort(
            key=lambda item: (
                item.get(
                    "authority",
                    0,
                ),
                int(
                    item.get(
                        "current",
                        False,
                    )
                ),
                int(
                    item.get(
                        "richest",
                        False,
                    )
                ),
            ),
            reverse=True,
        )

        best_person = (
            person_evidence[0]
        )

        print()
        print(
            "[Research] Person identified "
            "but exact current net worth "
            "was not verified."
        )

        print(
            f"[Research] Person: "
            f"{best_person.get('person')}"
        )

        return [
            {
                "title": best_person.get(
                    "title",
                    "",
                ),

                "url": best_person.get(
                    "url",
                    "",
                ),

                "domain": best_person.get(
                    "domain",
                    "",
                ),

                "snippet": best_person.get(
                    "snippet",
                    "",
                ),

                "authority": best_person.get(
                    "authority",
                    0,
                ),

                "verified_fact": None,

                "person_evidence": {
                    "person": best_person.get(
                        "person"
                    ),

                    "current": best_person.get(
                        "current",
                        False,
                    ),

                    "richest": best_person.get(
                        "richest",
                        False,
                    ),
                },
            }
        ]

    print(
        "[Research] No verified "
        "richest-person fact found."
    )

    return []


# ============================================================
# GENERAL RESEARCH
# ============================================================

def score_general_result(
    result,
    question,
):

    title = clean_text(
        result.get(
            "title",
            "",
        )
    )

    snippet = clean_text(
        result.get(
            "snippet",
            "",
        )
    )

    url = result.get(
        "url",
        "",
    )

    combined = (
        title
        + " "
        + snippet
    ).lower()

    score = source_authority(
        url
    )

    words = re.findall(
        r"[a-zA-Z]{4,}",
        question.lower(),
    )

    for word in set(words):

        if word in combined:
            score += 10

    if contains_current_term(
        combined
    ):
        score += 20

    return score


def general_research(
    question,
    results,
):

    ranked = sorted(
        results,
        key=lambda result: (
            score_general_result(
                result,
                question,
            )
        ),
        reverse=True,
    )

    selected = []

    for result in ranked:

        title = clean_text(
            result.get(
                "title",
                "",
            )
        )

        snippet = clean_text(
            result.get(
                "snippet",
                "",
            )
        )

        if not title and not snippet:
            continue

        selected.append(
            {
                "title": title,

                "url": result.get(
                    "url",
                    "",
                ),

                "domain": result.get(
                    "domain",
                    "",
                ),

                "snippet": snippet,

                "authority": (
                    source_authority(
                        result.get(
                            "url",
                            "",
                        )
                    )
                ),

                "evidence_excerpt": (
                    snippet[:1200]
                ),
            }
        )

        if len(
            selected
        ) >= MAX_SOURCES:

            break

    return selected


# ============================================================
# MAIN RESEARCH
# ============================================================

def research(question):

    print()
    print(
        "=" * 70
    )

    print(
        "[Research] Starting research"
    )

    print(
        "=" * 70
    )

    question = clean_text(
        question
    )

    if not question:

        print(
            "[Research] Empty question."
        )

        return []

    richest_query = is_richest_query(
        question
    )

    if richest_query:

        queries = (
            build_richest_queries()
        )

    else:

        queries = (
            build_general_queries(
                question
            )
        )

    print(
        "[Research] Search plan:"
    )

    for query in queries:

        print(
            f"  -> {query}"
        )

    results = []

    with ThreadPoolExecutor(
        max_workers=min(
            8,
            len(queries),
        )
    ) as executor:

        futures = [
            executor.submit(
                search_bing,
                query,
                richest_query,
            )
            for query in queries
        ]

        for future in as_completed(
            futures
        ):

            try:

                results.extend(
                    future.result()
                )

            except Exception as error:

                print(
                    "[Research] Search worker "
                    f"error: {error}"
                )

    print()
    print(
        "[Research] Raw search results: "
        f"{len(results)}"
    )

    results = deduplicate_results(
        results
    )

    print(
        "[Research] Unique results: "
        f"{len(results)}"
    )

    if richest_query:

        return fast_richest_research(
            results
        )

    return general_research(
        question,
        results,
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print(
        "=" * 70
    )

    print(
        "VEYRiX RESEARCH TEST"
    )

    print(
        "=" * 70
    )

    question = (
        "Who is the richest person "
        "right now?"
    )

    sources = research(
        question
    )

    print()
    print(
        "=" * 70
    )

    print(
        "FINAL RESULT"
    )

    print(
        "=" * 70
    )

    if not sources:

        print(
            "No verified sources returned."
        )

    for index, source in enumerate(
        sources,
        start=1,
    ):

        print()
        print(
            f"SOURCE {index}"
        )

        print(
            "Title:",
            source.get(
                "title",
                "",
            ),
        )

        print(
            "Domain:",
            source.get(
                "domain",
                "",
            ),
        )

        print(
            "URL:",
            source.get(
                "url",
                "",
            ),
        )

        print(
            "Evidence:",
            source.get(
                "evidence_excerpt",
                "",
            ),
        )

        if source.get(
            "verified_fact"
        ):

            print(
                "Verified fact:"
            )

            print(
                source[
                    "verified_fact"
                ]
            )

        elif source.get(
            "person_evidence"
        ):

            print(
                "Person evidence:"
            )

            print(
                source[
                    "person_evidence"
                ]
            )

    print()
    print(
        "=" * 70
    )