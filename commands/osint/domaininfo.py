"""Usage: !domaininfo example.com

Aggregator: DNS, RDAP, crt.sh subs, and GeoIP for A records. Produces a concise summary.
"""

import asyncio
import json
import urllib.parse
import urllib.request
import time

_CACHE_TTL = 3600


def _cache_get(client, key):
    item = client.storage.get(key)
    if not item:
        return None
    try:
        if item.get("expires", 0) < int(time.time()):
            client.storage.set(key, None)
            return None
        return item.get("value")
    except Exception:
        return None


def _cache_set(client, key, value, ttl=_CACHE_TTL):
    client.storage.set(key, {"value": value, "expires": int(time.time()) + ttl})


async def _fetch_json(url, timeout=12):
    def _f():
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.read()
    data = await asyncio.to_thread(_f)
    return json.loads(data)


async def run(client, message, args):
    """Domain intelligence aggregator. Usage: !domaininfo <domain>"""
    domain = args.strip().lower()
    if not domain:
        await message.channel.send("Usage: `!domaininfo <domain>`")
        return

    key = f"osint:domaininfo:{domain}"
    cached = _cache_get(client, key)
    if cached:
        await message.channel.send(cached)
        return

    out_lines = [f"**Domain info: {domain}**"]

    # DNS A
    try:
        url = f"https://dns.google/resolve?name={urllib.parse.quote(domain)}&type=A"
        data = await _fetch_json(url)
        adds = []
        for a in data.get("Answer", [])[:10]:
            adds.append(a.get("data"))
        if adds:
            out_lines.append("A: " + ", ".join(adds))
    except Exception:
        out_lines.append("A: (lookup failed)")

    # NS
    try:
        url = f"https://dns.google/resolve?name={urllib.parse.quote(domain)}&type=NS"
        data = await _fetch_json(url)
        nss = [a.get("data") for a in data.get("Answer", [])[:10]]
        if nss:
            out_lines.append("NS: " + ", ".join(nss))
    except Exception:
        pass

    # MX
    try:
        url = f"https://dns.google/resolve?name={urllib.parse.quote(domain)}&type=MX"
        data = await _fetch_json(url)
        mxs = [a.get("data") for a in data.get("Answer", [])[:10]]
        if mxs:
            out_lines.append("MX: " + ", ".join(mxs))
    except Exception:
        pass

    # RDAP
    try:
        rdap_url = f"https://rdap.org/domain/{urllib.parse.quote(domain)}"
        try:
            rdap_raw = await asyncio.to_thread(lambda: urllib.request.urlopen(rdap_url, timeout=12).read())
            rdap = json.loads(rdap_raw)
            if rdap.get("handle"):
                out_lines.append(f"Registrar/Handle: {rdap.get('handle')}")
            if rdap.get("events"):
                evs = []
                for e in rdap.get("events", [])[:4]:
                    evs.append(f"{e.get('eventAction')}:{e.get('eventDate')}")
                if evs:
                    out_lines.append("Events: " + ", ".join(evs))
        except Exception:
            out_lines.append("RDAP: failed")
    except Exception:
        pass

    # crt.sh (few subdomains)
    try:
        crt_url = f"https://crt.sh/?q=%25{urllib.parse.quote(domain)}&output=json"
        crt_raw = await asyncio.to_thread(lambda: urllib.request.urlopen(crt_url, timeout=15).read())
        try:
            crt = json.loads(crt_raw)
            names = set()
            for e in crt:
                nv = e.get("name_value") or ""
                for n in nv.split("\n"):
                    names.add(n.strip().lower())
            subs = sorted(names)[:20]
            if subs:
                out_lines.append("Subdomains (crt.sh sample): " + ", ".join(subs))
        except Exception:
            pass
    except Exception:
        pass

    # GeoIP for A records (first 3)
    try:
        a_records = []
        url = f"https://dns.google/resolve?name={urllib.parse.quote(domain)}&type=A"
        data = await _fetch_json(url)
        for a in data.get("Answer", [])[:5]:
            a_records.append(a.get("data"))
        geo_lines = []
        for ip in a_records[:3]:
            try:
                ip_api = f"http://ip-api.com/json/{urllib.parse.quote(ip)}?fields=status,country,regionName,city,isp,query"
                raw = await asyncio.to_thread(lambda url=ip_api: urllib.request.urlopen(url, timeout=10).read())
                obj = json.loads(raw)
                if obj.get("status") == "success":
                    geo_lines.append(f"{ip} ({obj.get('city')}, {obj.get('country')}) {obj.get('isp')}")
            except Exception:
                pass
        if geo_lines:
            out_lines.append("IP Geo: " + " | ".join(geo_lines))
    except Exception:
        pass

    out = "\n".join(out_lines)
    _cache_set(client, key, out)
    await message.channel.send(out)
