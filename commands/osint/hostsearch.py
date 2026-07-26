"""Usage: !hostsearch example.com

Combine hostsearch (hackertarget) and crt.sh to build a richer list of hosts/subdomains. Caches results.
"""

import asyncio
import json
import urllib.parse
import urllib.request
import time

_API_HOST = "https://api.hackertarget.com/hostsearch/?q={}"
_API_CRT = "https://crt.sh/?q=%25{}&output=json"
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
    """Subdomain/host discovery combining hackertarget hostsearch and crt.sh. Usage: !hostsearch <domain>"""
    domain = args.strip().lower()
    if not domain:
        await message.channel.send("Usage: `!hostsearch <domain>`")
        return

    key = f"osint:hostsearch:{domain}"
    cached = _cache_get(client, key)
    if cached:
        await message.channel.send(cached)
        return

    results = set()

    # hackertarget hostsearch (CSV: host,ip)
    try:
        url = _API_HOST.format(urllib.parse.quote(domain))
        raw = await asyncio.to_thread(lambda url=url: urllib.request.urlopen(url, timeout=15).read().decode(errors="ignore"))
        if raw and "error" not in raw.lower():
            for line in raw.splitlines():
                parts = line.split(',')
                if parts:
                    results.add(parts[0].strip().lower())
    except Exception:
        pass

    # crt.sh
    try:
        url = _API_CRT.format(urllib.parse.quote(domain))
        raw = await asyncio.to_thread(lambda url=url: urllib.request.urlopen(url, timeout=15).read())
        try:
            entries = json.loads(raw)
            for e in entries:
                nv = e.get('name_value') or ''
                for n in nv.split('\n'):
                    results.add(n.strip().lower())
        except Exception:
            pass
    except Exception:
        pass

    if not results:
        await message.channel.send("No hosts found or APIs blocked/rate-limited.")
        return

    out_list = sorted(results)[:200]
    out = f"Found {len(results)} names (showing {len(out_list)}):\n" + "\n".join(out_list)
    _cache_set(client, key, out)
    await message.channel.send(out)
