"""Usage: !geoip 8.8.8.8 or !geoip example.com

GeoIP lookup using ip-api.com with short caching.
"""

import asyncio
import json
import urllib.parse
import urllib.request
import time

_API = "http://ip-api.com/json/{}?fields=status,message,country,regionName,city,isp,org,as,query,lat,lon,timezone,reverse"
_CACHE_TTL = 3600  # 1 hour


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
    """GeoIP lookup (ip-api.com). Usage: !geoip <ip_or_hostname>"""
    target = args.strip()
    if not target:
        await message.channel.send("Usage: `!geoip <ip_or_hostname>`")
        return

    key = f"osint:geoip:{target}"
    cached = _cache_get(client, key)
    if cached:
        await message.channel.send(cached)
        return

    url = _API.format(urllib.parse.quote(target))

    try:
        def _fetch():
            with urllib.request.urlopen(url, timeout=10) as r:
                return r.read()
        data = await asyncio.to_thread(_fetch)
        obj = json.loads(data)
    except Exception as e:
        await message.channel.send(f"Error fetching GeoIP: {e}")
        return

    if obj.get("status") != "success":
        await message.channel.send(f"Lookup failed: {obj.get('message','unknown')}")
        return

    lines = [
        f"**GeoIP for** `{obj.get('query')}`",
        f"Location: {obj.get('city')}, {obj.get('regionName')}, {obj.get('country')}",
        f"ISP: {obj.get('isp')}  |  Org: {obj.get('org')}",
        f"ASN: {obj.get('as')}",
        f"Coordinates: {obj.get('lat')}, {obj.get('lon')}  |  TZ: {obj.get('timezone')}",
    ]
    if obj.get("reverse"):
        lines.append(f"Reverse DNS: `{obj.get('reverse')}`")

    out = "\n".join(lines)
    _cache_set(client, key, out)
    await message.channel.send(out)
