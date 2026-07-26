"""Usage: !dns example.com A

DNS lookup via Google DNS-over-HTTPS. Supports common record types.
"""

import asyncio
import json
import urllib.parse
import urllib.request
import time

_API = "https://dns.google/resolve?name={}&type={}&cd=true"
_CACHE_TTL = 1800


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
    """DNS lookup: !dns <name> [type]. Type defaults to A. Examples: A, MX, NS, TXT, CNAME, AAAA"""
    parts = args.strip().split()
    if not parts:
        await message.channel.send("Usage: `!dns <name> [type]` (type defaults to A)")
        return
    name = parts[0]
    qtype = parts[1].upper() if len(parts) > 1 else "A"

    key = f"osint:dns:{name}:{qtype}"
    cached = _cache_get(client, key)
    if cached:
        await message.channel.send(cached)
        return

    url = _API.format(urllib.parse.quote(name), urllib.parse.quote(qtype))
    try:
        def _f():
            with urllib.request.urlopen(url, timeout=10) as r:
                return r.read()
        data = await asyncio.to_thread(_f)
        obj = json.loads(data)
    except Exception as e:
        await message.channel.send(f"DNS request failed: {e}")
        return

    if not obj.get("Answer"):
        # maybe NXDOMAIN or no results
        await message.channel.send(f"No answers for {name} {qtype} (Status {obj.get('Status')}).")
        return

    lines = [f"**DNS {qtype} for {name}**"]
    for a in obj.get("Answer", [])[:30]:
        ttl = a.get("TTL")
        data = a.get("data")
        lines.append(f"{data}  (TTL: {ttl})")

    out = "\n".join(lines)
    _cache_set(client, key, out)
    await message.channel.send(out)
