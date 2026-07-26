"""Usage: !crtsearch example.com

Query crt.sh for certificate entries and extract subdomains (deduped). Caches results.
"""

import asyncio
import json
import urllib.parse
import urllib.request
import time

_API = "https://crt.sh/?q=%25{}&output=json"
_CACHE_TTL = 6 * 3600


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


async def run(client, message, args):
    """crt.sh subdomain discovery. Usage: !crtsearch <domain>"""
    domain = args.strip().lower()
    if not domain:
        await message.channel.send("Usage: `!crtsearch <domain>`")
        return

    key = f"osint:crt:{domain}"
    cached = _cache_get(client, key)
    if cached:
        await message.channel.send(cached)
        return

    url = _API.format(urllib.parse.quote(domain))
    try:
        def _f():
            with urllib.request.urlopen(url, timeout=20) as r:
                return r.read()
        data = await asyncio.to_thread(_f)
        obj = json.loads(data)
    except Exception as e:
        await message.channel.send(f"crt.sh lookup failed: {e}")
        return

    names = set()
    for entry in obj:
        name = entry.get("name_value") or ""
        for n in name.split("\n"):
            n = n.strip().lower()
            if n:
                names.add(n)

    if not names:
        await message.channel.send("No certificate names found.")
        return

    out_list = sorted(names)[:60]
    lines = [f"Found {len(names)} names (showing {len(out_list)}):"]
    lines.extend(out_list)
    out = "\n".join(lines)
    _cache_set(client, key, out)
    await message.channel.send(out)
