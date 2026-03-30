# NJ Ecological Convergence Map
### Light Pollution x Atlantic Flyway x Sea Turtle Nesting

An interactive conservation data tool visualizing the relationship 
between artificial light pollution, bird migration, and sea turtle 
nesting vulnerability across the New Jersey coastline.

Built by Jan Dudaczyk — Bergen County Technical High School, 2026
License: MIT

---

## Overview

New Jersey sits at one of the most ecologically significant points on 
the East Coast. The Atlantic Flyway funnels millions of migratory birds 
through the state each year, and the NJ coastline hosts some of the 
northernmost sea turtle nesting activity on the Eastern Seaboard. Both 
are under growing threat from artificial light pollution, which disrupts 
nocturnal migration, disorients sea turtle hatchlings crawling toward 
the ocean, and degrades foraging habitat for threatened shorebird species.

This tool makes those threats visible. By layering VIIRS satellite light 
pollution data over real-time Cornell eBird bird observations, NOAA sea 
turtle nesting sites, and the Atlantic Flyway corridor, it creates an 
interactive platform for understanding where light pollution and 
ecological vulnerability overlap and what that means for species already 
under pressure.

---

## Features

- VIIRS Light Pollution Overlay — satellite-derived artificial sky 
  brightness across NJ, sourced from the World Atlas of Artificial 
  Night-Sky Brightness (Falchi et al. 2016)
- Atlantic Flyway Corridor — visualized coastal migration funnel from 
  the NY/CT border south to Cape May and back up the Delaware Bay
- Sea Turtle Nesting Sites — six confirmed NJ nesting locations with 
  species-specific data (Loggerhead, Leatherback, Green Turtle) from 
  NOAA NCCOS and NJ DEP field surveys
- Live eBird Integration — real-time bird observation data from the 
  Cornell Lab of Ornithology eBird API v2, including notable sightings 
  and coastal hotspots
- Per-Species Danger Scoring — composite threat index combining light 
  pollution exposure, species light-sensitivity, and IUCN conservation 
  status for 11 priority migratory species
- Threat Overlap Heatmap — identifies geographic zones where light 
  pollution intensity and ecological vulnerability are highest
- Seasonal Migration Calendar — month-by-month species presence windows 
  for all tracked birds and sea turtles
- What-If Light Pollution Simulator — models ecological impact under 
  different light reduction scenarios
- Interactive Dashboard — layer controls, fullscreen mode, minimap, and 
  species danger cards with IUCN status and threat explanations

---

## Data Sources

| Dataset | Source |
|---------|--------|
| Light pollution | VIIRS satellite / Falchi et al. 2016 World Atlas |
| Bird observations | Cornell Lab of Ornithology eBird API v2 |
| Sea turtle nesting | NOAA NCCOS / NJ DEP / Marine Mammal Stranding Center NJ |
| Conservation status | IUCN Red List |
| Flyway corridor | USFWS Atlantic Flyway Council |

---

## Installation and Usage

export EBIRD_API_KEY=your_key_here  # Mac/Linux
set EBIRD_API_KEY=your_key_here     # Windows

Requirements: Python 3.8+
```bash
git clone https://github.com/jdudaczyk09-droid/nj-eco-map
cd nj-eco-map
pip install -r requirements.txt
```

Get a free eBird API key at https://ebird.org/api/keygen and paste it 
into the EBIRD_API_KEY field at the top of nj_eco_map.py.

Run the map:
```bash
python nj_eco_map.py
```

The map will build and open automatically in your browser at 
http://localhost:8765/nj_eco_map.html. Keep the terminal open while 
using it. Press Enter to stop the server.

---

## Why I Built This

I started thinking about this project while writing a guest editorial 
about light pollution for my local newspaper. Researching the article, 
I kept coming across the same problem from different angles. Birds 
colliding with buildings in New York because artificial light scrambles 
their navigation. Sea turtle hatchlings on the Jersey Shore crawling 
toward parking lots instead of the ocean because artificial light 
outshines the moon. The data existed but it was scattered across 
different agencies and hard to visualize together.

Around the same time I was working on a computer vision system for our 
school robotics team to detect invasive European green crabs underwater. 
That project made me realize how much useful ecological data already 
exists and how much value you can add just by making it accessible and 
visual.

So I built this. The goal was to create something that shows where light 
pollution and ecological vulnerability actually converge along the NJ 
coast, which species are most at risk, and what targeted light reduction 
could realistically accomplish. I used the Cornell Lab of Ornithology 
eBird API for real-time bird data because it is one of the best open 
biodiversity datasets available, and I wanted the map to reflect what 
is actually happening right now, not just static historical records.

---

## Conservation Context

New Jersey's coastline lies within the Atlantic Flyway, one of four 
major North American bird migration corridors, and supports confirmed 
nesting from Loggerhead, Leatherback, and Green sea turtles. The state's 
proximity to the New York metro area creates serious pressure on these 
ecosystems. Species like the Piping Plover, Red Knot, and Black Skimmer 
depend on dark coastal habitat that keeps shrinking as artificial light 
expands. This map is an attempt to show exactly where that pressure is 
greatest and which species are bearing the most of it.

---

## Future Development

- Real-time light pollution sensor network integration
- Expansion to full Atlantic coast coverage
- Species population trend data overlays
- Mobile responsive interface
- Public API endpoint for conservation researchers and educators
- Integration with NJ Lights Out Initiative building participation data

---

## Acknowledgments

Cornell Lab of Ornithology for the eBird API and the open science 
infrastructure behind it. NOAA NCCOS for sea turtle nesting data. 
Falchi et al. 2016 for the World Atlas of Artificial Night-Sky Brightness 
methodology. NJ Department of Environmental Protection for coastal field 
survey data. Marine Mammal Stranding Center of NJ for regional nesting 
records.

---

## License

MIT License — Copyright Jan Dudaczyk, 2026

Permission is hereby granted, free of charge, to any person obtaining 
a copy of this software to use, copy, modify, merge, publish, 
distribute, and sublicense, subject to the condition that the above 
copyright notice appears in all copies.