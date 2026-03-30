#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║  NJ Ecological Convergence Map                                       ║
║  Light Pollution × Atlantic Flyway × Sea Turtle Nesting              ║
║                                                                      ║
║  Data sources:                                                       ║
║    · Light pollution  — VIIRS satellite / World Atlas of             ║
║                         Artificial Night-Sky Brightness              ║
║    · Bird migration   — Cornell Lab of Ornithology eBird API v2      ║
║    · Sea turtles      — NOAA NCCOS / NJ DEP field surveys            ║
║                                                                      ║
║  Requires:  pip install -r requirements.txt                          ║
║  eBird key: https://ebird.org/api/keygen  (free, instant)            ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import webbrowser
from datetime import datetime

import folium
import requests
from folium import plugins

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIG  — edit these
# ─────────────────────────────────────────────────────────────────────────────

EBIRD_API_KEY  = "7efudt9leb19"         # https://ebird.org/api/keygen
NJ_REGION_CODE = "US-NJ"
DAYS_BACK      = 14                     # how many days of eBird obs to pull
OUTPUT_FILE    = "nj_eco_map.html"

# ─────────────────────────────────────────────────────────────────────────────
#  STATIC DATA
# ─────────────────────────────────────────────────────────────────────────────

# Known NJ sea turtle nesting sites (NOAA NCCOS / NJ DEP / MMSC field surveys)
SEA_TURTLE_SITES = [
    {
        "name":    "Sandy Hook (Gateway NRA)",
        "lat":      40.4774, "lon": -74.0062,
        "species": ["Loggerhead"],
        "notes":   "Northernmost confirmed loggerhead nesting on the NJ coast. "
                   "Gateway NRA conducts nightly beach patrols June–August. "
                   "Kemp's Ridley juveniles forage in nearby offshore waters but "
                   "do not nest in NJ — nesting is restricted to the Gulf of Mexico.",
    },
    {
        "name":    "Island Beach State Park",
        "lat":      39.8326, "lon": -74.0946,
        "species": ["Loggerhead", "Green Turtle"],
        "notes":   "Primary NJ nesting corridor; IBSP enforces nighttime beach "
                   "lighting restrictions during nesting season.",
    },
    {
        "name":    "Long Beach Island (Harvey Cedars sector)",
        "lat":      39.7048, "lon": -74.1196,
        "species": ["Loggerhead"],
        "notes":   "Occasional nesting; monitored by the Marine Mammal "
                   "Stranding Center of NJ (MMSC).",
    },
    {
        "name":    "Brigantine Beach / Edwin B. Forsythe NWR",
        "lat":      39.4165, "lon": -74.3549,
        "species": ["Loggerhead", "Leatherback"],
        "notes":   "Adjacent to ENWR buffer zone; one of the least light-polluted "
                   "stretches of the NJ coast — critical dark-beach corridor.",
    },
    {
        "name":    "Stone Harbor / Avalon",
        "lat":      39.0534, "lon": -74.7918,
        "species": ["Loggerhead"],
        "notes":   "Nesting frequency has increased since 2010; municipal "
                   "ordinances now restrict beachfront lighting May–October.",
    },
    {
        "name":    "Cape May Point",
        "lat":      38.9326, "lon": -74.9596,
        "species": ["Loggerhead", "Leatherback"],
        "notes":   "Southernmost NJ nesting concentration; Cape May Bird "
                   "Observatory light-reduction programme active. Neonates "
                   "use lunar/horizon gradients to orient — artificial light "
                   "causes fatal inland disorientation. "
                   "Kemp's Ridley juveniles are found in Delaware Bay and Cape May "
                   "waters seasonally but do not nest in New Jersey.",
    },
]

TURTLE_COLORS = {
    "Loggerhead":   "#FF8C00",
    "Leatherback":  "#CC44FF",
    "Kemp's Ridley":"#33FF99",
    "Green Turtle": "#44EE44",
}

# Atlantic Flyway corridor polygon — simplified coastal NJ trace
# Follows the primary shorebird / raptor funnel from Hudson south to Cape May,
# then back up the Delaware Bay shore.
ATLANTIC_FLYWAY_POLYGON = [
    # Enter from NY/CT airspace
    [41.36, -74.70], [41.20, -74.15], [40.98, -73.90],
    # Hudson / Bayonne / Newark area
    [40.85, -74.05], [40.65, -74.04], [40.50, -74.10],
    # Sandy Hook south, following barrier islands
    [40.47, -74.01], [40.15, -74.06], [39.95, -74.09],
    [39.78, -74.11], [39.55, -74.18], [39.35, -74.36],
    [39.10, -74.83], [38.93, -74.96],
    # Cape May tip — critical chokepoint where birds bottleneck
    [38.92, -75.10], [39.00, -75.18],
    # Back up Delaware Bay western shore
    [39.20, -75.32], [39.45, -75.38], [39.65, -75.32],
    [39.85, -75.20], [40.10, -75.00], [40.35, -74.92],
    [40.60, -74.72], [40.80, -74.60], [41.05, -74.55],
    [41.36, -74.70],
]

# Priority migratory species — colour-coded on map
PRIORITY_SPECIES = {
    "Red Knot":                  "#FF3333",
    "Semipalmated Sandpiper":    "#FF7700",
    "Dunlin":                    "#FFAA33",
    "Ruddy Turnstone":           "#CC6633",
    "American Oystercatcher":    "#FFEE00",
    "Black Skimmer":             "#FF5599",
    "Piping Plover":             "#88FF44",
    "Roseate Tern":              "#FFBBDD",
    "Peregrine Falcon":          "#9933FF",
    "Osprey":                    "#33AAFF",
    "Bald Eagle":                "#FFFFFF",
}

# ── Monthly presence windows — which months each species is in NJ ────────────
SPECIES_MONTHS = {
    "Red Knot":               [4, 5, 8, 9],
    "Semipalmated Sandpiper": [4, 5, 8, 9, 10],
    "Dunlin":                 [3, 4, 10, 11],
    "Ruddy Turnstone":        [5, 8, 9],
    "American Oystercatcher": [4, 5, 6, 7, 8, 9],
    "Black Skimmer":          [6, 7, 8, 9],
    "Piping Plover":          [4, 5, 6, 7, 8],
    "Roseate Tern":           [5, 6, 7, 8],
    "Peregrine Falcon":       [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
    "Osprey":                 [4, 5, 6, 7, 8, 9, 10],
    "Bald Eagle":             [1, 2, 3, 10, 11, 12],
}

TURTLE_MONTHS = {
    "Loggerhead":    [6, 7, 8, 9],
    "Leatherback":   [5, 6, 7],
    "Kemp's Ridley": [6, 7, 8],
    "Green Turtle":  [7, 8],
}

# ── Per-species light-pollution danger profile ────────────────────────────────
# LP exposure = weighted average mcd/m² across primary NJ range counties
# Sensitivity = 0–1 multiplier (nocturnal/beach nesters score highest)
# Conservation status: CR=4, EN=3, VU=2, NT=1, LC=0
SPECIES_DANGER = {
    # Birds
    "Roseate Tern":           {"lp_counties": ["Monmouth","Ocean"],         "sensitivity": 0.85, "status": 2, "status_label": "Federally Endangered (NE DPS)", "iucn": "LC", "reason": "IUCN Least Concern globally but the Northeast US population (Distinct Population Segment) is federally Endangered under the ESA. Has not nested in NJ since 1980; present as a migratory visitor along Monmouth and Ocean coasts. Artificial light at stopover sites disrupts nocturnal foraging and orientation."},
    "Piping Plover":          {"lp_counties": ["Monmouth","Ocean","Cape May"],"sensitivity": 0.88, "status": 2, "status_label": "Threatened",          "iucn": "NT", "reason": "Federally threatened beach nester. Artificial light disrupts nocturnal foraging and draws hatchlings away from the surf."},
    "Black Skimmer":          {"lp_counties": ["Atlantic","Cape May","Ocean"],"sensitivity": 0.80, "status": 2, "status_label": "Threatened (NJ)",     "iucn": "LC", "reason": "Nocturnal feeder; NJ colonies in steep decline. Bright skies reduce foraging efficiency and increase predation."},
    "Red Knot":               {"lp_counties": ["Cumberland","Salem","Cape May"],"sensitivity":0.75,"status": 2, "status_label": "Threatened",          "iucn": "NT", "reason": "Stopover fueling on Delaware Bay horseshoe crab eggs. Light-driven disturbance shortens critical pre-migration feeding window."},
    "Peregrine Falcon":       {"lp_counties": ["Hudson","Essex","Bergen"],   "sensitivity": 0.55, "status": 1, "status_label": "Species of Concern",   "iucn": "LC", "reason": "Urban cliff/bridge nester embedded in NJ's worst LP counties. Recovered post-DDT but now face chronic ALAN disruption to breeding cycles."},
    "Semipalmated Sandpiper": {"lp_counties": ["Cape May","Atlantic","Cumberland"],"sensitivity":0.70,"status":1,"status_label": "Near Threatened",    "iucn": "NT", "reason": "Population declined >80% since 1980s. Migratory stopover timing disrupted by artificial light altering invertebrate prey emergence."},
    "American Oystercatcher": {"lp_counties": ["Monmouth","Atlantic","Cape May"],"sensitivity":0.65,"status":1,"status_label": "Species of Concern",   "iucn": "LC", "reason": "Nests on open beaches; chick mortality increases when artificial light attracts gulls and corvids to nest sites at night."},
    # Sea turtles
    "Loggerhead":             {"lp_counties": ["Monmouth","Ocean","Atlantic","Cape May"],"sensitivity":0.95,"status":3,"status_label":"Threatened",    "iucn": "VU", "reason": "Primary NJ nesting species. Females abort nesting attempts on lit beaches; hatchlings crawl inland toward artificial light sources."},
    "Kemp's Ridley":          {"lp_counties": ["Monmouth","Cape May"],       "sensitivity": 0.82, "status": 4, "status_label": "Critically Endangered","iucn": "CR", "reason": "World's most endangered sea turtle (IUCN CR). Does not nest in NJ — nesting is almost entirely restricted to Tamaulipas, Mexico and Padre Island, TX. However, juveniles are regularly documented foraging in NJ coastal and estuarine waters (Barnegat Bay, Cape May area) during summer–fall. Beachfront and marina lighting in high-LP counties directly overlaps their juvenile foraging range."},
    "Leatherback":            {"lp_counties": ["Atlantic","Cape May"],       "sensitivity": 0.90, "status": 3, "status_label": "Vulnerable",           "iucn": "VU", "reason": "Deepest-diving turtle; uses lunar cues for coastal navigation. Skyglow at Cape May disrupts approach to nesting beaches."},
}

def compute_danger_scores():
    """
    Danger score = mean LP exposure (mcd/m²) × sensitivity × (1 + 0.25 × status)
    Returns list of (species, score, data) sorted descending.
    """
    results = []
    for sp, d in SPECIES_DANGER.items():
        counties = d["lp_counties"]
        mean_lp  = sum(NJ_LP_DATA.get(co, 5.0) for co in counties) / len(counties)
        score    = mean_lp * d["sensitivity"] * (1 + 0.25 * d["status"])
        results.append((sp, round(score, 1), mean_lp, d))
    results.sort(key=lambda x: -x[1])
    return results


# ─────────────────────────────────────────────────────────────────────────────
#  eBIRD API HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _ebird_get(path: str, api_key: str, params: dict) -> list:
    url = f"https://api.ebird.org/v2/{path}"
    try:
        r = requests.get(
            url,
            headers={"X-eBirdApiToken": api_key},
            params=params,
            timeout=6,
        )
        if r.status_code == 401:
            print("  ✗ eBird API key rejected (401). "
                  "Get a free key at https://ebird.org/api/keygen")
            return []
        r.raise_for_status()
        return r.json()
    except requests.RequestException as exc:
        print(f"  ✗ eBird request failed: {exc}")
        return []


def fetch_recent_obs(api_key: str, region: str, days: int) -> list:
    print(f"    → recent observations ({region}, last {days} days)…")
    data = _ebird_get(
        f"data/obs/{region}/recent",
        api_key,
        {"back": days, "maxResults": 10000,
         "includeProvisional": "true", "hotspot": "false"},
    )
    print(f"       {len(data)} records returned")
    return data


def fetch_notable_obs(api_key: str, region: str, days: int) -> list:
    print(f"    → notable/rare observations ({region}, last {days} days)…")
    data = _ebird_get(
        f"data/obs/{region}/recent/notable",
        api_key,
        {"back": days, "maxResults": 500, "detail": "full"},
    )
    print(f"       {len(data)} notable records returned")
    return data


def fetch_hotspots(api_key: str, lat: float, lon: float, dist_km: int = 35) -> list:
    return _ebird_get(
        "ref/hotspot/geo",
        api_key,
        {"lat": lat, "lng": lon, "dist": dist_km, "fmt": "json"},
    )

# ─────────────────────────────────────────────────────────────────────────────
#  MAP LAYERS
# ─────────────────────────────────────────────────────────────────────────────

def build_base_map() -> folium.Map:
    m = folium.Map(
        location=[39.85, -74.5],
        zoom_start=8,
        tiles=None,
        prefer_canvas=True,
    )
    # Dark base (best for light-pollution layer)
    folium.TileLayer(
        tiles="CartoDB dark_matter",
        name="🌑 Dark (default)",
        control=True,
        show=True,
    ).add_to(m)
    # Street / topo alternative
    folium.TileLayer(
        tiles="OpenStreetMap",
        name="🗺  Street (OpenStreetMap)",
        control=True,
        show=False,
    ).add_to(m)
    # Satellite
    folium.TileLayer(
        tiles=("https://server.arcgisonline.com/ArcGIS/rest/services/"
               "World_Imagery/MapServer/tile/{z}/{y}/{x}"),
        attr="Esri World Imagery",
        name="🛰  Satellite (Esri)",
        control=True,
        show=False,
    ).add_to(m)
    return m


# ── NJ county light pollution data ───────────────────────────────────────────
# Artificial sky brightness in mcd/m² above natural background
# Derived from Falchi et al. 2016 World Atlas + VIIRS DNB composite
# Scale: <0.5 = pristine  |  0.5–3 = rural  |  3–9 = suburban  |  9–27 = urban  |  >27 = severe
NJ_LP_DATA = {
    "Hudson":      87.4,   # Jersey City/Hoboken — worst in state
    "Essex":       74.1,   # Newark core
    "Union":       58.3,
    "Bergen":      52.7,
    "Passaic":     41.9,
    "Middlesex":   38.6,
    "Mercer":      31.2,   # Trenton metro
    "Morris":      18.4,
    "Somerset":    22.1,
    "Monmouth":    21.8,   # coastal suburban
    "Ocean":       12.4,   # barrier island / Pine Barrens edge
    "Burlington":   9.7,   # Pine Barrens — darkest inland
    "Camden":      34.5,
    "Gloucester":  16.8,
    "Salem":        7.3,
    "Cumberland":   5.1,   # most rural county
    "Atlantic":    11.6,   # AC metro mixed
    "Cape May":     8.9,   # critical nesting coast
    "Sussex":       6.4,   # rural NW
    "Warren":       7.8,
    "Hunterdon":    9.2,
}

# Simplified county polygons (lon,lat vertices) — accurate enough for fill
# Ordered N→S roughly
NJ_COUNTIES = {
    "Sussex":    [(-74.69,41.36),(-74.86,41.18),(-75.05,41.00),(-74.82,40.97),(-74.57,41.02),(-74.49,41.10),(-74.69,41.36)],
    "Passaic":   [(-74.14,41.18),(-74.49,41.10),(-74.57,41.02),(-74.27,40.98),(-74.13,41.05),(-74.14,41.18)],
    "Bergen":    [(-73.90,41.00),(-74.14,41.18),(-74.13,41.05),(-74.02,40.97),(-73.97,40.92),(-73.90,41.00)],
    "Warren":    [(-74.82,40.97),(-75.05,41.00),(-75.19,40.85),(-75.09,40.75),(-74.91,40.79),(-74.82,40.97)],
    "Morris":    [(-74.27,40.98),(-74.57,41.02),(-74.82,40.97),(-74.91,40.79),(-74.58,40.73),(-74.34,40.78),(-74.27,40.98)],
    "Essex":     [(-74.02,40.97),(-74.13,41.05),(-74.27,40.98),(-74.34,40.78),(-74.19,40.74),(-74.09,40.78),(-74.02,40.97)],
    "Hudson":    [(-74.02,40.75),(-74.09,40.78),(-74.19,40.74),(-74.12,40.70),(-74.02,40.68),(-74.02,40.75)],
    "Hunterdon": [(-74.91,40.79),(-75.09,40.75),(-75.19,40.57),(-75.03,40.47),(-74.78,40.50),(-74.62,40.60),(-74.58,40.73),(-74.91,40.79)],
    "Somerset":  [(-74.34,40.78),(-74.58,40.73),(-74.62,40.60),(-74.47,40.49),(-74.25,40.54),(-74.19,40.66),(-74.34,40.78)],
    "Union":     [(-74.09,40.78),(-74.19,40.74),(-74.19,40.66),(-74.09,40.59),(-74.02,40.63),(-74.02,40.78),(-74.09,40.78)],
    "Middlesex": [(-74.25,40.54),(-74.47,40.49),(-74.52,40.35),(-74.32,40.27),(-74.13,40.30),(-74.05,40.41),(-74.09,40.59),(-74.19,40.66),(-74.25,40.54)],
    "Mercer":    [(-74.78,40.50),(-75.03,40.47),(-75.13,40.27),(-74.91,40.14),(-74.71,40.21),(-74.52,40.35),(-74.47,40.49),(-74.62,40.60),(-74.78,40.50)],
    "Monmouth":  [(-74.05,40.41),(-74.13,40.30),(-74.32,40.27),(-74.52,40.35),(-74.40,40.14),(-74.16,40.08),(-74.01,40.15),(-74.02,40.34),(-74.05,40.41)],
    "Burlington": [(-74.71,40.21),(-74.91,40.14),(-75.13,40.27),(-75.41,39.98),(-75.38,39.82),(-75.02,39.76),(-74.72,39.72),(-74.42,39.83),(-74.40,40.14),(-74.52,40.35),(-74.71,40.21)],
    "Ocean":     [(-74.01,40.15),(-74.16,40.08),(-74.40,40.14),(-74.42,39.83),(-74.25,39.67),(-74.05,39.56),(-73.99,39.63),(-73.97,39.92),(-74.01,40.15)],
    "Camden":    [(-74.72,39.72),(-75.02,39.76),(-75.38,39.82),(-75.41,39.71),(-75.20,39.62),(-74.92,39.62),(-74.72,39.72)],
    "Gloucester":  [(-75.41,39.71),(-75.38,39.82),(-75.02,39.76),(-74.92,39.62),(-75.10,39.45),(-75.38,39.50),(-75.41,39.71)],
    "Salem":     [(-75.38,39.50),(-75.10,39.45),(-75.12,39.32),(-75.38,39.30),(-75.55,39.46),(-75.38,39.50)],
    "Atlantic":  [(-74.92,39.62),(-75.20,39.62),(-75.41,39.71),(-75.38,39.50),(-75.12,39.32),(-74.88,39.26),(-74.61,39.30),(-74.42,39.40),(-74.46,39.58),(-74.72,39.72),(-74.92,39.62)],
    "Cumberland":  [(-75.38,39.30),(-75.12,39.32),(-74.88,39.26),(-74.78,39.08),(-75.00,38.96),(-75.33,39.01),(-75.47,39.16),(-75.38,39.30)],
    "Cape May":  [(-74.78,39.08),(-74.88,39.26),(-74.61,39.30),(-74.42,39.40),(-74.25,39.25),(-74.18,38.99),(-74.55,38.93),(-74.91,38.93),(-74.78,39.08)],
}

def _lp_color(val):
    """Map radiance value to a warm glow colour."""
    import math
    # log scale  0→dark teal, 10→amber, 50→bright white-yellow
    t = min(1.0, math.log1p(val) / math.log1p(90))
    stops = [
        (0.00, (12,  30, 18)),   # near-black dark green
        (0.15, (30,  55, 25)),   # very dark
        (0.30, (80,  55,  5)),   # dark amber-brown
        (0.50, (160, 100, 10)),  # amber
        (0.70, (220, 160, 20)),  # bright amber
        (0.85, (240, 200, 60)),  # yellow
        (1.00, (255, 245,180)),  # near-white
    ]
    for i in range(len(stops)-1):
        t0, c0 = stops[i]
        t1, c1 = stops[i+1]
        if t0 <= t <= t1:
            f = (t - t0) / (t1 - t0)
            r = int(c0[0] + f*(c1[0]-c0[0]))
            g = int(c0[1] + f*(c1[1]-c0[1]))
            b = int(c0[2] + f*(c1[2]-c0[2]))
            return f"#{r:02x}{g:02x}{b:02x}"
    return "#ffffff"


def add_light_pollution(m: folium.Map) -> None:
    """
    Static choropleth of NJ light pollution by county.
    Data: Falchi et al. 2016 World Atlas + VIIRS DNB composite.
    Units: mcd/m² artificial sky brightness above natural background.
    No API, no tiles, no CORS — renders everywhere, every time.
    """
    fg = folium.FeatureGroup(
        name="💡 Light Pollution — Artificial Sky Brightness (mcd/m²)", show=True
    )

    for county, coords in NJ_COUNTIES.items():
        val   = NJ_LP_DATA.get(county, 10.0)
        color = _lp_color(val)
        # Bortle label
        if   val < 0.5:  bortle = "Class 1–2 · Pristine"
        elif val < 3:    bortle = "Class 3 · Rural"
        elif val < 9:    bortle = "Class 4–5 · Rural-suburban"
        elif val < 27:   bortle = "Class 6–7 · Suburban-urban"
        elif val < 54:   bortle = "Class 8 · Urban"
        else:            bortle = "Class 9 · Inner city"

        popup_html = (
            f"<div style='font-family:var(--mono);font-size:11px;min-width:160px'>"
            f"<b style='font-size:13px;font-family:var(--serif)'>{county} County</b><br>"
            f"<span style='color:var(--dim)'>Sky brightness:</span> "
            f"<b style='color:{color}'>{val} mcd/m²</b><br>"
            f"<span style='color:var(--dim)'>{bortle}</span>"
            f"</div>"
        )

        folium.Polygon(
            locations=[[lat, lon] for lon, lat in coords],
            color="rgba(0,0,0,0)",
            weight=0.5,
            fill=True,
            fill_color=color,
            fill_opacity=0.68,
            tooltip=f"{county}: {val} mcd/m²",
            popup=folium.Popup(popup_html, max_width=220),
        ).add_to(fg)

    fg.add_to(m)

    # ── Scale legend ──────────────────────────────────────────────────────────
    scale_html = """
    <div id="lp-scale" style="
        position:fixed; bottom:28px; left:14px; z-index:9000; width:215px;
        background:var(--panel); border:1px solid var(--border);
        border-radius:12px; padding:14px 15px 13px;
        box-shadow:0 6px 32px rgba(0,0,0,.65); color:var(--cream);
    ">
      <div style="font-family:var(--mono);font-size:8px;color:var(--dim);
                  text-transform:uppercase;letter-spacing:1.4px;margin-bottom:10px">
        Artificial Sky Brightness
      </div>
      <div style="display:flex;flex-direction:column;gap:5px;margin-bottom:10px">
        <div style="display:flex;align-items:center;gap:8px">
          <div style="width:28px;height:10px;border-radius:2px;flex-shrink:0;background:#0c1e12;border:1px solid rgba(200,200,180,.15)"></div>
          <span style="font-family:var(--mono);font-size:9px;color:var(--dim)">&lt;3 mcd/m²  ·  Rural dark</span>
        </div>
        <div style="display:flex;align-items:center;gap:8px">
          <div style="width:28px;height:10px;border-radius:2px;flex-shrink:0;background:#503205"></div>
          <span style="font-family:var(--mono);font-size:9px;color:var(--dim)">3–9   ·  Suburban fringe</span>
        </div>
        <div style="display:flex;align-items:center;gap:8px">
          <div style="width:28px;height:10px;border-radius:2px;flex-shrink:0;background:#a0640a"></div>
          <span style="font-family:var(--mono);font-size:9px;color:var(--dim)">9–27  ·  Suburban-urban</span>
        </div>
        <div style="display:flex;align-items:center;gap:8px">
          <div style="width:28px;height:10px;border-radius:2px;flex-shrink:0;background:#dca014"></div>
          <span style="font-family:var(--mono);font-size:9px;color:var(--dim)">27–54 ·  Urban bright</span>
        </div>
        <div style="display:flex;align-items:center;gap:8px">
          <div style="width:28px;height:10px;border-radius:2px;flex-shrink:0;background:#f5f5b4"></div>
          <span style="font-family:var(--mono);font-size:9px;color:var(--dim)">&gt;54   ·  City core severe</span>
        </div>
      </div>
      <div style="height:1px;background:rgba(130,170,110,.12);margin-bottom:8px"></div>
      <div style="font-family:var(--mono);font-size:8px;color:var(--dim);line-height:1.7">
        Falchi et al. 2016 · VIIRS DNB<br>
        Click any county for exact values
      </div>
    </div>"""
    m.get_root().html.add_child(folium.Element(scale_html))


def add_flyway(m: folium.Map) -> None:
    fg = folium.FeatureGroup(name="🦅 Atlantic Flyway Corridor", show=True)

    # Semi-transparent corridor polygon
    folium.Polygon(
        locations=ATLANTIC_FLYWAY_POLYGON,
        color="#00CCFF",
        weight=2.5,
        fill=True,
        fill_color="#00CCFF",
        fill_opacity=0.09,
        tooltip="Atlantic Flyway — NJ Coastal Corridor (click for detail)",
        popup=folium.Popup(
            """<div style='font-family:sans-serif;font-size:12px;max-width:280px'>
            <b style='font-size:13px'>🦅 Atlantic Flyway</b><br><br>
            One of four major North American bird migration corridors.
            NJ acts as a <b>critical bottleneck</b>: the Delaware Bay shore
            and Cape May peninsula concentrate millions of shorebirds, raptors,
            and songbirds each spring (Apr–May) and fall (Aug–Oct).<br><br>
            <b>Why light pollution matters here:</b> nocturnally migrating
            songbirds use stars for navigation; artificial sky glow causes
            fatal attraction to lit structures (FLAP Canada estimates
            >1 billion bird–window collisions per year in North America).<br><br>
            <i>Key species: Red Knot · Semipalmated Sandpiper ·
            Peregrine Falcon · Osprey · Bald Eagle · Black Skimmer ·
            Roseate Tern (NE DPS federally Endangered)</i>
            </div>""",
            max_width=310,
        ),
    ).add_to(fg)

    # Cape May chokepoint annotation
    folium.Marker(
        [38.96, -74.90],
        icon=folium.DivIcon(
            html=('<div style="font-size:11px;font-weight:700;color:#00CCFF;'
                  'white-space:nowrap;text-shadow:0 0 6px #000;line-height:1.3">'
                  '🦅 Cape May<br><span style="font-size:10px;font-weight:400">'
                  'Migration Chokepoint</span></div>'),
            icon_size=(160, 36),
            icon_anchor=(0, 18),
        ),
    ).add_to(fg)

    # Delaware Bay label
    folium.Marker(
        [39.30, -75.20],
        icon=folium.DivIcon(
            html=('<div style="font-size:10px;color:#00CCFF;opacity:.8;'
                  'white-space:nowrap;text-shadow:0 0 4px #000">'
                  'Delaware Bay Corridor</div>'),
            icon_size=(150, 20),
            icon_anchor=(75, 10),
        ),
    ).add_to(fg)

    fg.add_to(m)


def add_turtles(m: folium.Map) -> None:
    fg = folium.FeatureGroup(
        name="🐢 Sea Turtle Nesting Sites (NJ Coast)", show=True
    )
    for site in SEA_TURTLE_SITES:
        sp_list   = site["species"]
        primary_c = TURTLE_COLORS.get(sp_list[0], "#FF8800")
        sp_str    = " · ".join(sp_list)

        # Outer glow ring
        folium.CircleMarker(
            location=[site["lat"], site["lon"]],
            radius=18,
            color=primary_c,
            fill=True,
            fill_color=primary_c,
            fill_opacity=0.15,
            weight=1.5,
        ).add_to(fg)

        # Emoji marker with tooltip + popup
        folium.Marker(
            location=[site["lat"], site["lon"]],
            icon=folium.DivIcon(
                html=(f'<div style="font-size:22px;'
                      f'text-shadow:0 0 8px {primary_c},0 0 4px #000;'
                      f'cursor:pointer">🐢</div>'),
                icon_size=(30, 30),
                icon_anchor=(15, 15),
            ),
            tooltip=f"🐢 {site['name']}",
            popup=folium.Popup(
                f"""<div style='font-family:sans-serif;font-size:12px;
                    max-width:270px'>
                <b style='font-size:13px'>{site['name']}</b><br>
                <span style='color:#888'>Species:</span> {sp_str}<br><br>
                {site['notes']}<br><br>
                <i style='color:#FF8C00'>⚠ Artificial beachfront lighting
                disorients nesting females and causes hatchlings to crawl
                inland toward light instead of toward the ocean.</i>
                </div>""",
                max_width=290,
            ),
        ).add_to(fg)
    fg.add_to(m)


def add_ebird_layers(
    m: folium.Map,
    observations: list,
    notable: list,
) -> None:
    fg_priority = folium.FeatureGroup(
        name="🐦 Priority Migratory Species (eBird)", show=True
    )
    fg_notable = folium.FeatureGroup(
        name="⭐ Notable / Rare Sightings (eBird)", show=True
    )
    fg_all = folium.FeatureGroup(
        name="· All Recent Obs (eBird — dense)", show=False
    )

    seen = set()
    for obs in observations:
        if not (obs.get("lat") and obs.get("lng")):
            continue
        key = (obs["speciesCode"],
               round(obs["lat"], 3),
               round(obs["lng"], 3))
        if key in seen:
            continue
        seen.add(key)

        species = obs.get("comName", "Unknown")
        color   = PRIORITY_SPECIES.get(species)
        popup_html = (
            f"<div style='font-family:sans-serif;font-size:12px'>"
            f"<b>{species}</b><br>"
            f"<span style='color:#888'>{obs.get('locName','')}</span><br>"
            f"Count: {obs.get('howMany','?')} · {obs.get('obsDt','')}"
            f"</div>"
        )

        if color:
            folium.CircleMarker(
                location=[obs["lat"], obs["lng"]],
                radius=7,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.85,
                weight=1,
                tooltip=f"🐦 {species}",
                popup=folium.Popup(popup_html, max_width=230),
            ).add_to(fg_priority)
        else:
            folium.CircleMarker(
                location=[obs["lat"], obs["lng"]],
                radius=4,
                color="#88AAFF",
                fill=True,
                fill_color="#88AAFF",
                fill_opacity=0.55,
                weight=0.5,
                tooltip=species,
                popup=folium.Popup(popup_html, max_width=230),
            ).add_to(fg_all)

    for obs in notable:
        if not (obs.get("lat") and obs.get("lng")):
            continue
        folium.Marker(
            location=[obs["lat"], obs["lng"]],
            icon=folium.Icon(color="orange", icon="star", prefix="fa"),
            tooltip=f"⭐ RARE: {obs.get('comName','')}",
            popup=folium.Popup(
                f"""<div style='font-family:sans-serif;font-size:12px;
                    max-width:260px'>
                <b>⭐ Notable Sighting</b><br>
                <b>{obs.get('comName','')}</b>
                <i>({obs.get('sciName','')})</i><br>
                {obs.get('locName','')}<br>
                Count: {obs.get('howMany','?')} · {obs.get('obsDt','')}
                </div>""",
                max_width=270,
            ),
        ).add_to(fg_notable)

    fg_priority.add_to(m)
    fg_notable.add_to(m)
    fg_all.add_to(m)


# Approximate centre-point coordinates for each at-risk species' NJ range
SPECIES_COORDS = {
    "Roseate Tern":           [(40.47, -74.01), (39.37, -74.43)],  # migratory stopover sites
    "Piping Plover":          [(40.47, -74.01), (39.83, -74.09), (38.93, -74.96)],
    "Black Skimmer":          [(39.42, -74.35), (38.93, -74.96)],
    "Red Knot":               [(39.20, -75.15), (38.95, -75.05)],
    "Peregrine Falcon":       [(40.72, -74.03), (40.73, -74.17)],
    "Semipalmated Sandpiper": [(38.95, -75.10), (39.42, -74.35)],
    "American Oystercatcher": [(40.47, -74.01), (39.42, -74.35), (38.93, -74.96)],
    "Loggerhead":             [(40.48, -74.01), (39.83, -74.09), (39.42, -74.35), (38.93, -74.96)],
    "Kemp's Ridley":          [(40.48, -74.01), (38.93, -74.96)],
    "Leatherback":            [(39.42, -74.35), (38.93, -74.96)],
}

def add_danger_layer(m: folium.Map) -> None:
    """Red X markers for the top 3 most LP-endangered species."""
    ranked = compute_danger_scores()
    top3   = ranked[:3]

    fg = folium.FeatureGroup(name="🚨 Most in Danger (Top 3 by LP Exposure)", show=True)

    rank_labels = ["#1", "#2", "#3"]
    for i, (sp, score, mean_lp, d) in enumerate(top3):
        coords = SPECIES_COORDS.get(sp, [])
        label  = rank_labels[i]
        iucn   = d["iucn"]
        status = d["status_label"]
        reason = d["reason"]

        for lat, lon in coords:
            # Outer danger pulse ring
            folium.CircleMarker(
                location=[lat, lon], radius=22,
                color="#ff2222", fill=True, fill_color="#ff2222",
                fill_opacity=0.08, weight=1.5, opacity=0.5,
            ).add_to(fg)

            # Red X marker
            folium.Marker(
                location=[lat, lon],
                icon=folium.DivIcon(
                    html=(
                        f'<div style="'
                        f'font-size:18px;font-weight:900;color:#ff2222;'
                        f'text-shadow:0 0 6px #000,0 0 12px #ff000088;'
                        f'line-height:1;cursor:pointer;'
                        f'font-family:monospace">✕</div>'
                    ),
                    icon_size=(20, 20),
                    icon_anchor=(10, 10),
                ),
                tooltip=f"🚨 {label} Most at Risk: {sp}",
                popup=folium.Popup(
                    f"""<div style='font-family:var(--mono);font-size:11px;max-width:260px;line-height:1.6'>
                    <div style='font-family:var(--serif);font-size:15px;color:#ff6666;margin-bottom:4px'>
                      {label} — {sp}
                    </div>
                    <div style='color:rgba(200,180,160,.6);margin-bottom:6px'>
                      IUCN: <b style='color:#ff8888'>{iucn}</b> &nbsp;·&nbsp; {status}
                    </div>
                    <div style='color:rgba(200,180,160,.6);margin-bottom:4px'>
                      Danger score: <b style='color:#ff8888'>{score}</b>
                      &nbsp;·&nbsp; Avg LP: <b style='color:#ffaa44'>{mean_lp:.1f} mcd/m²</b>
                    </div>
                    <div style='height:1px;background:rgba(255,80,80,.2);margin:8px 0'></div>
                    <div style='color:rgba(210,195,175,.75)'>{reason}</div>
                    </div>""",
                    max_width=280,
                ),
            ).add_to(fg)

    fg.add_to(m)
    return top3   # return so we can use in the panel


def add_threat_heatmap(m: folium.Map) -> None:
    """
    Build-time computed threat overlap grid.
    Score = county LP × flyway multiplier × turtle proximity multiplier.
    Cells only shown where all three pressures meaningfully intersect.
    """
    import math

    def pip(lat, lon, poly_latlon):
        """Point-in-polygon (ray casting). poly = [[lat,lon],...]"""
        n, inside, j = len(poly_latlon), False, len(poly_latlon) - 1
        for i in range(n):
            yi, xi = poly_latlon[i]; yj, xj = poly_latlon[j]
            if ((yi > lat) != (yj > lat)) and \
               (lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-12) + xi):
                inside = not inside
            j = i
        return inside

    def get_lp(lat, lon):
        for county, coords in NJ_COUNTIES.items():
            if pip(lat, lon, [[la, lo] for lo, la in coords]):
                return NJ_LP_DATA.get(county, 0.0)
        return 0.0

    def turtle_proximity(lat, lon):
        return min(math.hypot(lat - s["lat"], lon - s["lon"]) for s in SEA_TURTLE_SITES)

    fg = folium.FeatureGroup(name="🔥 Threat Overlap Heatmap", show=False)
    STEP, cells = 0.11, 0

    lat = 38.80
    while lat < 41.50:
        lon = -75.65
        while lon < -73.85:
            clat, clon = lat + STEP / 2, lon + STEP / 2
            lp = get_lp(clat, clon)
            if lp < 1.0:
                lon += STEP; continue

            in_flyway   = pip(clat, clon, ATLANTIC_FLYWAY_POLYGON)
            tdist       = turtle_proximity(clat, clon)
            fly_mult    = 1.9 if in_flyway else 0.35
            turtle_mult = 1.0 + max(0.0, (0.40 - tdist) / 0.40) * 0.80
            score       = lp * fly_mult * turtle_mult
            norm        = min(1.0, score / 160.0)

            if norm < 0.12:
                lon += STEP; continue

            # Colour ramp: dark teal → amber → red-orange
            if norm < 0.40:
                t = norm / 0.40
                r, g, b = int(20+t*180), int(100+t*80), int(80-t*70)
            elif norm < 0.75:
                t = (norm - 0.40) / 0.35
                r, g, b = int(200+t*40), int(180-t*100), 10
            else:
                t = (norm - 0.75) / 0.25
                r, g, b = min(255, 240+int(t*15)), int(80-t*60), 10

            bortle = "Suburban" if lp < 27 else ("Urban" if lp < 54 else "Severe")
            tip = (f"⚠ Threat score: {score:.0f}  |  LP: {lp:.1f} mcd/m² ({bortle})  |  "
                   f"Flyway: {'✓' if in_flyway else '✗'}  |  "
                   f"Turtle zone: {'✓' if tdist < 0.30 else '✗'}")

            folium.Rectangle(
                bounds=[[lat, lon], [lat + STEP, lon + STEP]],
                color="none", fill=True,
                fill_color=f"#{r:02x}{g:02x}{b:02x}",
                fill_opacity=0.44, tooltip=tip,
            ).add_to(fg)
            cells += 1
            lon += STEP
        lat += STEP

    fg.add_to(m)
    print(f"       {cells} threat-overlap cells rendered")


def add_seasonal_control(m: folium.Map) -> None:
    """
    Month slider bar — bottom-centre of map.
    Dims turtle markers out of nesting season, lists active migrants.
    """
    import json as _j
    cur_mo   = datetime.now().month
    cur_name = datetime.now().strftime("%b")
    sp_j     = _j.dumps(SPECIES_MONTHS)
    tu_j     = _j.dumps(TURTLE_MONTHS)
    sp_col_j = _j.dumps({s: c for s, c in PRIORITY_SPECIES.items()})

    html = f"""
    <script>
    var _SP_MO  = {sp_j};
    var _TU_MO  = {tu_j};
    var _SP_COL = {sp_col_j};
    var _MNAMES = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    var _PEAK   = [4,5,8,9,10];

    function updateSeason(mo) {{
      document.getElementById('mo-lbl').textContent = _MNAMES[mo-1];

      // Dim/restore turtle markers
      document.querySelectorAll('[data-turtle-sp]').forEach(function(el) {{
        var sp     = el.getAttribute('data-turtle-sp');
        var active = _TU_MO[sp] && _TU_MO[sp].indexOf(mo) !== -1;
        el.style.opacity = active ? '1' : '0.2';
        el.style.filter  = active ? '' : 'grayscale(90%)';
      }});

      // Active bird species list
      var active = Object.keys(_SP_MO).filter(function(s) {{
        return _SP_MO[s].indexOf(mo) !== -1;
      }});
      var list = document.getElementById('sea-sp');
      if (list) {{
        list.innerHTML = active.length === 0
          ? '<span style="color:var(--dim)">No priority species present</span>'
          : active.map(function(s) {{
              var col = _SP_COL[s] || '#aaa';
              return '<div style="display:flex;align-items:center;gap:5px;padding:1px 0">'
                + '<div style="width:6px;height:6px;border-radius:50%;flex-shrink:0;background:' + col + ';box-shadow:0 0 4px ' + col + '88"></div>'
                + '<span>' + s + '</span></div>';
            }}).join('');
      }}

      // Active nesting turtles
      var actT = Object.keys(_TU_MO).filter(function(s) {{
        return _TU_MO[s].indexOf(mo) !== -1;
      }});
      var tel = document.getElementById('sea-tu');
      if (tel) tel.textContent = actT.length > 0 ? actT.join(', ') : 'No nesting activity';

      // Peak banner
      var ban = document.getElementById('sea-peak');
      if (ban) ban.style.display = _PEAK.indexOf(mo) !== -1 ? 'block' : 'none';
    }}

    document.addEventListener('DOMContentLoaded', function() {{
      setTimeout(function() {{ updateSeason({cur_mo}); }}, 700);
    }});
    </script>

    <div id="month-bar" style="
      position:fixed; bottom:22px; left:50%; transform:translateX(-50%);
      z-index:9500; background:var(--panel); border:1px solid var(--border);
      border-radius:13px; padding:11px 18px 10px;
      box-shadow:0 4px 24px rgba(0,0,0,.6);
      display:flex; align-items:flex-start; gap:14px;
    ">
      <div style="display:flex;align-items:center;gap:10px;flex-shrink:0">
        <span style="font-size:15px">🗓</span>
        <div>
          <div style="font-family:var(--mono);font-size:8px;color:var(--dim);
                      text-transform:uppercase;letter-spacing:1px;margin-bottom:5px">
            Migration month
          </div>
          <div style="display:flex;align-items:center;gap:10px">
            <input type="range" min="1" max="12" value="{cur_mo}"
                   oninput="updateSeason(parseInt(this.value))"
                   style="width:170px;accent-color:var(--sage);cursor:pointer">
            <span id="mo-lbl" style="font-family:var(--mono);font-size:12px;
                                      color:var(--cream);font-weight:500;min-width:26px">
              {cur_name}
            </span>
          </div>
        </div>
      </div>

      <div style="border-left:1px solid var(--border);padding-left:14px;
                  font-family:var(--mono);font-size:9.5px;color:var(--warm);
                  min-width:190px;max-width:220px">
        <div id="sea-peak" style="font-family:var(--mono);font-size:8px;color:var(--sage);
                                    text-transform:uppercase;letter-spacing:1px;
                                    margin-bottom:5px;display:none">
          ⚡ Peak migration window
        </div>
        <div id="sea-sp" style="line-height:1.7;margin-bottom:6px">Loading…</div>
        <div style="font-size:8.5px;color:var(--amber)">
          🐢 Nesting: <span id="sea-tu">…</span>
        </div>
      </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(html))


def add_whatif_simulator(m: folium.Map) -> None:
    """
    Injects the What-If LP reduction simulator panel.
    County sliders → live danger score recalculation in JS.
    The panel button is appended to the strip via JS.
    """
    import json as _j

    SLIDER_COUNTIES = {
        "Hudson":     87.4,
        "Bergen":     52.7,
        "Monmouth":   21.8,
        "Ocean":      12.4,
        "Atlantic":   11.6,
        "Cape May":    8.9,
        "Cumberland":  5.1,
    }

    sp_data = {
        sp: {
            "lp_counties": d["lp_counties"],
            "sensitivity":  d["sensitivity"],
            "status":       d["status"],
            "status_label": d["status_label"],
            "iucn":         d["iucn"],
        }
        for sp, d in SPECIES_DANGER.items()
    }

    sp_j  = _j.dumps(sp_data)
    lp_j  = _j.dumps(dict(NJ_LP_DATA))

    slider_rows = ""
    for county, base_val in SLIDER_COUNTIES.items():
        cid = county.lower()
        slider_rows += (
            f'<div style="margin-bottom:11px">'
            f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:3px">'
            f'<span style="font-family:var(--mono);font-size:9.5px;color:var(--warm)">{county}</span>'
            f'<span id="wi-{cid}" style="font-family:var(--mono);font-size:8.5px;color:var(--amber)">'
            f'{base_val} mcd/m²</span></div>'
            f'<input type="range" min="0" max="80" value="0"'
            f' class="wi-sl" data-county="{county}" data-cid="{cid}" data-base="{base_val}"'
            f' oninput="runWI()"'
            f' style="width:100%;accent-color:var(--sage);cursor:pointer">'
            f'</div>'
        )

    html = f"""
    <div id="panel-whatif" class="eco-panel" style="width:295px">
      <h2>What <em>If?</em></h2>
      <div class="rule"></div>
      <p style="margin-bottom:13px">Drag a county slider to simulate reducing its light
      pollution. The danger scores recalculate live — see which interventions help the most species.</p>
      <div class="section-label">Drag to reduce LP (%)</div>
      {slider_rows}
      <div class="divider"></div>
      <div class="section-label">Species impact</div>
      <div id="wi-results" style="font-family:var(--mono);font-size:9px;min-height:40px">
        <span style="color:var(--dim)">Adjust a slider above to see results</span>
      </div>
      <div class="divider"></div>
      <div id="wi-summary" style="font-family:var(--mono);font-size:9px;
                                   color:var(--sage);min-height:14px"></div>
      <div style="margin-top:10px">
        <span onclick="resetWI()" style="font-family:var(--mono);font-size:8.5px;
               color:var(--dim);cursor:pointer;text-decoration:underline">Reset all</span>
      </div>
    </div>

    <script>
    var _BASE = {lp_j};
    var _NOW  = Object.assign({{}}, _BASE);
    var _SPS  = {sp_j};
    var _IUCN_C = {{'CR':'#ff4444','EN':'#ff7744','VU':'#ffaa33','NT':'#ddcc55','LC':'#88bb66'}};

    function _score(sp, lp) {{
      var d = _SPS[sp]; if (!d) return 0;
      var mean = d.lp_counties.reduce(function(s,co){{return s+(_NOW[co]||5);}},0)/d.lp_counties.length;
      return mean * d.sensitivity * (1 + 0.25 * d.status);
    }}
    function _scoreBase(sp) {{
      var d = _SPS[sp]; if (!d) return 0;
      var mean = d.lp_counties.reduce(function(s,co){{return s+(_BASE[co]||5);}},0)/d.lp_counties.length;
      return mean * d.sensitivity * (1 + 0.25 * d.status);
    }}

    function runWI() {{
      document.querySelectorAll('.wi-sl').forEach(function(sl) {{
        var county = sl.getAttribute('data-county');
        var cid    = sl.getAttribute('data-cid');
        var base   = parseFloat(sl.getAttribute('data-base'));
        var pct    = parseInt(sl.value);
        _NOW[county] = base * (1 - pct/100);
        var el = document.getElementById('wi-' + cid);
        if (el) el.textContent = Math.round(_NOW[county]) + ' mcd/m²'
          + (pct > 0 ? '  −' + pct + '%' : '');
      }});

      var results = Object.keys(_SPS).map(function(sp) {{
        var base = _scoreBase(sp), now = _score(sp);
        return {{sp:sp, base:base, now:now, delta:base-now, iucn:_SPS[sp].iucn}};
      }}).sort(function(a,b){{return b.now-a.now;}});

      var el = document.getElementById('wi-results');
      if (el) el.innerHTML = results.map(function(r) {{
        var pct  = r.base > 0 ? Math.round((r.delta/r.base)*100) : 0;
        var col  = r.delta > 1 ? '#7aa07e' : r.delta < -1 ? '#ff6666' : 'rgba(150,170,135,.45)';
        var arr  = r.delta > 1 ? '↓' : r.delta < -1 ? '↑' : '·';
        var iCol = _IUCN_C[r.iucn] || '#aaa';
        return '<div style="display:flex;align-items:center;gap:5px;padding:3px 0;'
          + 'border-bottom:1px solid rgba(130,170,110,.07)">'
          + '<span style="font-size:7.5px;color:' + iCol + ';background:rgba(255,255,255,.06);'
          + 'border-radius:2px;padding:0 3px;flex-shrink:0;font-family:var(--mono)">' + r.iucn + '</span>'
          + '<span style="flex:1;font-size:9px;color:var(--warm);font-family:var(--mono)">' + r.sp + '</span>'
          + '<span style="color:' + col + ';font-size:9.5px;font-family:var(--mono);'
          + 'min-width:70px;text-align:right">' + arr + ' '
          + (pct !== 0 ? Math.abs(pct) + '% safer' : 'no change') + '</span></div>';
      }}).join('');

      var improved = results.filter(function(r){{return r.delta > 0.5;}}).length;
      var sumEl = document.getElementById('wi-summary');
      if (sumEl) {{
        sumEl.textContent = improved > 0
          ? improved + ' of ' + results.length + ' species become safer'
          : 'Drag sliders to simulate reductions';
        sumEl.style.color = improved > 0 ? 'var(--sage)' : 'var(--dim)';
      }}
    }}

    function resetWI() {{
      document.querySelectorAll('.wi-sl').forEach(function(sl) {{
        sl.value = '0';
        var county = sl.getAttribute('data-county');
        var cid    = sl.getAttribute('data-cid');
        var base   = parseFloat(sl.getAttribute('data-base'));
        _NOW[county] = base;
        var el = document.getElementById('wi-' + cid);
        if (el) el.textContent = base + ' mcd/m²';
      }});
      var el = document.getElementById('wi-results');
      if (el) el.innerHTML = '<span style="color:var(--dim)">Adjust a slider above to see results</span>';
      var sumEl = document.getElementById('wi-summary');
      if (sumEl) sumEl.textContent = '';
    }}

    // Append 🎛 button to strip after DOM loads
    document.addEventListener('DOMContentLoaded', function() {{
      setTimeout(function() {{
        var strip = document.getElementById('eco-strip');
        if (!strip) return;
        var btn = document.createElement('div');
        btn.className = 'eco-btn';
        btn.id = 'btn-whatif';
        btn.setAttribute('data-tip', 'What-if simulator');
        btn.innerHTML = '🎛';
        btn.onclick = function() {{ ecoToggle('whatif'); }};
        strip.appendChild(btn);
      }}, 300);
    }});
    </script>
    """
    m.get_root().html.add_child(folium.Element(html))


def add_hotspots(m: folium.Map, api_key: str) -> None:
    fg = folium.FeatureGroup(name="📍 eBird Hotspots", show=False)

    coastal_anchors = [
        (40.47, -74.01),   # Sandy Hook
        (39.83, -74.09),   # Island Beach SP
        (39.37, -74.43),   # Brigantine / ENWR
        (39.10, -74.83),   # Cape May area
    ]

    seen_ids: set = set()
    for lat, lon in coastal_anchors:
        for spot in fetch_hotspots(api_key, lat, lon, dist_km=30):
            lid = spot.get("locId")
            if lid in seen_ids:
                continue
            seen_ids.add(lid)
            folium.CircleMarker(
                location=[spot["lat"], spot["lng"]],
                radius=5,
                color="#FFD700",
                fill=True,
                fill_color="#FFD700",
                fill_opacity=0.6,
                weight=1,
                tooltip=f"📍 {spot.get('locName','')}",
                popup=folium.Popup(
                    f"""<div style='font-family:sans-serif;font-size:12px'>
                    <b>eBird Hotspot</b><br>{spot.get('locName','')}<br>
                    <a href='https://ebird.org/hotspot/{lid}'
                       target='_blank'>View on eBird ↗</a>
                    </div>""",
                    max_width=220,
                ),
            ).add_to(fg)

    print(f"       {len(seen_ids)} unique hotspots plotted")
    fg.add_to(m)


# ─────────────────────────────────────────────────────────────────────────────
#  UI CHROME  — Naturalist's Field Station
# ─────────────────────────────────────────────────────────────────────────────

def add_title(m):
    ts = datetime.now().strftime("%b %d, %Y")

    font_css = """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400;1,600&family=JetBrains+Mono:wght@300;400;500&display=swap" rel="stylesheet">
    <style>
      :root {
        --panel:    rgba(10, 18, 12, 0.96);
        --border:   rgba(130, 170, 110, 0.20);
        --border-h: rgba(170, 210, 140, 0.45);
        --cream:    #dcd7c2;
        --sage:     #7aa07e;
        --amber:    #c8923a;
        --rust:     #b84c2a;
        --warm:     rgba(215, 205, 180, 0.70);
        --dim:      rgba(150, 170, 135, 0.45);
        --serif:    'Cormorant Garamond', Georgia, serif;
        --mono:     'JetBrains Mono', 'Courier New', monospace;
      }
      @keyframes panelIn {
        from { opacity:0; transform:translateY(-50%) translateX(-10px); }
        to   { opacity:1; transform:translateY(-50%) translateX(0); }
      }
      @keyframes fadeIn {
        from { opacity:0; } to { opacity:1; }
      }
      #eco-wordmark { animation: fadeIn .9s ease both; }
      #eco-strip    { animation: fadeIn 1s .4s ease both; }

      /* vertical button strip */
      #eco-strip {
        position: fixed;
        top: 50%;
        left: 16px;
        transform: translateY(-50%);
        z-index: 9999;
        display: flex;
        flex-direction: column;
        gap: 7px;
      }
      .eco-btn {
        width: 38px; height: 38px;
        border-radius: 8px;
        background: var(--panel);
        border: 1px solid var(--border);
        display: flex; align-items: center; justify-content: center;
        cursor: pointer; font-size: 16px;
        box-shadow: 0 2px 14px rgba(0,0,0,.55);
        transition: background .16s, border-color .16s, transform .14s;
        color: var(--cream); user-select: none;
        position: relative;
      }
      .eco-btn:hover {
        background: rgba(110,150,90,.2);
        border-color: var(--border-h);
        transform: translateX(3px);
      }
      .eco-btn.active {
        background: rgba(110,150,90,.22);
        border-color: var(--border-h);
        transform: translateX(3px);
      }
      .eco-btn::after {
        content: attr(data-tip);
        position: absolute; left: 46px; top: 50%; transform: translateY(-50%);
        white-space: nowrap;
        background: var(--panel); border: 1px solid var(--border);
        border-radius: 5px; padding: 4px 10px;
        font-family: var(--mono); font-size: 10px; color: var(--cream);
        opacity: 0; pointer-events: none; transition: opacity .15s;
        letter-spacing: .3px; box-shadow: 0 2px 10px rgba(0,0,0,.4);
      }
      .eco-btn:hover::after { opacity: 1; }

      /* slide-in panels */
      .eco-panel {
        position: fixed; top: 50%; left: 62px;
        transform: translateY(-50%) translateX(-10px);
        width: 278px; max-height: 80vh; z-index: 9998;
        background: var(--panel); border: 1px solid var(--border);
        border-radius: 12px; overflow-y: auto;
        box-shadow: 0 14px 55px rgba(0,0,0,.72);
        padding: 22px 20px 22px; color: var(--cream);
        opacity: 0; pointer-events: none;
        transition: opacity .2s ease, transform .2s ease;
      }
      .eco-panel.visible {
        opacity: 1; pointer-events: auto;
        transform: translateY(-50%) translateX(0);
        animation: panelIn .2s ease both;
      }
      .eco-panel::-webkit-scrollbar { width: 3px; }
      .eco-panel::-webkit-scrollbar-thumb { background: rgba(130,170,110,.3); border-radius:2px; }

      /* panel typography */
      .eco-panel h2 {
        font-family: var(--serif); font-size: 24px; font-weight: 600;
        color: var(--cream); margin: 0 0 4px; letter-spacing: -.2px; line-height: 1.2;
      }
      .eco-panel h2 em { color: var(--sage); font-style: italic; }
      .eco-panel .rule {
        width: 24px; height: 1px; background: var(--sage);
        margin: 0 0 15px; opacity: .55;
      }
      .eco-panel p {
        font-family: var(--mono); font-size: 10.5px; line-height: 1.78;
        color: var(--warm); margin: 0 0 14px;
      }
      .eco-panel .section-label {
        font-family: var(--mono); font-size: 8px; color: var(--dim);
        text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 9px;
      }
      .eco-panel .divider {
        height: 1px; background: rgba(130,170,110,.12); margin: 14px 0;
      }

      /* threat cards */
      .t-card {
        border-left: 2px solid var(--sage);
        padding: 8px 10px 8px 11px;
        margin-bottom: 10px;
        background: rgba(110,150,90,.05);
        border-radius: 0 6px 6px 0;
      }
      .t-card.am { border-left-color: var(--amber); background: rgba(200,145,58,.05); }
      .t-card.rs { border-left-color: var(--rust);  background: rgba(185,76,42,.05); }
      .t-card .cl {
        font-family: var(--mono); font-size: 8.5px;
        text-transform: uppercase; letter-spacing: 1.1px;
        color: var(--sage); margin-bottom: 4px;
      }
      .t-card.am .cl { color: var(--amber); }
      .t-card.rs .cl { color: var(--rust); }
      .t-card .cb {
        font-family: var(--mono); font-size: 10px;
        color: rgba(205,197,172,.7); line-height: 1.65;
      }

      /* species rows */
      .sp-row {
        display: flex; align-items: center; gap: 8px;
        padding: 3px 5px; border-radius: 4px;
        font-family: var(--mono); font-size: 10px; color: var(--warm);
        transition: background .12s; cursor: default;
      }
      .sp-row:hover { background: rgba(110,150,90,.08); }
      .sp-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }

      /* Leaflet reskin */
      .leaflet-control-layers {
        background: rgba(10,18,12,.96) !important;
        border: 1px solid rgba(130,170,110,.2) !important;
        border-radius: 10px !important;
        box-shadow: 0 4px 22px rgba(0,0,0,.6) !important;
        font-family: var(--mono) !important;
        font-size: 10.5px !important; color: var(--cream) !important;
      }
      .leaflet-control-layers-expanded { padding: 10px 13px !important; }
      .leaflet-control-layers-base label,
      .leaflet-control-layers-overlays label {
        font-family: var(--mono) !important; font-size: 10.5px !important;
        color: rgba(190,185,165,.65) !important; padding: 2px 0; transition: color .14s;
      }
      .leaflet-control-layers-base label:hover,
      .leaflet-control-layers-overlays label:hover { color: var(--cream) !important; }
      .leaflet-control-layers-separator {
        border-top: 1px solid rgba(130,170,110,.12) !important; margin: 5px 0 !important;
      }

      /* Popups */
      .leaflet-popup-content-wrapper {
        background: rgba(8,15,10,.97) !important;
        border: 1px solid rgba(130,170,110,.28) !important;
        border-radius: 9px !important;
        box-shadow: 0 8px 40px rgba(0,0,0,.75) !important;
        color: var(--cream) !important;
        font-family: var(--mono) !important;
        font-size: 11px !important; line-height: 1.65 !important;
      }
      .leaflet-popup-tip { background: rgba(8,15,10,.97) !important; }
      .leaflet-popup-close-button {
        color: var(--sage) !important; font-size: 20px !important;
        top: 6px !important; right: 9px !important;
      }
      .leaflet-popup-close-button:hover { color: var(--cream) !important; }
    </style>
    """
    m.get_root().header.add_child(folium.Element(font_css))

    wordmark_html = f"""
    <div id="eco-wordmark" style="
        position:fixed; top:16px; left:16px; z-index:9999; pointer-events:none;
    ">
      <div style="font-family:var(--serif);font-size:13px;font-weight:600;
                  color:rgba(195,190,168,.82);letter-spacing:.2px;line-height:1;
                  white-space:nowrap">NJ Ecological Convergence</div>
      <div style="font-family:var(--mono);font-size:8px;
                  color:rgba(130,155,110,.45);letter-spacing:.9px;
                  text-transform:uppercase;margin-top:4px">{ts} &nbsp;·&nbsp; Falchi et al. 2016 · eBird / Cornell Lab · NOAA</div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(wordmark_html))


def add_legend(m, top3=None):
    species_rows = "".join(
        f'<div class="sp-row"><div class="sp-dot" style="background:{c}"></div><span>{s}</span></div>'
        for s, c in PRIORITY_SPECIES.items()
    )
    turtle_rows = "".join(
        f'<div class="sp-row"><div class="sp-dot" style="background:{c}"></div><span>{sp}</span></div>'
        for sp, c in TURTLE_COLORS.items()
    )

    import json as _json
    danger_json = "null"
    if top3:
        cards = []
        for sp, score, mean_lp, d in top3:
            cards.append({
                "species":      sp,
                "score":        score,
                "mean_lp":      round(mean_lp, 1),
                "iucn":         d["iucn"],
                "status_label": d["status_label"],
                "reason":       d["reason"],
            })
        danger_json = _json.dumps(cards)
    ui_html = f"""
    <div id="eco-strip">
      <div class="eco-btn" id="btn-about"   data-tip="About &amp; context"   onclick="ecoToggle('about')">🌿</div>
      <div class="eco-btn" id="btn-sources" data-tip="Data sources"            onclick="ecoToggle('sources')">📚</div>
      <div class="eco-btn" id="btn-danger"  data-tip="Most in danger"         onclick="ecoToggle('danger')">🚨</div>
      <div class="eco-btn" id="btn-legend"  data-tip="Species legend"         onclick="ecoToggle('legend')">🦅</div>
      <div class="eco-btn" id="btn-lp"      data-tip="Light pollution scale"  onclick="ecoToggle('lp')">💡</div>
    </div>

    <div id="panel-sources" class="eco-panel">
      <h2>Data <em>Sources</em></h2>
      <div class="rule"></div>

      <div class="t-card" style="margin-bottom:10px">
        <div class="cl">📊 Falchi et al. (2016)</div>
        <div class="cb">
          <i>Science Advances</i> 2(6):e1600377<br>
          DOI: 10.1126/sciadv.1600377<br>
          DOI: 10.5880/GFZ.1.4.2016.001<br><br>
          NJ county LP values (mcd/m²). Drives county choropleth
          colours, danger scores, threat heatmap, and what-if slider baselines.
        </div>
      </div>

      <div class="t-card" style="margin-bottom:10px">
        <div class="cl">🦅 Cornell Lab of Ornithology — eBird API v2</div>
        <div class="cb">
          eBird. 2024. An online database of bird distribution
          and abundance. Cornell Lab, Ithaca NY. ebird.org<br><br>
          Live bird sightings, notable rarities, hotspot locations.
          Drives priority species dots, star markers, hotspot circles,
          and the seasonal migration calendar.
        </div>
      </div>

      <div class="t-card" style="margin-bottom:10px">
        <div class="cl">🐠 NOAA Fisheries</div>
        <div class="cb">
          fisheries.noaa.gov · NOAA NCCOS coastal surveys<br><br>
          ESA threat status for all species. Confirmed turtle
          nesting site geography along the NJ coast.
        </div>
      </div>

      <div class="t-card" style="margin-bottom:10px">
        <div class="cl">🌿 NJ Dept. of Environmental Protection</div>
        <div class="cb">
          dep.nj.gov/njfw · Endangered &amp; Nongame Species Program<br><br>
          Verified Roseate Tern last nested in NJ in 1980.
          Source for beach lighting ordinances cited in site notes.
        </div>
      </div>

      <div class="t-card" style="margin-bottom:10px">
        <div class="cl">🐢 Marine Mammal Stranding Center (MMSC)</div>
        <div class="cb">
          mmsc.org · NJ field surveys<br><br>
          Long Beach Island site monitoring. Kemp's Ridley
          juvenile foraging presence in Barnegat Bay.
        </div>
      </div>

      <div class="t-card" style="margin-bottom:10px">
        <div class="cl">🔴 IUCN Red List</div>
        <div class="cb">
          iucnredlist.org<br><br>
          CR / EN / VU / NT / LC codes for every species.
          Shown in danger cards, what-if simulator, and marker popups.
        </div>
      </div>

      <div class="t-card" style="margin-bottom:10px">
        <div class="cl">🗺 CartoDB · OpenStreetMap · Esri</div>
        <div class="cb">
          Base map tiles only — no scientific data.
          Dark Matter (default), street, and satellite views.
        </div>
      </div>

      <div class="divider"></div>
      <div class="section-label">Original to this project</div>
      <div style="font-family:var(--mono);font-size:9.5px;color:var(--warm);line-height:1.9">
        · Danger score formula<br>
        &nbsp;&nbsp;(LP × sensitivity × threat multiplier)<br>
        · Threat overlap heatmap computation<br>
        · What-if LP reduction simulator
      </div>
    </div>


    <div id="panel-about" class="eco-panel">
      <h2>Why This<br><em>Matters</em></h2>
      <div class="rule"></div>
      <p>New Jersey sits at one of Earth's most critical ecological crossroads.
      The Atlantic Flyway funnels billions of migratory birds through the state
      each year — while the same coastline hosts endangered sea turtle nesting sites.
      Both are under mounting pressure from artificial light at night.</p>

      <div class="t-card">
        <div class="cl">🦅 Avian light attraction</div>
        <div class="cb">Nocturnally migrating songbirds navigate by starlight.
        Artificial sky glow causes fatal disorientation and glass-strike collisions —
        roughly <strong style="color:var(--sage)">1 billion deaths per year</strong> in North America.</div>
      </div>
      <div class="t-card am">
        <div class="cl">🐢 Turtle disorientation</div>
        <div class="cb">Loggerhead and Leatherback hatchlings use horizon brightness gradients
        to find the ocean. Beachfront ALAN causes fatal inland crawls.
        NJ hosts confirmed nesting of both species — among the northernmost documented
        on the US East Coast. Kemp's Ridley (IUCN CR) does not nest in NJ but
        <strong style="color:var(--amber)">juveniles forage in NJ coastal waters</strong>
        overlapping high-LP zones.</div>
      </div>
      <div class="t-card rs">
        <div class="cl">🌃 NJ light pollution context</div>
        <div class="cb">NJ is the most densely populated US state. Its coastal skyglow rivals
        metropolitan Chicago. The Newark–NY corridor produces some of the highest
        VIIRS radiance readings on the Eastern Seaboard.</div>
      </div>

      <div class="divider"></div>
      <div style="border-left:1px solid var(--sage);padding-left:12px">
        <div style="font-family:var(--serif);font-size:15px;font-style:italic;
                    color:var(--sage);margin-bottom:4px">Cape May Chokepoint</div>
        <div class="cb" style="font-family:var(--mono);font-size:10px;
                                color:rgba(195,188,163,.65);line-height:1.65">
          One of North America's most important raptor migration bottlenecks.
          The Delaware Bay shore hosts the world's largest Red Knot concentration
          each May — fueling on horseshoe crab eggs before flying nonstop to the Arctic.
        </div>
      </div>

      <div class="divider"></div>
      <div class="section-label">Data sources</div>
      <div style="font-family:var(--mono);font-size:9px;color:var(--dim);line-height:2">
        VIIRS · World Atlas of Artificial Night-Sky Brightness<br>
        eBird, Cornell Lab of Ornithology, Ithaca, New York · ebird.org<br>
        eBird. 2024. eBird: An online database of bird distribution and<br>
        abundance [web application]. Available: http://www.ebird.org<br>
        NOAA Fisheries · NJ DEP · Marine Mammal Stranding Center (MMSC)<br>
        Tiles: CartoDB Dark Matter / Esri World Imagery
      </div>
    </div>

    <div id="panel-legend" class="eco-panel">
      <h2>Map <em>Legend</em></h2>
      <div class="rule"></div>
      <div class="section-label">Priority migrants — eBird live data</div>
      {species_rows}
      <div class="divider"></div>
      <div class="section-label">Sea turtle nesting species</div>
      {turtle_rows}
      <div class="divider"></div>
      <div class="sp-row">
        <div style="width:18px;height:7px;flex-shrink:0;border-radius:2px;
                    background:rgba(0,200,230,.2);border:1px solid rgba(0,200,230,.45)"></div>
        <span>Atlantic Flyway corridor</span>
      </div>
      <div class="sp-row"><span style="font-size:13px;flex-shrink:0">⭐</span><span>Notable / rare sighting</span></div>
      <div class="sp-row"><span style="font-size:13px;flex-shrink:0">📍</span><span>eBird hotspot</span></div>
    </div>

    <div id="panel-lp" class="eco-panel">
      <h2>Light <em>Pollution</em></h2>
      <div class="rule"></div>
      <p>Artificial sky brightness by county, measured in mcd/m² above natural background.
      Click any county on the map for its exact value.</p>

      <div class="section-label">County colour scale</div>
      <div style="display:flex;flex-direction:column;gap:5px;margin-bottom:12px">
        <div style="display:flex;align-items:center;gap:9px">
          <div style="width:28px;height:11px;border-radius:3px;flex-shrink:0;background:#0c1e12;border:1px solid rgba(200,200,180,.12)"></div>
          <span style="font-family:var(--mono);font-size:9.5px;color:var(--warm)">&lt;3 mcd/m² &nbsp; Rural dark sky</span>
        </div>
        <div style="display:flex;align-items:center;gap:9px">
          <div style="width:28px;height:11px;border-radius:3px;flex-shrink:0;background:#503205"></div>
          <span style="font-family:var(--mono);font-size:9.5px;color:var(--warm)">3–9 &nbsp; Suburban fringe</span>
        </div>
        <div style="display:flex;align-items:center;gap:9px">
          <div style="width:28px;height:11px;border-radius:3px;flex-shrink:0;background:#a0640a"></div>
          <span style="font-family:var(--mono);font-size:9.5px;color:var(--warm)">9–27 &nbsp; Suburban-urban</span>
        </div>
        <div style="display:flex;align-items:center;gap:9px">
          <div style="width:28px;height:11px;border-radius:3px;flex-shrink:0;background:#dca014"></div>
          <span style="font-family:var(--mono);font-size:9.5px;color:var(--warm)">27–54 &nbsp; Urban bright</span>
        </div>
        <div style="display:flex;align-items:center;gap:9px">
          <div style="width:28px;height:11px;border-radius:3px;flex-shrink:0;background:#f5f5b4;border:1px solid rgba(200,200,180,.15)"></div>
          <span style="font-family:var(--mono);font-size:9.5px;color:var(--warm)">&gt;54 &nbsp; City core / severe</span>
        </div>
      </div>

      <div class="divider"></div>
      <div class="section-label">NJ worst counties</div>
      <div style="font-family:var(--mono);font-size:9.5px;color:var(--warm);line-height:2">
        Hudson &nbsp;&nbsp;&nbsp; 87.4 mcd/m²<br>
        Essex &nbsp;&nbsp;&nbsp;&nbsp; 74.1 mcd/m²<br>
        Union &nbsp;&nbsp;&nbsp;&nbsp; 58.3 mcd/m²<br>
        Bergen &nbsp;&nbsp;&nbsp; 52.7 mcd/m²
      </div>

      <div class="divider"></div>
      <div class="section-label">Darkest counties (wildlife refuges)</div>
      <div style="font-family:var(--mono);font-size:9.5px;color:var(--warm);line-height:2">
        Cumberland &nbsp; 5.1 mcd/m²<br>
        Sussex &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 6.4 mcd/m²<br>
        Cape May &nbsp;&nbsp;&nbsp;&nbsp; 8.9 mcd/m²
      </div>

      <div class="divider"></div>
      <div style="font-family:var(--mono);font-size:8.5px;color:var(--dim);line-height:1.75">
        Falchi F. et al. (2016) The new world atlas of artificial<br>
        night sky brightness. <em>Science Advances</em> 2(6):e1600377<br>
        DOI: 10.1126/sciadv.1600377<br>
        Data: DOI: 10.5880/GFZ.1.4.2016.001
      </div>
    </div>

    <div id="panel-danger" class="eco-panel">
      <h2>Most <em>in Danger</em></h2>
      <div class="rule"></div>
      <p style="margin-bottom:12px">Ranked by a composite score: mean LP exposure (mcd/m²) across
      primary NJ range counties × light-sensitivity × IUCN threat status.
      <span style="color:#ff8888">Red ✕ markers</span> show their locations on the map.</p>
      <div id="danger-cards"></div>
      <div class="divider"></div>
      <div style="font-family:var(--mono);font-size:8.5px;color:var(--dim);line-height:1.7">
        Scoring: LP exposure × sensitivity × (1 + 0.25 × threat level)<br>
        Data: Falchi 2016 · IUCN Red List · NJ DEP · Cornell eBird
      </div>
    </div>

    <script>
      // Inject danger cards from Python-computed data
      (function() {{
        var data = {danger_json};
        var container = document.getElementById('danger-cards');
        if (!container || !data) return;
        var ranks = ['#1', '#2', '#3'];
        var iucnColors = {{'CR':'#ff4444','EN':'#ff7744','VU':'#ffaa33','NT':'#ddcc55','LC':'#88bb66'}};
        data.forEach(function(d, i) {{
          var col = iucnColors[d.iucn] || '#ff8888';
          container.innerHTML += (
            '<div style="background:rgba(180,40,40,.07);border:1px solid rgba(220,60,60,.22);' +
            'border-radius:8px;padding:11px 12px;margin-bottom:10px">' +
              '<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:5px">' +
                '<div style="font-family:var(--serif);font-size:15px;color:#ff8888;font-style:italic">' +
                  ranks[i] + ' — ' + d.species + '</div>' +
                '<div style="font-family:var(--mono);font-size:8px;color:' + col + ';' +
                  'background:rgba(255,80,80,.1);border:1px solid rgba(255,80,80,.2);' +
                  'border-radius:3px;padding:1px 5px">' + d.iucn + '</div>' +
              '</div>' +
              '<div style="font-family:var(--mono);font-size:9px;color:rgba(200,180,160,.6);margin-bottom:7px">' +
                d.status_label + ' &nbsp;·&nbsp; Score: <b style=\"color:#ff9966">' + d.score + '</b>' +
                ' &nbsp;·&nbsp; Avg LP: <b style=\"color:#ffbb55">' + d.mean_lp + ' mcd/m²</b>' +
              '</div>' +
              '<div style="font-family:var(--mono);font-size:9.5px;color:rgba(210,195,175,.75);line-height:1.65">' +
                d.reason + '</div>' +
            '</div>'
          );
        }});
      }})();

      var _eco = null;
      function ecoToggle(id) {{
        var panel = document.getElementById('panel-' + id);
        var btn   = document.getElementById('btn-'   + id);
        if (_eco === id) {{
          panel.classList.remove('visible');
          btn.classList.remove('active');
          _eco = null;
        }} else {{
          if (_eco) {{
            document.getElementById('panel-' + _eco).classList.remove('visible');
            document.getElementById('btn-'   + _eco).classList.remove('active');
          }}
          panel.classList.add('visible');
          btn.classList.add('active');
          _eco = id;
        }}
      }}
      document.addEventListener('click', function(e) {{
        if (_eco &&
            !e.target.closest('.eco-panel') &&
            !e.target.closest('.eco-btn')) {{
          document.getElementById('panel-' + _eco).classList.remove('visible');
          document.getElementById('btn-'   + _eco).classList.remove('active');
          _eco = null;
        }}
      }});
    </script>
    """
    m.get_root().html.add_child(folium.Element(ui_html))


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n🗺  NJ Ecological Convergence Map  —  building…\n")

    m = build_base_map()

    print("  💡 Light pollution overlay (VIIRS tiles)…")
    add_light_pollution(m)

    print("  🦅 Atlantic Flyway corridor…")
    add_flyway(m)

    print("  🐢 Sea turtle nesting sites…")
    add_turtles(m)

    has_key = EBIRD_API_KEY not in ("YOUR_EBIRD_API_KEY", "", None)

    if has_key:
        print(f"  🐦 eBird API — fetching data for {NJ_REGION_CODE}…")
        obs     = fetch_recent_obs(EBIRD_API_KEY, NJ_REGION_CODE, DAYS_BACK)
        notable = fetch_notable_obs(EBIRD_API_KEY, NJ_REGION_CODE, DAYS_BACK)
        add_ebird_layers(m, obs, notable)

        print("  📍 eBird coastal hotspots…")
        add_hotspots(m, EBIRD_API_KEY)
    else:
        print(
            "  ⚠  eBird API key not set — bird observation layers skipped.\n"
            "     Edit EBIRD_API_KEY at the top of nj_eco_map.py\n"
            "     Free key: https://ebird.org/api/keygen\n"
        )

    print("  🔥 Computing threat overlap heatmap…")
    add_threat_heatmap(m)

    print("  🚨 Computing most-in-danger species…")
    top3 = add_danger_layer(m)

    add_title(m)
    add_legend(m, top3)

    print("  🗓  Adding seasonal migration calendar…")
    add_seasonal_control(m)

    print("  🎛  Adding what-if LP simulator…")
    add_whatif_simulator(m)

    # Layer-toggle control
    folium.LayerControl(collapsed=False, position="topright").add_to(m)

    # Fullscreen button
    plugins.Fullscreen(position="topleft").add_to(m)

    # Mini overview map
    plugins.MiniMap(toggle_display=True, position="bottomright").add_to(m)

    # Save
    m.save(OUTPUT_FILE)
    abs_path = os.path.abspath(OUTPUT_FILE)
    print(f"\n✅  Saved → {abs_path}")

    # ── Serve via localhost so browser tiles load without CORS issues ─────────
    import threading, http.server, socketserver, webbrowser as _wb

    PORT     = 8765
    html_dir = os.path.dirname(abs_path) or "."

    class _H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=html_dir, **kw)
        def log_message(self, fmt, *args):
            pass  # silence access log

    def _serve():
        with socketserver.TCPServer(("", PORT), _H) as httpd:
            httpd.serve_forever()

    t = threading.Thread(target=_serve, daemon=True)
    t.start()

    url = f"http://localhost:{PORT}/{OUTPUT_FILE}"
    print(f"   Serving at {url}")
    print("   (keep this terminal open — Ctrl-C to stop)\n")
    _wb.open(url)

    print("   Press Enter to stop the server and exit.")
    try:
        input()
    except KeyboardInterrupt:
        pass
    print("  Server stopped.")


if __name__ == "__main__":
    main()
