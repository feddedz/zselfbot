"""Usage: !headers https://example.com

Fetch HTTP headers and show key security and server headers.
"""

import asyncio
import urllib.parse
import urllib.request


async def run(client, message, args):
    """Fetch HTTP headers for a URL and display selected headers. Usage: !headers <url>"""
    url = args.strip()
    if not url:
        await message.channel.send("Usage: `!headers <url>`")
        return
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "http://" + url

    def _fetch():
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "zselfbot-osint/1.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            status = r.getcode()
            final = r.geturl()
            headers = dict(r.getheaders())
            return status, final, headers

    try:
        status, final, headers = await asyncio.to_thread(_fetch)
    except Exception as e:
        await message.channel.send(f"Error fetching URL: {e}")
        return

    keys = [
        "server",
        "content-type",
        "content-length",
        "set-cookie",
        "strict-transport-security",
        "content-security-policy",
        "x-frame-options",
        "x-xss-protection",
        "referrer-policy",
    ]
    lines = [f"{status} - {final}"]
    for k in keys:
        v = headers.get(k) or headers.get(k.title())
        if v:
            val = v if len(v) < 800 else v[:800] + "…"
            lines.append(f"{k}: {val}")

    await message.channel.send("\n".join(lines))
