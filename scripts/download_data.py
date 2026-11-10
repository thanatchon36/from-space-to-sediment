#!/usr/bin/env python3
"""Download the third-party map data used by the figure scripts and `fs2s network` / `fs2s sim` into data/.
Sources: Natural Earth (public domain); OpenGISData-Thailand districts (CC BY 4.0);
HydroRIVERS v1.0 extract for mainland Southeast Asia from github.com/oadtz/waterways
(HydroRIVERS: Lehner & Grill 2013 - check the HydroSHEDS licence terms)."""
import io
import urllib.request
import zipfile
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
NE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
FILES = {f"{n}.geojson": NE + f"{n}.geojson" for n in (
    "ne_10m_admin_0_countries", "ne_10m_admin_1_states_provinces", "ne_10m_admin_0_boundary_lines_land",
    "ne_10m_coastline", "ne_10m_lakes", "ne_50m_admin_0_countries")}
FILES["og_districts.geojson"] = ("https://raw.githubusercontent.com/chingchai/OpenGISData-Thailand/"
                                 "master/districts.geojson")
WATERWAYS = "https://codeload.github.com/oadtz/waterways/zip/refs/heads/main"


def get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=300) as r:
        return r.read()


def main():
    DATA.mkdir(exist_ok=True)
    for name, url in FILES.items():
        path = DATA / name
        if path.exists():
            print(f"exists      {name}")
            continue
        print(f"downloading {name}")
        path.write_bytes(get(url))
    rivers = DATA / "rivers.json"
    if not rivers.exists():
        print("downloading rivers.json (HydroRIVERS extract)")
        z = zipfile.ZipFile(io.BytesIO(get(WATERWAYS)))
        rivers.write_bytes(z.read("waterways-main/public/data/rivers.json"))
    print(f"done: {len(list(DATA.iterdir()))} files in {DATA}")


if __name__ == "__main__":
    main()
