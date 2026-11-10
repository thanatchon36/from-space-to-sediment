/*******************************************************************************
 * FROM SPACE TO SEDIMENT - Module 1: multi-sensor screening of candidate
 * e-waste processing / dumping sites.  Google Earth Engine Code Editor (JS).
 *
 * Default AOI : Prachin Buri + Chachoengsao (Bang Pakong basin), Thailand
 * Window      : 2018-01-01 .. 2026-10-31   (baseline 2016-2017)
 *
 * Proxies (paper: Table 2, Fig. 3)
 *  P1 New structures or material piles of 0.1-2 ha outside industrial estates
 *     (Dynamic World built/bare change + Sentinel-2 TOA indices + Sentinel-1 VV)
 *  P2 Off-season (May-Nov) or recurrent thermal anomalies
 *     (VIIRS 375 m active fires from a FIRMS archive table asset + Landsat 8/9 ST_B10)
 *  P3 Night-time light surge after 2018 and after 2025 (VIIRS Black Marble VNP46A2)
 *  P4 Colour / turbidity anomalies of small ponds within 200 m (Sentinel-2 SR hue angle)
 *  +  Wet-season flood frequency from Sentinel-1 (hydrological connectivity, C2)
 *
 * READ BEFORE USE
 *  - screening_score is a heuristic in [0,1], NOT a calibrated probability.
 *    Calibrate it with verified labels in fs2s_verify_trace.py (--labels).
 *  - Outputs are CANDIDATES, not findings of illegality. Keep exact coordinates
 *    restricted and publish aggregated products only (paper, Section 9).
 *  - Sentinel-2 L2A is not available over Thailand before late 2018. The
 *    2016-2017 structural baseline therefore uses L1C TOA in BOTH periods, and
 *    the pond-colour baseline starts in 2019 (first full L2A year).
 *  - Thresholds below are starting values. Tune them on known seed sites and
 *    hard negatives before trusting the ranking.
 *  - Exports are heavy. Run them as batch tasks (Tasks tab); if a task times
 *    out, split the AOI (e.g. one province per run) via CFG.aoiAsset.
 ******************************************************************************/

// =============================== CONFIGURATION ===============================
var CFG = {
  // ---- area of interest ----------------------------------------------------
  provinces: ['Prachin Buri', 'Chachoengsao'],   // FAO GAUL 2015 ADM1_NAME spelling
  aoiAsset: null,            // optional FeatureCollection asset that overrides provinces
  fallbackBox: [100.85, 13.10, 102.10, 14.50],   // used if GAUL names do not match

  // ---- optional user assets (Assets > New > Table upload) ------------------
  industrialEstatesAsset: null,  // polygons of industrial estates/parks to exclude
  firmsAsset: null,              // FIRMS VIIRS 375 m archive CSV (lon/lat columns
                                 // 'longitude','latitude'; keep acq_date, type, frp)

  // ---- time windows (end dates are exclusive) -------------------------------
  baseStart: '2016-01-01', baseEnd: '2018-01-01',
  studyStart: '2018-01-01', studyEnd: '2026-11-01',
  recentStart: '2024-01-01',
  pondBaseStart: '2019-01-01', pondBaseEnd: '2020-01-01',

  // ---- P1 structures / piles ------------------------------------------------
  minAreaM2: 1000, maxAreaM2: 20000,   // 0.1-2 ha
  dwBaseMax: 0.25,                      // Dynamic World probability before 2018
  dwNewMin: 0.50,                       // Dynamic World probability in the recent window
  dVVmin: 3.0,                          // dB increase of Sentinel-1 VV (new roofs)
  dNDBImin: 0.08, dNDVImax: -0.15,

  // ---- P2 thermal -----------------------------------------------------------
  offSeasonMonths: [5, 6, 7, 8, 9, 10, 11],   // outside the Dec-Apr burning season
  viirsRadiusM: 400,                           // VIIRS 375 m pixel + geolocation error
  lstAnomalyK: 4.0,                            // hot if LST exceeds local mean by this
  lstBackgroundRadiusM: 750,

  // ---- P3 night-time lights -------------------------------------------------
  ntlSource: 'VNP46A2',        // 'VNP46A2' (Black Marble) or 'VCMSLCFG' (EOG monthly)
  ntlRatioMin: 1.5,
  ntlDeltaMin: 2.0,            // native units of the chosen product; check scaling
  settlementMaxFrac: 0.05,     // GHSL 2015 built fraction within 1 km = "no community"

  // ---- P4 ponds ---------------------------------------------------------------
  pondRadiusM: 200,
  pondMaxAreaM2: 50000,        // ignore rivers and reservoirs
  hueMethod: 'RGB10',          // 'RGB10' (10 m bands, small ponds) or 'MSI5'
  hueShiftMinDeg: 40, hueZmin: 2.5, ndtiShiftMin: 0.15,

  // ---- flood connectivity ----------------------------------------------------
  floodVVmaxDb: -16, floodMonths: [8, 11],

  // ---- scoring and export -----------------------------------------------------
  weights: {struct: 0.25, thermal: 0.30, ntl: 0.15, pond: 0.30},
  minExportScore: 0.30,        // export sites with score >= this OR >= 2 proxies
  exportFolder: 'FS2S_module1',
  prefix: 'bangpakong',
  crs: 'EPSG:32647',           // WGS 84 / UTM 47N covers both provinces
  debugPrints: false
};

// ==================================== AOI ====================================
var gaul = ee.FeatureCollection('FAO/GAUL/2015/level1')
  .filter(ee.Filter.eq('ADM0_NAME', 'Thailand'))
  .filter(ee.Filter.inList('ADM1_NAME', CFG.provinces));
var aoi = CFG.aoiAsset
  ? ee.FeatureCollection(CFG.aoiAsset).geometry()
  : ee.Geometry(ee.Algorithms.If(gaul.size().gt(0), gaul.geometry(),
                                 ee.Geometry.Rectangle(CFG.fallbackBox)));
print('Provinces matched in FAO GAUL (expect 2; otherwise the fallback box is used):',
      gaul.aggregate_array('ADM1_NAME'));

// ================================== HELPERS ==================================
var CSP = ee.ImageCollection('GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED');
var S2_BANDS = ['B1', 'B2', 'B3', 'B4', 'B5', 'B8', 'B11'];

// Sentinel-2 collection (L1C or L2A) with Cloud Score+ masking, reflectance 0-1.
function s2(collectionId, start, end) {
  return ee.ImageCollection(collectionId)
    .filterBounds(aoi).filterDate(start, end)
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 80))
    .linkCollection(CSP, ['cs_cdf'])
    .map(function (img) {
      var clear = img.select('cs_cdf').gte(0.60);
      var refl = img.select(S2_BANDS).divide(10000).updateMask(clear);
      return ee.Image(refl.copyProperties(img, ['system:time_start']));
    });
}

function addIndices(img) {
  return img.addBands(ee.Image.cat([
    img.normalizedDifference(['B8', 'B4']).rename('NDVI'),
    img.normalizedDifference(['B11', 'B8']).rename('NDBI'),
    img.normalizedDifference(['B3', 'B11']).rename('MNDWI'),
    img.normalizedDifference(['B3', 'B8']).rename('NDWI'),
    img.normalizedDifference(['B4', 'B3']).rename('NDTI')   // turbidity (Lacaux et al. 2007)
  ]));
}

// Sentinel-1 IW GRD, VV backscatter in dB.
function s1(start, end) {
  return ee.ImageCollection('COPERNICUS/S1_GRD')
    .filterBounds(aoi).filterDate(start, end)
    .filter(ee.Filter.eq('instrumentMode', 'IW'))
    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
    .select('VV');
}

// Mean of one band of a collection; constant fallback if the collection is empty.
function safeMean(col, band, fallback) {
  return ee.Image(ee.Algorithms.If(col.size().gt(0), col.select(band).mean(),
                                   ee.Image.constant(fallback).rename(band)));
}

// Null-safe numeric property.
function num(f, key, dflt) {
  var v = f.get(key);
  return ee.Number(ee.Algorithms.If(ee.Algorithms.IsEqual(v, null), dflt, v));
}
function clamp01(x) { return ee.Number(x).max(0).min(1); }

// Reduce an image over a disc around each site (site footprint radius + extra metres),
// then restore the point geometry. Multi-band images keep their band names.
function reduceOnBuffer(fc, img, reducer, scale, extraM) {
  var buffered = fc.map(function (f) {
    var r = ee.Number(f.get('radius_m')).add(extraM).max(15);
    return f.setGeometry(f.geometry().buffer(r, 5));
  });
  return img.reduceRegions({collection: buffered, reducer: reducer, scale: scale,
                            crs: CFG.crs, tileScale: 4})
    .map(function (f) {
      return f.setGeometry(ee.Geometry.Point([f.get('lon'), f.get('lat')]));
    });
}

// =============================== STATIC MASKS ================================
var permWater = ee.Image('JRC/GSW1_4/GlobalSurfaceWater').select('occurrence')
  .unmask(0).gt(80);
var notIE = ee.Image(1);
if (CFG.industrialEstatesAsset) {
  notIE = ee.Image(0).paint(ee.FeatureCollection(CFG.industrialEstatesAsset), 1).not();
}

// ======================= P1  NEW STRUCTURES / PILES ==========================
var DW = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1').filterBounds(aoi);
var dwBaseCol = DW.filterDate(CFG.baseStart, CFG.baseEnd);
var dwRecentCol = DW.filterDate(CFG.recentStart, CFG.studyEnd);
var builtBase = safeMean(dwBaseCol, 'built', 0);
var bareBase = safeMean(dwBaseCol, 'bare', 0);
var builtRecent = safeMean(dwRecentCol, 'built', 0);
var bareRecent = safeMean(dwRecentCol, 'bare', 0);

// First year (2018-2026) in which the annual mean built probability exceeds dwNewMin.
var firstBuiltYear = ee.ImageCollection.fromImages(
  ee.List.sequence(2018, 2026).map(function (y) {
    y = ee.Number(y);
    var col = DW.filterDate(ee.Date.fromYMD(y, 1, 1), ee.Date.fromYMD(y.add(1), 1, 1));
    var built = safeMean(col, 'built', 0);
    return ee.Image.constant(y).toInt16().rename('first_built_year')
      .updateMask(built.gt(CFG.dwNewMin));
  })).min();

var toaBase = addIndices(s2('COPERNICUS/S2_HARMONIZED', CFG.baseStart, CFG.baseEnd).median());
var toaRecent = addIndices(s2('COPERNICUS/S2_HARMONIZED', CFG.recentStart, CFG.studyEnd).median());
var dNDBI = toaRecent.select('NDBI').subtract(toaBase.select('NDBI')).rename('dNDBI');
var dNDVI = toaRecent.select('NDVI').subtract(toaBase.select('NDVI')).rename('dNDVI');
var dVV = s1(CFG.recentStart, CFG.studyEnd).median()
  .subtract(s1(CFG.baseStart, CFG.baseEnd).median()).rename('dVV');

var newBuilt = builtBase.lt(CFG.dwBaseMax).and(builtRecent.gt(CFG.dwNewMin));
var newBare = bareBase.lt(CFG.dwBaseMax).and(bareRecent.gt(CFG.dwNewMin));   // open piles
var changeEvidence = dVV.gt(CFG.dVVmin).or(dNDBI.gt(CFG.dNDBImin)).or(dNDVI.lt(CFG.dNDVImax));
var p1 = newBuilt.or(newBare).and(changeEvidence).and(notIE).and(permWater.not())
  .selfMask().reproject({crs: CFG.crs, scale: 10});   // fixed grid for pixel counting

// Keep connected objects of 0.1-2 ha (10-200 pixels of 10 m).
var nPix = p1.connectedPixelCount({maxSize: 256, eightConnected: true});
var p1sized = p1.updateMask(nPix.gte(CFG.minAreaM2 / 100).and(nPix.lte(CFG.maxAreaM2 / 100)));

var objects = p1sized.toInt().reduceToVectors({
  geometry: aoi, crs: CFG.crs, scale: 10, geometryType: 'polygon',
  eightConnected: true, labelProperty: 'label', maxPixels: 1e10, tileScale: 4
}).map(function (f) { return f.set('site_id', ee.String('BPK_').cat(f.id())); });

var objStack = ee.Image.cat([dVV, dNDBI, dNDVI,
  builtRecent.rename('built_recent'), bareRecent.rename('bare_recent')]);
var sites = objStack.reduceRegions({collection: objects, reducer: ee.Reducer.mean(),
                                    scale: 10, crs: CFG.crs, tileScale: 4});
sites = firstBuiltYear.reduceRegions({collection: sites,
  reducer: ee.Reducer.min().setOutputs(['first_built_year']),
  scale: 10, crs: CFG.crs, tileScale: 4});
// Convert polygons to centroid points that carry footprint size.
sites = sites.map(function (f) {
  var area = f.geometry().area(1);
  var c = f.geometry().centroid(1);
  var xy = c.coordinates();
  return ee.Feature(c, f.toDictionary()).set({
    area_m2: area, radius_m: area.divide(Math.PI).sqrt(),
    lon: xy.get(0), lat: xy.get(1)
  });
});

// =========================== P2  THERMAL ANOMALIES ===========================
function lstHot(collectionId) {
  return ee.ImageCollection(collectionId)
    .filterBounds(aoi).filterDate(CFG.studyStart, CFG.studyEnd)
    .filter(ee.Filter.calendarRange(CFG.offSeasonMonths[0],
            CFG.offSeasonMonths[CFG.offSeasonMonths.length - 1], 'month'))
    .map(function (img) {
      var qa = img.select('QA_PIXEL');
      var clear = qa.bitwiseAnd(2).eq(0)      // bit 1 dilated cloud
        .and(qa.bitwiseAnd(4).eq(0))          // bit 2 cirrus
        .and(qa.bitwiseAnd(8).eq(0))          // bit 3 cloud
        .and(qa.bitwiseAnd(16).eq(0));        // bit 4 cloud shadow
      var lst = img.select('ST_B10').multiply(0.00341802).add(149.0).updateMask(clear); // K
      var bg = lst.focalMean({radius: CFG.lstBackgroundRadiusM, kernelType: 'circle',
                              units: 'meters'});
      var hot = lst.subtract(bg).gt(CFG.lstAnomalyK).rename('lst_hot');
      return ee.Image(hot.updateMask(clear).copyProperties(img, ['system:time_start']));
    });
}
var lstCol = lstHot('LANDSAT/LC08/C02/T1_L2').merge(lstHot('LANDSAT/LC09/C02/T1_L2'));
// Fraction and number of clear off-season scenes with a local hot anomaly.
// Note: TIRS is 100 m (delivered at 30 m), so only strong heat sources register.
var thermalStack = ee.Image.cat([lstCol.mean().rename('lst_hot_freq'),
                                 lstCol.sum().rename('lst_hot_n')]);
sites = reduceOnBuffer(sites, thermalStack, ee.Reducer.max(), 30, 60);

// VIIRS 375 m detections (FIRMS archive). FIRMS 'type' 2 = other static land source.
function addViirs(fc) {
  if (!CFG.firmsAsset) {
    return fc.map(function (f) {
      return f.set({viirs_n_all: -1, viirs_dates_all: -1, viirs_dates_off: -1, viirs_static_n: -1});
    });
  }
  var pts = ee.FeatureCollection(CFG.firmsAsset).filterBounds(aoi)
    .map(function (p) {
      var d = ee.String(p.get('acq_date'));
      return p.set({year: ee.Number.parse(d.slice(0, 4)), month: ee.Number.parse(d.slice(5, 7))});
    })
    .filter(ee.Filter.gte('year', 2018));
  var near = ee.Filter.withinDistance({distance: CFG.viirsRadiusM, leftField: '.geo',
                                       rightField: '.geo', maxError: 10});
  var joined = ee.Join.saveAll({matchesKey: 'hits', outer: true}).apply(fc, pts, near);
  return joined.map(function (f) {
    var raw = f.get('hits');
    var hits = ee.FeatureCollection(ee.List(ee.Algorithms.If(
      ee.Algorithms.IsEqual(raw, null), ee.List([]), raw)));
    var off = hits.filter(ee.Filter.inList('month', CFG.offSeasonMonths));
    return ee.Feature(f.geometry(), f.toDictionary().remove(['hits'], true)).set({
      viirs_n_all: hits.size(),
      viirs_dates_all: hits.aggregate_count_distinct('acq_date'),
      viirs_dates_off: off.aggregate_count_distinct('acq_date'),
      viirs_static_n: hits.filter(ee.Filter.eq('type', 2)).size()
    });
  });
}
sites = addViirs(sites);

// ============================ P3  NIGHT-TIME LIGHTS ==========================
function ntlYear(y) {
  y = ee.Number(y);
  var start = ee.Date.fromYMD(y, 1, 1);
  var end = start.advance(1, 'year');
  if (CFG.ntlSource === 'VNP46A2') {
    // Black Marble daily, BRDF-corrected, gap-filled; keep quality flags 0-1.
    return ee.ImageCollection('NASA/VIIRS/002/VNP46A2').filterBounds(aoi).filterDate(start, end)
      .map(function (img) {
        return img.select('Gap_Filled_DNB_BRDF_Corrected_NTL')
          .updateMask(img.select('Mandatory_Quality_Flag').lte(1));
      }).median().rename('ntl');
  }
  return ee.ImageCollection('NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG').filterBounds(aoi)
    .filterDate(start, end)
    .map(function (img) { return img.select('avg_rad').updateMask(img.select('cf_cvg').gt(0)); })
    .median().rename('ntl');
}
function ntlMean(y0, y1) {
  return ee.ImageCollection.fromImages(ee.List.sequence(y0, y1).map(ntlYear)).mean();
}
var EPS = 0.5;
var ntlBase = ntlMean(2016, 2017), ntlPost18 = ntlMean(2019, 2021);
var ntlPre25 = ntlMean(2023, 2024), ntlPost25 = ntlMean(2025, 2026);
var r18 = ntlPost18.add(EPS).divide(ntlBase.add(EPS)).rename('ntl_ratio_2018');
var d18 = ntlPost18.subtract(ntlBase).rename('ntl_delta_2018');
var r25 = ntlPost25.add(EPS).divide(ntlPre25.add(EPS)).rename('ntl_ratio_2025');
var d25 = ntlPost25.subtract(ntlPre25).rename('ntl_delta_2025');
var ntlSurge = r18.gte(CFG.ntlRatioMin).and(d18.gte(CFG.ntlDeltaMin))
  .or(r25.gte(CFG.ntlRatioMin).and(d25.gte(CFG.ntlDeltaMin))).rename('ntl_surge');
// Baseline settlement density (GHSL built surface 2015, 100 m) within 1 km.
var settle = ee.Image('JRC/GHSL/P2023A/GHS_BUILT_S/2015').select('built_surface')
  .reduceNeighborhood({reducer: ee.Reducer.mean(),
                       kernel: ee.Kernel.circle({radius: 1000, units: 'meters'})})
  .divide(10000).rename('settle_frac_1km');
var ntlStack = ee.Image.cat([r18, d18, r25, d25, ntlSurge, settle]);
sites = reduceOnBuffer(sites, ntlStack, ee.Reducer.max(), 100, 0);

// ============================ P4  POND COLOUR ================================
// Hue angle of water-leaving reflectance (CIE 1931 chromaticity).
//  'RGB10': linear sRGB(D65) -> XYZ on 10 m bands B4/B3/B2; approximate hue, used
//           only for anomalies (temporal shift and population z), not FU classes.
//  'MSI5' : Van der Woerd & Wernand (2018) MSI coefficients incl. B1 (60 m) and
//           the MSI hue correction polynomial; suitable for larger water bodies.
//           VERIFY these coefficients against the paper before publication.
function hueAngle(img) {
  var X, Y, Z;
  if (CFG.hueMethod === 'MSI5') {
    var b = {b1: img.select('B1'), b2: img.select('B2'), b3: img.select('B3'),
             b4: img.select('B4'), b5: img.select('B5')};
    X = img.expression('11.756*b1 + 6.423*b2 + 53.696*b3 + 32.028*b4 + 0.529*b5', b);
    Y = img.expression('1.744*b1 + 22.289*b2 + 65.702*b3 + 16.808*b4 + 0.192*b5', b);
    Z = img.expression('62.696*b1 + 31.101*b2 + 1.778*b3 + 0.015*b4 + 0.000*b5', b);
  } else {
    var R = img.select('B4'), G = img.select('B3'), B = img.select('B2');
    X = R.multiply(0.4124).add(G.multiply(0.3576)).add(B.multiply(0.1805));
    Y = R.multiply(0.2126).add(G.multiply(0.7152)).add(B.multiply(0.0722));
    Z = R.multiply(0.0193).add(G.multiply(0.1192)).add(B.multiply(0.9505));
  }
  var S = X.add(Y).add(Z);
  var a = Y.divide(S).subtract(1 / 3).atan2(X.divide(S).subtract(1 / 3))
    .multiply(180 / Math.PI).add(360).mod(360);
  if (CFG.hueMethod === 'MSI5') {
    var t = a.divide(100);
    var corr = t.pow(5).multiply(-164.83).add(t.pow(4).multiply(1139.90))
      .add(t.pow(3).multiply(-3006.04)).add(t.pow(2).multiply(3677.75))
      .add(t.multiply(-1979.71)).add(371.38);
    a = a.add(corr);
  }
  return a.rename('hue');
}

// Per-image water mask, hue as unit vector (for circular averaging) and NDTI.
function pondFeatures(img) {
  img = addIndices(img);
  var water = img.select('MNDWI').gt(0.1).and(img.select('NDWI').gt(0));
  var h = hueAngle(img).multiply(Math.PI / 180);
  var feats = ee.Image.cat([h.cos().rename('hc'), h.sin().rename('hs'), img.select('NDTI')])
    .updateMask(water);
  return ee.Image(feats.addBands(water.rename('w'))
    .copyProperties(img, ['system:time_start']));
}
function circularMeanHue(col) {
  var m = col.select(['hc', 'hs']).mean();
  return m.select('hs').atan2(m.select('hc')).multiply(180 / Math.PI).add(360).mod(360)
    .rename('hue');
}
var srBase = s2('COPERNICUS/S2_SR_HARMONIZED', CFG.pondBaseStart, CFG.pondBaseEnd).map(pondFeatures);
var srRecent = s2('COPERNICUS/S2_SR_HARMONIZED', CFG.recentStart, CFG.studyEnd).map(pondFeatures);
var hueBase = circularMeanHue(srBase);
var hueRecent = circularMeanHue(srRecent);
var wfBase = srBase.select('w').mean();
var wfRecent = srRecent.select('w').mean();

// Small, non-permanent water bodies (ponds, borrow pits) on a fixed 10 m grid.
var pondWater = wfRecent.gt(0.3).and(permWater.not()).selfMask()
  .reproject({crs: CFG.crs, scale: 10});
var pondSize = pondWater.connectedPixelCount({maxSize: 600, eightConnected: true});
var pondMask = pondWater.updateMask(pondSize.lte(CFG.pondMaxAreaM2 / 100));

// Population statistics of recent pond hue across the AOI (robust z-score).
var hueStats = hueRecent.updateMask(pondMask).reduceRegion({
  reducer: ee.Reducer.percentile([25, 50, 75]), geometry: aoi, scale: 20,
  maxPixels: 1e10, tileScale: 4, bestEffort: true});
var hueMed = ee.Number(hueStats.get('hue_p50'));
var hueSigma = ee.Number(hueStats.get('hue_p75')).subtract(hueStats.get('hue_p25'))
  .divide(1.349).max(1);
var hueZ = hueRecent.subtract(hueMed).divide(hueSigma).abs().rename('hue_z_abs');
var hueShift = hueRecent.subtract(hueBase).add(540).mod(360).subtract(180).abs()
  .rename('hue_shift_abs');                                   // circular difference
var ndtiShift = srRecent.select('NDTI').median().subtract(srBase.select('NDTI').median())
  .rename('ndti_shift');
var pondAnom = hueShift.gt(CFG.hueShiftMinDeg).unmask(0)
  .or(hueZ.gt(CFG.hueZmin).unmask(0)).or(ndtiShift.gt(CFG.ndtiShiftMin).unmask(0))
  .updateMask(pondMask).rename('pond_anom');
var newPond = wfRecent.gt(0.3).and(wfBase.unmask(0).lt(0.05)).unmask(0).rename('new_pond');
var pondStack = ee.Image.cat([pondAnom, hueShift.updateMask(pondMask),
  hueZ.updateMask(pondMask), ndtiShift.updateMask(pondMask), newPond]);
var pondReducer = ee.Reducer.mean()
  .combine({reducer2: ee.Reducer.max(), sharedInputs: true})
  .combine({reducer2: ee.Reducer.count(), sharedInputs: true});
sites = reduceOnBuffer(sites, pondStack, pondReducer, 10, CFG.pondRadiusM);

// ========================= FLOOD CONNECTIVITY (S1) ===========================
var floodFreq = s1(CFG.studyStart, CFG.studyEnd)
  .filter(ee.Filter.calendarRange(CFG.floodMonths[0], CFG.floodMonths[1], 'month'))
  .map(function (img) {
    return img.focalMedian({radius: 30, kernelType: 'circle', units: 'meters'})
      .lt(CFG.floodVVmaxDb).rename('flood');
  })
  .mean().updateMask(permWater.not()).rename('flood_freq');
sites = reduceOnBuffer(sites, floodFreq,
  ee.Reducer.max().setOutputs(['flood_freq_max']), 20, 300);

// ================================== SCORING ==================================
function tag(score, name) {
  return ee.String(ee.Algorithms.If(ee.Number(score).gte(0.5), name + ';', ''));
}
var candidates = sites.map(function (f) {
  var sStruct = clamp01(ee.Number(0.5).add(num(f, 'dVV', 0).max(0).divide(12))
    .add(num(f, 'dNDBI', 0).max(0)));
  var sThermal = clamp01(num(f, 'viirs_dates_off', 0).divide(3)
    .max(num(f, 'lst_hot_freq', 0).divide(0.2))
    .max(num(f, 'viirs_static_n', 0).gt(0).multiply(0.5)));
  var settleFrac = num(f, 'settle_frac_1km', 0);
  var sNtl = clamp01(num(f, 'ntl_surge', 0).multiply(
    ee.Number(ee.Algorithms.If(settleFrac.lt(CFG.settlementMaxFrac), 1, 0.6))));
  var pondN = num(f, 'pond_anom_count', 0);
  var sPond = clamp01(ee.Number(ee.Algorithms.If(pondN.gte(4),
      num(f, 'pond_anom_mean', 0).divide(0.2), 0))
    .max(num(f, 'new_pond_max', 0).multiply(0.5)));
  var w = CFG.weights;
  var score = sStruct.multiply(w.struct).add(sThermal.multiply(w.thermal))
    .add(sNtl.multiply(w.ntl)).add(sPond.multiply(w.pond));
  var activity = clamp01(sThermal.multiply(0.5).add(sNtl.multiply(0.3))
    .add(sPond.multiply(0.2))).max(0.1);
  var nProx = sStruct.gte(0.5).add(sThermal.gte(0.5)).add(sNtl.gte(0.5)).add(sPond.gte(0.5));
  return f.set({
    s_struct: sStruct, s_thermal: sThermal, s_ntl: sNtl, s_pond: sPond,
    screening_score: score, activity_index: activity, n_proxies: nProx,
    proxies: tag(sStruct, 'struct').cat(tag(sThermal, 'thermal'))
      .cat(tag(sNtl, 'ntl_surge')).cat(tag(sPond, 'pond_colour'))
  });
}).filter(ee.Filter.or(ee.Filter.gte('screening_score', CFG.minExportScore),
                        ee.Filter.gte('n_proxies', 2)));

// ================================== EXPORTS ==================================
var SELECT = ['site_id', 'lon', 'lat', 'area_m2', 'screening_score', 'activity_index',
  'n_proxies', 'proxies', 's_struct', 's_thermal', 's_ntl', 's_pond', 'first_built_year',
  'dVV', 'dNDBI', 'dNDVI', 'built_recent', 'bare_recent',
  'viirs_n_all', 'viirs_dates_all', 'viirs_dates_off', 'viirs_static_n',
  'lst_hot_freq', 'lst_hot_n',
  'ntl_ratio_2018', 'ntl_delta_2018', 'ntl_ratio_2025', 'ntl_delta_2025', 'ntl_surge',
  'settle_frac_1km', 'pond_anom_mean', 'pond_anom_count', 'hue_shift_abs_max',
  'hue_z_abs_max', 'ndti_shift_max', 'new_pond_max', 'flood_freq_max'];

Export.table.toDrive({collection: candidates, description: CFG.prefix + '_candidates',
  folder: CFG.exportFolder, fileFormat: 'CSV', selectors: SELECT});
Export.table.toDrive({collection: objects, description: CFG.prefix + '_footprints',
  folder: CFG.exportFolder, fileFormat: 'SHP'});
Export.image.toDrive({image: floodFreq.toFloat(), description: CFG.prefix + '_flood_freq',
  folder: CFG.exportFolder, region: aoi, scale: 20, crs: CFG.crs, maxPixels: 1e10});

// ============================ VISUAL QA (optional) ===========================
Map.centerObject(aoi, 9);
Map.addLayer(aoi, {color: 'white'}, 'AOI', false);
Map.addLayer(p1sized, {palette: ['ff7f00']}, 'P1 new structures / piles (0.1-2 ha)');
Map.addLayer(thermalStack.select('lst_hot_freq').clip(aoi),
  {min: 0, max: 0.3, palette: ['000000', 'b2182b', 'fddbc7']}, 'P2 Landsat hot frequency', false);
Map.addLayer(r18.clip(aoi), {min: 1, max: 3, palette: ['000000', 'ffd92f', 'ffffff']},
  'P3 NTL ratio 2019-21 / 2016-17', false);
Map.addLayer(pondAnom, {min: 0, max: 1, palette: ['2c7fb8', 'e7298a']},
  'P4 pond colour anomaly', false);
Map.addLayer(floodFreq.clip(aoi), {min: 0, max: 0.5, palette: ['ffffff', '08519c']},
  'Wet-season flood frequency', false);
Map.addLayer(candidates.filter(ee.Filter.gte('screening_score', 0.6)), {color: 'ff00ff'},
  'Candidates (score >= 0.6, slow)', false);

if (CFG.debugPrints) {
  print('Objects (0.1-2 ha):', objects.size());
  print('Exported candidates:', candidates.size());
  print('Pond hue population stats:', hueStats);
}
print('Start the three export tasks in the Tasks tab. Results are candidates, not findings.');
