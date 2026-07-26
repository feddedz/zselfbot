"""Usage: !reverseip 93.184.216.34

Reverse IP lookup using hackertarget free API (rate-limited). Caches results.
"""

import asyncio
import urllib.parse
import urllib.request
import time

_API = "https://api.hackertarget.com/reverseiplookup/?q={}"
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
    """Reverse IP: list domains hosted on the same IP/host. Usage: !reverseip <ip_orhost>"""
    target = args.strip()
    if not target:
        await message.channel.send("Usage: `!reverseip <ip_or_host>`")
        return

    key = f"osint:reverseip:{target}"
    cached = _cache_get(client, key)
    if cached:
        await message.channel.send(cached)
        return

    url = _API.format(urllib.parse.quote(target))
    try:
        def _f():
            with urllib.request.urlopen(url, timeout=15) as r:
                return r.read().decode(errors="ignore")
        data = await asyncio.to_thread(_f)
    except Exception as e:
        await message.channel.send(f"Reverse IP lookup failed: {e}")
        return

    if not data or data.lower().startswith("error") or "no records" in data.lower():
        await message.channel.send(f"No reverse-ip results or API limit: {data.strip()}")
        return

    domains = [line.strip() for line in data.splitlines() if line.strip()]
    domains = domains[:60]
    lines = [f"Found {len(domains)} domains (showing up to 60):"] + domains
    out = "\n".join(lines)
    _cache_set(client, key, out)
    await message.channel.send(out)
