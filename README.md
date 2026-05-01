# NJ Light Pollution Mapper

An interactive map of New Jersey overlaying three pressures on coastal wildlife:

- **Light pollution** by county (Falchi et al. 2016 World Atlas + VIIRS DNB).
- **Atlantic Flyway corridor** with the Cape May migration chokepoint.
- **Sea turtle nesting sites** along the NJ coast (NOAA NCCOS / NJ DEP / MMSC).

The script generates `nj_eco_map.html` and serves it locally so map tiles load without CORS issues.

## Features

- Per-county choropleth on a dark base map, with an LP scale legend.
- Live priority-species and notable-rarity markers from the **Cornell Lab eBird API**.
- A composite **danger score** (LP × sensitivity × IUCN status) flags the top 3 most-impacted species.
- A **threat-overlap heatmap** showing where LP, the flyway, and turtle nesting all converge.
- A **seasonal slider** that dims species/turtles outside their NJ months.
- A **what-if simulator**: drag county sliders to model LP reductions and watch danger scores update live.

## Setup

```bash
pip install -r requirements.txt
```

Get a free eBird API key at <https://ebird.org/api/keygen>, then expose it:

```bash
# macOS / Linux
export EBIRD_API_KEY=your_key_here

# Windows (PowerShell)
$env:EBIRD_API_KEY = "your_key_here"
```

If the key isn't set the map still renders — the eBird layers are simply skipped.

## Run

```bash
python Nj_eco_map.py
```

The script writes `nj_eco_map.html`, starts a local server (default port 8765, falls back automatically if busy), and opens your browser. Press Enter in the terminal to stop.

## Data sources

- Falchi F. et al. (2016). *Science Advances* 2(6):e1600377. DOI: 10.1126/sciadv.1600377.
- eBird, Cornell Lab of Ornithology — <https://ebird.org>.
- NOAA Fisheries · NJ DEP Endangered & Nongame Species Program · Marine Mammal Stranding Center (MMSC).
- IUCN Red List — <https://iucnredlist.org>.
- Map tiles: CartoDB Dark Matter, OpenStreetMap, Esri World Imagery.

## File layout

```
Nj_eco_map.py        # generator script
nj_eco_map.html      # generated map (open in any modern browser)
requirements.txt     # Python dependencies
Screenshots_of_features/
```
