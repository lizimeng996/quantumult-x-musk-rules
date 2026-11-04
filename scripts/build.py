#!/usr/bin/env python3
"""Build X 全家 rule sets (X/Twitter, Grok/xAI, SpaceX/Starlink) for Quantumult X and Loon.
Tesla is deliberately EXCLUDED (Tesla China must go direct). Standard library only.
Usage: python3 scripts/build.py
"""
import ipaddress, json, re, sys, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "quantumult-x-musk-rules-builder"}
REPO = "https://github.com/lizimeng996/quantumult-x-musk-rules"
V2FLY = "https://raw.githubusercontent.com/v2fly/domain-list-community/master/data/{}"
BM7_TWITTER = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/Twitter/Twitter.list"
VPSD_XAI = "https://raw.githubusercontent.com/VPSDance/ai-proxy-rules/main/rules/quantumult-x/x-ai.list"
TWITTER_ASNS = [13414]  # TWITTER (RIPEstat)

GROK_CORE = [("HOST-SUFFIX", d) for d in ("grok.com", "grok.x.com", "grokipedia.com", "x.ai")]
X_CORE = [("HOST-SUFFIX", d) for d in ("x.com", "twitter.com", "twimg.com", "t.co", "pscp.tv", "periscope.tv")]
# No upstream list for SpaceX besides v2fly's tiny one; all verified via DNS.
SPACEX_MANUAL = [("HOST-SUFFIX", d) for d in ("spacex.com", "starlink.com", "starshield.com")]

# Never emit: Tesla (user needs Tesla China direct) and over-broad keywords.
TESLA_RE = re.compile(r"(^|\.)(tesla|teslamotors|teslaenergy|teslazta|solarcity|ts\.la)|tesla", re.I)
BAD_KEYWORDS = {"twitter", "x", "grok", "tesla"}
FAKE_NETS = [ipaddress.ip_network(n) for n in ("198.18.0.0/15", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
             "127.0.0.0/8", "100.64.0.0/10", "0.0.0.0/8", "fc00::/7", "fe80::/10", "::1/128")]
DOMAIN_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9_]([a-z0-9_-]{0,61}[a-z0-9_])?\.)+[a-z0-9-]{2,63}$")
TYPE_MAP = {"DOMAIN": "HOST", "DOMAIN-SUFFIX": "HOST-SUFFIX", "DOMAIN-KEYWORD": "HOST-KEYWORD", "HOST": "HOST",
            "HOST-SUFFIX": "HOST-SUFFIX", "HOST-KEYWORD": "HOST-KEYWORD", "IP-CIDR": "IP-CIDR",
            "IP6-CIDR": "IP6-CIDR", "IP-CIDR6": "IP6-CIDR", "IP-ASN": "IP-ASN"}
ORDER = {"HOST": 0, "HOST-SUFFIX": 1, "HOST-KEYWORD": 2, "IP-CIDR": 3, "IP6-CIDR": 4, "IP-ASN": 5}
LOON_MAP = {"HOST": "DOMAIN", "HOST-SUFFIX": "DOMAIN-SUFFIX", "HOST-KEYWORD": "DOMAIN-KEYWORD",
            "IP-CIDR": "IP-CIDR", "IP6-CIDR": "IP-CIDR6", "IP-ASN": "IP-ASN"}


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def parse_rules(text):
    out = []
    for line in text.splitlines():
        line = "" if line.lstrip().startswith("#") else line.split("#", 1)[0].strip()
        parts = [p.strip() for p in line.split(",")]
        t = TYPE_MAP.get(parts[0].upper()) if line else None
        if t and len(parts) >= 2:
            out.append((t, parts[1].lower()))
    return out


def v2fly(name):
    out = []
    for raw in fetch(V2FLY.format(name)).splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith(("include:", "regexp:")):
            continue
        val = line.split()[0]
        if val.startswith("full:"):
            out.append(("HOST", val[5:].lower()))
        elif not val.startswith("keyword:"):
            out.append(("HOST-SUFFIX", val.removeprefix("domain:").lower()))
    return out


def asn_prefixes(asn):
    url = f"https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS{asn}&sourceapp=quantumult-x-musk-rules"
    return [ipaddress.ip_network(p["prefix"], strict=False) for p in json.loads(fetch(url))["data"]["prefixes"]]


def valid(rule):
    t, v = rule
    if TESLA_RE.search(v):
        return False
    if t in ("HOST", "HOST-SUFFIX"):
        return bool(DOMAIN_RE.match(v))
    if t == "HOST-KEYWORD":
        return False  # keywords too broad; not emitted
    if t in ("IP-CIDR", "IP6-CIDR"):
        try:
            n = ipaddress.ip_network(v, strict=False)
        except ValueError:
            return False
        return (t == "IP-CIDR") == (n.version == 4) and not any(n.version == f.version and n.overlaps(f) for f in FAKE_NETS)
    if t == "IP-ASN":
        return v.isdigit()
    return False


def normalise(rules, parents=()):
    """Dedupe; drop rules covered by a HOST-SUFFIX in this set or in `parents` (earlier sections)."""
    rules = {r for r in rules if valid(r)}
    suffixes = {v for t, v in rules if t == "HOST-SUFFIX"}
    psuf = {v for t, v in parents if t == "HOST-SUFFIX"}
    out = []
    for t, v in rules:
        if (t, v) in parents:
            continue
        if t in ("HOST", "HOST-SUFFIX"):
            labels = v.split(".")
            start = 1 if t == "HOST-SUFFIX" else 0
            if any(".".join(labels[i:]) in suffixes for i in range(start, len(labels) - 1)):
                continue
            if any(".".join(labels[i:]) in psuf for i in range(0, len(labels) - 1)):
                continue
        out.append((t, v))
    return sorted(out, key=sort_key)


def sort_key(r):
    t, v = r
    if t in ("IP-CIDR", "IP6-CIDR"):
        n = ipaddress.ip_network(v)
        return (ORDER[t], n.network_address.packed, n.prefixlen)
    return (ORDER[t], int(v)) if t == "IP-ASN" else (ORDER[t], v)


def header(name, desc, rules, sources):
    counts = {}
    for t, _ in rules:
        counts[t] = counts.get(t, 0) + 1
    h = [f"# NAME: {name}", "# AUTHOR: lizimeng996", f"# REPO: {REPO}",
         f"# UPDATED: {datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')}"]
    h += [f"# {t}: {counts[t]}" for t in sorted(counts, key=ORDER.get)]
    return h + [f"# TOTAL: {len(rules)}"]


def fmt(t, v, name, loon):
    if not loon:
        return f"{t},{v},{name}"
    return f"{LOON_MAP[t]},{v}" + (",no-resolve" if t in ("IP-CIDR", "IP6-CIDR", "IP-ASN") else "")


def write(name, desc, sections, sources):
    allr = sorted({r for _, rs in sections for r in rs}, key=lambda r: (ORDER[r[0]], r[1]))
    for loon, d in ((False, "QuantumultX"), (True, "Loon")):
        body = [fmt(t, v, name, loon) for t, v in allr]
        (ROOT / d).mkdir(exist_ok=True)
        (ROOT / d / f"{name}.list").write_text("\n".join(header(name, desc, allr, sources) + body) + "\n")
    return len(allr)


QX_LINE = re.compile(r"^(HOST|HOST-SUFFIX|IP-CIDR|IP6-CIDR|IP-ASN),[^,\s]+,[A-Za-z0-9_-]+$")
LOON_LINE = re.compile(r"^(DOMAIN|DOMAIN-SUFFIX|IP-CIDR|IP-CIDR6|IP-ASN),[^,\s]+(,no-resolve)?$")


def validate():
    bad = []
    for d, rx in (("QuantumultX", QX_LINE), ("Loon", LOON_LINE)):
        for p in (ROOT / d).glob("*.list"):
            n = 0
            for i, line in enumerate(p.read_text().splitlines(), 1):
                if not line or line.startswith("#"):
                    continue
                n += 1
                if not rx.match(line) or TESLA_RE.search(line):
                    bad.append(f"{d}/{p.name}:{i}: {line}")
            if n == 0:
                bad.append(f"{d}/{p.name}: empty")
    return bad


def safe(label, fn, default):
    try:
        return fn()
    except Exception as e:  # upstream outage must not wipe our list
        print(f"WARN: {label}: {e}", file=sys.stderr)
        return default


def main():
    bm7 = safe("blackmatrix7 Twitter", lambda: parse_rules(fetch(BM7_TWITTER)), [])
    grok_src = GROK_CORE + safe("VPSDance x-ai", lambda: parse_rules(fetch(VPSD_XAI)), []) + safe("v2fly xai", lambda: v2fly("xai"), [])
    x_src = X_CORE + [r for r in bm7 if r[0] in ("HOST", "HOST-SUFFIX")] + safe("v2fly twitter", lambda: v2fly("twitter"), [])
    sp_src = SPACEX_MANUAL + safe("v2fly spacex", lambda: v2fly("spacex"), [])
    ip_src = [r for r in bm7 if r[0] in ("IP-CIDR", "IP6-CIDR")]
    nets = [ipaddress.ip_network(v) for _, v in ip_src]
    for asn in TWITTER_ASNS:
        nets += safe(f"RIPEstat AS{asn}", lambda: asn_prefixes(asn), [])
        ip_src.append(("IP-ASN", str(asn)))
    ip_src = [r for r in ip_src if r[0] == "IP-ASN"]
    for v in (4, 6):
        ip_src += [("IP-CIDR" if v == 4 else "IP6-CIDR", str(n))
                   for n in ipaddress.collapse_addresses([x for x in nets if x.version == v])]

    # grok.x.com stays in Grok even though x.com covers it (so Grok can use its own node)
    grok = sorted({r for r in grok_src if valid(r)}, key=sort_key)
    xr = normalise(x_src, parents=set(grok) - {("HOST-SUFFIX", "grok.x.com")})
    sp = normalise(sp_src)
    ips = normalise(ip_src)
    if len(grok) < 3 or len(xr) < 15 or len(sp) < 2 or len(ips) < 3:
        sys.exit(f"ERROR: too few rules grok={len(grok)} x={len(xr)} spacex={len(sp)} ip={len(ips)}")

    srcs = ["VPSDance/ai-proxy-rules", "blackmatrix7/ios_rule_script", "v2fly/domain-list-community", "RIPEstat (AS13414)", "manual"]
    xfull = normalise(x_src + ip_src)
    write("Grok", "Grok / xAI", [("Grok / xAI", grok)], srcs[:1] + srcs[2:3])
    write("Twitter", "X / Twitter domains + Twitter IP ranges", [("X / Twitter", xfull)], srcs[1:4])
    write("SpaceX", "SpaceX / Starlink / Starshield", [("SpaceX / Starlink", sp)], srcs[2:3] + srcs[4:])
    total = write("X", "X 全家: Grok/xAI + X/Twitter + SpaceX/Starlink + Twitter IPs (no Tesla)",
                  [("Grok / xAI", grok), ("X / Twitter", xr), ("SpaceX / Starlink", sp), ("Twitter IP", ips)], srcs)
    bad = validate()
    if bad:
        sys.exit("INVALID LINES:\n" + "\n".join(bad))
    print(f"OK: X.list={total} (grok={len(grok)} x={len(xr)} spacex={len(sp)} ip={len(ips)})")


if __name__ == "__main__":
    main()
