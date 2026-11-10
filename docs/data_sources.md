# Data sources — the shopping list

Every input the pipeline expects for a real run, where it comes from, and the file to prepare. Column layouts
are in [`templates/`](../templates/) (one header row per table); coordinates are WGS 84 decimal degrees.

The repository contains **no real candidate sites**. `make test` and `make selftest` use the synthetic data set
written by `fs2s synthetic`, and the simulations in `results/sim_out/` place synthetic sites and stations on
the real Bang Pakong river network. URLs, portal names and dataset versions below were written from
memory and **must be verified** [ต้องตรวจ] before you rely on them.

## Module 1 — screening in Google Earth Engine

`gee/fs2s_module1_screening.js` reads these Earth Engine catalogue datasets directly; nothing to download.

| proxy | dataset (Earth Engine ID) | role |
|---|---|---|
| new structures, material piles | `COPERNICUS/S2_HARMONIZED`, `GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED` | baseline vs recent median composites, cloud-masked |
| land cover context | `GOOGLE/DYNAMICWORLD/V1` | built-up and bare-ground change |
| thermal anomalies | `LANDSAT/LC08/C02/T1_L2`, `LANDSAT/LC09/C02/T1_L2` (ST_B10) | hot pixels relative to the local background |
| night-time activity | `NASA/VIIRS/002/VNP46A2`, `NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG` | persistent lighting outside settlements |
| settlements mask | `JRC/GHSL/P2023A/GHS_BUILT_S/2015` | excludes existing built-up areas |
| pond colour | `COPERNICUS/S2_SR_HARMONIZED`, `JRC/GSW1_4/GlobalSurfaceWater` | hue / Forel-Ule anomalies of small water bodies |
| flood connectivity (C2) | `COPERNICUS/S1_GRD` | wet-season flood frequency, exported as GeoTIFF |
| study area | `FAO/GAUL/2015/level1` | provinces (or set `aoiAsset`) |

Optional uploads (Assets → New → Table upload), set in `CFG`:

| asset | source | how |
|---|---|---|
| `firmsAsset` | NASA FIRMS archive, VIIRS 375 m, Thailand — https://firms.modaps.eosdis.nasa.gov/download/ | request the archive CSV for Thailand; keep `latitude`/`longitude` columns |
| `industrialEstatesAsset` | Industrial Estate Authority of Thailand (กนอ.) — https://www.ieat.go.th, or OpenStreetMap `landuse=industrial` | polygons of industrial estates and parks to exclude |

Export: `candidates_from_gee.csv` (see [`templates/candidates_from_gee.csv`](../templates/candidates_from_gee.csv)),
footprints (SHP) and the flood-frequency raster.

## Verification layers — `fs2s verify`

| file | content | source | how |
|---|---|---|---|
| `diw_factories.csv` | licensed factories: `fac_id, category, lon, lat` | Department of Industrial Works (กรมโรงงานอุตสาหกรรม) — https://www.diw.go.th; factory lists are also on https://data.go.th | download the factory registry for the study provinces; categories 101, 105 and 106 are the targets, other categories feed the registry-mismatch flag. Category text such as `105(1)` or `ลำดับที่ 106` is parsed automatically |
| `known_sites.csv` | previously reported sites | news archives, DIW and police enforcement announcements, Pollution Control Department (กรมควบคุมมลพิษ) complaints, NGO reports (e.g. EARTH, Greenpeace Thailand) | one row per reported location with `source_type`, `source_ref`, `date_reported` and a location precision in metres |
| `hard_negatives.csv` | look-alikes to exclude: rice and sugar mills, landfills, livestock farms | DIW registry (other categories), OpenStreetMap, field knowledge | `neg_type` and an optional per-row `buffer_m` |
| `labels.csv` | verified labels for calibration: `site_id, verified` | field visits, very-high-resolution imagery review | the screening score is a heuristic until calibrated with these |

## Module 3 — river network, stations and cores

| file | content | source | how |
|---|---|---|---|
| rivers | vector river network with downstream IDs | HydroRIVERS v1.0 (Lehner & Grill, 2013) — https://www.hydrosheds.org/products/hydrorivers; or MERIT-Basins — https://www.reachhydro.org/home/params/merit-basins | Asia shapefile (`--river-format hydrorivers`) or MERIT-Basins (`meritbasins`); any network with an ID and next-downstream ID works with `custom`. `make data` fetches a HydroRIVERS extract for the simulations |
| `stations.csv` | water or sediment chemistry: `station_id, lon, lat` and at least one marker | Pollution Control Department surface-water monitoring (https://www.pcd.go.th) for water; own sediment sampling for the e-waste marker suite | Cu, Pb, Sn, Sb, Cd (plus Ni, Zn, Al, Fe for normalisation; PBDEs and PCDD/Fs on a subset). Values below detection as `<DL`. Mark reference stations with `is_reference` |
| `cores.csv` | dated sediment cores: `station_id, onset_year, onset_year_sd` | own coring, ²¹⁰Pb (CRS model) validated with ¹³⁷Cs | onset of marker enrichment, for criterion C4 |
| subdistricts (optional, `--admin`) | ตำบล polygons | OpenGISData-Thailand — https://github.com/chingchai/OpenGISData-Thailand (CC BY 4.0) | adds subdistrict names to the restricted tables |

## Figures and simulations — `make data`

`scripts/download_data.py` fetches Natural Earth layers (public domain), OpenGISData-Thailand districts and the
HydroRIVERS v1.0 extract (`rivers.json`) from https://github.com/oadtz/waterways into `data/`. Check the
HydroSHEDS licence before redistributing anything derived from it.

## Minimal real-data start

A first real run of `fs2s verify` needs only `candidates_from_gee.csv`; every other layer is optional and its
absence is logged. A credible Bang Pakong run needs the candidates, `diw_factories.csv`, `known_sites.csv`,
HydroRIVERS and `stations.csv` with paired upstream and downstream sediment samples. Keep every output
whose name contains `_RESTRICTED` off public repositories (see README, Responsible use).
