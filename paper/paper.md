---
title: "From Space to Sediment"
subtitle: "An Integrated Multi-Sensor Remote Sensing and Geochemical Fingerprinting Framework for Detecting E-Waste Hotspots and Attributing River Contamination in Thailand"
author: "Thanatchon Chongmankhong"
date: "November 2026"
keywords:
  - electronic waste
  - remote sensing
  - multi-sensor fusion
  - source apportionment
  - lead isotopes
  - spatial stream networks
  - Basel Convention
  - Thailand
abstract: |
  Informal processing and dumping of electronic waste (e-waste) release trace metals and persistent organic pollutants into soils, air and rivers. In Thailand, enforcement since 2018 has repeatedly uncovered unlicensed processing facilities in the eastern provinces, and household-scale dismantling persists in the Northeast, yet no systematic national inventory of such sites exists, their response to trade-policy shocks has not been quantified, and the contribution of individual sites to downstream river contamination has not been established. Satellites cannot observe e-waste directly and the contaminants of concern are not optically active, so neither remote sensing nor field sampling alone can close this gap. We present *From Space to Sediment*, a framework that couples three modules. Module 1 detects candidate processing and dumping sites nationwide from thermal, optical, synthetic aperture radar, night-time light and imaging-spectroscopy proxies, using positive--unlabelled learning, calibrated site probabilities, design-based accuracy assessment and a gap analysis against the national factory registry. Module 2 dates the emergence of sites and estimates their displacement around China's 2018 waste-import ban and the 2025 entry into force of the Basel Convention e-waste amendments, using heterogeneity-robust event-study designs. Module 3 attributes river contamination in the Bang Pakong basin by combining spatial stream-network models, an e-waste-specific geochemical marker suite, lead-isotope mixing models and ^210^Pb-dated sediment cores. A site is reported as an attributed source only when four independent lines of evidence converge: detection, hydrological connectivity, geochemical consistency and chronological agreement. An open implementation computed exact along-network distances on the real Bang Pakong river network, and in {{sim:simRepsTotal}} simulated scenarios the attributed level reached a precision of {{sim:rngPrecAttributed}}; the simulations also showed that a count-based rule was too permissive, so geochemical evidence is now required for a probable attribution. We specify data, sampling designs, hypotheses, identification assumptions and legal safeguards, including the reporting of candidate sites rather than allegations. Empirical results on real data will be reported separately.
---

<!-- Source of the paper. `make paper` fills the {{...}} placeholders (numbers from
     results/sim_out/paper_numbers.json, tables from paper/tables/) and builds paper.tex and paper.pdf
     with pandoc + tectonic; `make web` builds the web reader docs/paper/ from the same text.
     Cross-references are written as \cref{label}; citations as [@key]. -->

# Introduction {#sec:intro}

The world generated an estimated 62 million tonnes of electronic waste (e-waste) in 2022, of which only 22.3% was documented as formally collected and recycled [@balde2024]. The remainder is stored, landfilled, traded or processed informally, typically through manual dismantling, open burning of cables and casings, heating and acid leaching of printed circuit boards, and crude smelting [@robinson2009; @wong2007]. These practices release lead (Pb), cadmium (Cd), copper (Cu), antimony (Sb) and other metals, together with brominated flame retardants and dioxin-like compounds, into air, dust, soils and surface waters, with documented consequences for human health [@leung2008; @grant2013].

The geography of informal processing is not static. Trade in electronic discards responds to regulation, prices and enforcement [@lepawsky2015], and China's 2018 restrictions on imports of solid waste redirected large volumes of scrap towards Southeast Asia [@brooks2018]. In Thailand, enforcement actions from 2018 onwards uncovered recycling facilities processing imported e-waste in the eastern provinces, while household-scale dismantling in the Northeast predates these shocks and is supplied largely through domestic collection [@puangprasert2019]. Exposure studies have documented brominated flame retardants at Thai e-waste storage facilities [@muenhor2010], but the spatial extent of processing and its consequences for river systems remain poorly characterised.

Three gaps motivate this work. First, there is no national inventory: enforcement is largely reactive and complaint-driven, so known sites form a biased sample of the true distribution. Second, the dynamics are unknown: it is unclear whether policy shocks reduced processing or displaced it to new districts, a question analogous to the pollution-haven hypothesis in the trade-and-environment literature [@copeland2004]. Third, attribution is weak: metals in rivers have many sources, tidal rivers mix bidirectionally, and existing studies typically report concentrations near suspected sites without quantitatively linking them to upstream sources.

Remote sensing and field geochemistry have complementary blind spots. Satellites observe proxies of activity---heat, new structures, material piles, night-time lighting and water-colour anomalies---but not e-waste itself, and the contaminants of concern are not optically active. Field geochemistry measures contaminants precisely but at few locations, and without a source inventory it cannot establish where contamination originates. Linking the two requires an explicit chain of evidence from orbit to sediment. This paper proposes such a chain. Its contributions are:

1. an integrated framework linking national-scale satellite detection, policy-driven dynamics and river source attribution (\cref{fig:framework});
2. an observation model that maps processing activities to remotely sensed proxies, sensors and confounders (\cref{tab:obsmodel,fig:sensors});
3. a quasi-experimental design for estimating the emergence and displacement of processing sites around trade-policy shocks (\cref{fig:timeline});
4. a four-criterion rule that reports a site as a contamination source only when detection, hydrological connectivity, geochemistry and chronology agree (\cref{fig:attribution});
5. a protocol of legal, ethical and safety safeguards for mapping suspected illegal activity; and
6. an open implementation, checked on the real Bang Pakong river network and evaluated in simulations that led to a stricter evidence rule (\cref{sec:validation}).

\noindent \Cref{sec:background} reviews the background and \cref{sec:study} describes the study area. \Cref{sec:framework} introduces the framework, \cref{sec:m1,sec:m2,sec:m3} detail its three modules, \cref{sec:synthesis} describes evidence synthesis and \cref{sec:validation} reports the implementation and its validation. \Cref{sec:ethics} sets out safeguards, \cref{sec:discussion} discusses expected contributions and limitations, and \cref{sec:plan} presents the work plan. The framework and analysis plan are specified in advance; empirical results will be reported in companion studies.

# Background {#sec:background}

## Environmental signatures of informal processing

Informal e-waste processing combines activities with distinct footprints. Manual dismantling and sorting take place in roofed sheds or open yards and produce piles of casings, cables and boards. Cable insulation and plastics are burned to recover copper, generating brief, small fires and dense smoke. Printed circuit boards are heated to remove components or leached with acids to recover precious metals, producing acidic, metal-rich effluents. Residues are stockpiled, buried, or dumped into ponds and abandoned excavation pits. These activities leave potentially observable traces---thermal anomalies, changes in roofs and bare surfaces, heterogeneous material spectra, persistent night-time lighting and anomalous colour in small water bodies---but none of these traces is unique to e-waste. The framework therefore treats detection as probabilistic and evidence-based rather than as direct identification.

## Remote sensing of waste sites

Deep learning applied to satellite and aerial imagery now supports the detection of landfills and dumpsites at regional to global scales [@sun2023; @torres2023], and Sentinel-2 time series have been used to monitor terrestrial plastic-waste sites [@kruse2023]. These studies target large, persistent waste bodies. Informal e-waste processing differs: individual sites are often smaller than a hectare, partly roofed and intermittently active. Thermal detection is also challenging. The VIIRS 375 m active-fire product detects smaller fires than earlier 1 km products [@schroeder2014], and Landsat-8 OLI supports active-fire detection at 30 m [@schroeder2016], but brief cable fires remain close to detection limits, and dry-season agricultural burning in Thailand produces a large background of genuine fire detections. Plastics have diagnostic short-wave infrared absorption features [@garaba2018] that spaceborne imaging spectrometers such as EnMAP and PRISMA can in principle resolve [@guanter2015; @cogliati2021], although a typical processing yard is spectrally mixed within a 30 m pixel. Colour anomalies of small water bodies can be quantified with the Forel--Ule scale and hue angle [@vanderwoerd2015].

## Source attribution of trace contaminants in rivers

Receptor models such as positive matrix factorisation (PMF) resolve measured concentrations into source profiles and contributions [@paatero1994; @norris2014], and Bayesian mixing models estimate source proportions from tracers with explicit uncertainty [@stock2018]. Lead isotope ratios are among the most informative tracers because geogenic, industrial and gasoline-derived lead often carry distinct signatures [@komarek2008]. Spatial stream-network (SSN) models represent dependence along flow-connected and flow-unconnected paths in river networks [@verhoef2010; @peterson2013] and are implemented in open software [@dumelle2024]. Dated sediment cores reconstruct contamination histories, typically using ^210^Pb chronologies [@appleby1978]. In estuaries, salinity alters trace-metal partitioning, for example by promoting Cd desorption through chloride complexation [@dulaing2009].

## The Thai context

Thailand regulates factories under the Factory Act B.E. 2535 (1992). Waste-sorting and recycling facilities are licensed in dedicated factory categories (notably categories 105 and 106), and the resulting registry provides a reference for distinguishing licensed from unlicensed activity. The Pollution Control Department monitors surface-water quality in major rivers. The eastern provinces, including those of the Eastern Economic Corridor, combine dense industrial land use, port access through Laem Chabang and repeated reports of unlicensed processing, whereas the Northeast hosts village-scale dismantling linked to domestic collection networks. Monsoon cloud cover, roughly from May to October, limits optical observation, and dry-season agricultural burning, roughly from December to April, dominates thermal anomalies. Internationally, amendments to the Basel Convention adopted in 2022 extended prior-informed-consent controls to all e-waste from 1 January 2025 [@basel2022], and the 2022 edition of the Harmonized System introduced heading 8549 for electrical and electronic waste and scrap, which improves the traceability of trade statistics.

# Study area {#sec:study}

The national domain covers Thailand's 77 provinces (about 513,000 km^2^). Two case regions represent contrasting modes of processing (\cref{fig:study}). The eastern case region is the Bang Pakong river system, formed by the confluence of the Prachin Buri and Nakhon Nayok rivers and discharging to the upper Gulf of Thailand. In the HydroRIVERS network [@lehner2013], the basin drains about 22,000 km^2^ at its outlet, with a modelled long-term mean discharge of about 480 m^3^ s^$-1$^. Its lower reach is tidal and subject to saline intrusion in the dry season, and its floodplain is flood-prone. The basin spans Prachin Buri and Chachoengsao, two provinces with repeated reports of industrial-scale processing. The northeastern case region spans the Chi and Mun basins, where household-scale dismantling and open burning have been reported in Kalasin and Buri Ram. Rayong, in the East Coast basin, provides a hazardous industrial-waste context that is useful for testing the specificity of detection (\cref{tab:seeds}).

![Study context. (a) Thailand, with provinces where industrial-scale e-waste processing or related enforcement (East) and household-scale dismantling and open burning (Northeast) have been publicly reported. Markers show example districts used as seed localities, boxes show the extents of panels b and c, and the inset locates Thailand in Southeast Asia. (b) Eastern case region with the Bang Pakong river system (dark blue), the proposed case basin for Module 3. (c) Northeastern case region in the Chi and Mun basins. Hatched polygons are example districts shown at district level only; they are not findings about any facility or community, and province categories will be re-verified against primary records. Projection: Albers equal-area conic (standard parallels 8°N and 18°N, central meridian 101°E). Data: Natural Earth [@naturalearth]; HydroRIVERS v1.0 [@lehner2013]; OpenGISData-Thailand [@opengis].](figures/fig1_study_area.pdf){#fig:study width=100% latex-placement=p}

{{include:tables/tab_seeds.tex}}

# Framework overview {#sec:framework}

The framework (\cref{fig:framework}) follows five design principles.

(1) *Proxy-based detection with an explicit observation model.* Each sensor is used for a stated proxy with stated confounders (\cref{tab:obsmodel}).
(2) *Convergence of independent evidence.* No single line of evidence suffices to attribute contamination to a site.
(3) *Temporal consistency.* Causes must precede effects, so satellite-derived emergence dates constrain admissible sources.
(4) *Uncertainty propagation.* Detection probabilities, model uncertainty and analytical uncertainty are carried through to attribution.
(5) *Safeguards by design.* Outputs are probabilistic candidates, published at aggregated resolution.

\noindent Module 1 produces a candidate-site inventory $\mathcal{S}=\{(\mathbf{s}_i,p_i,t_i,a_i)\}$, where $\mathbf{s}_i$ is the location of site $i$, $p_i$ the calibrated probability that it hosts e-waste processing or dumping, $t_i$ its emergence date and $a_i$ an activity index. Module 2 uses $\mathcal{S}$ to analyse dynamics, Module 3 uses it as the source inventory for attribution, and a synthesis step combines the evidence (\cref{sec:synthesis}).

![The *From Space to Sediment* framework. Earth-observation proxies feed Module 1, which produces a candidate-site inventory with calibrated probabilities $p_i$, emergence dates $t_i$ and activity indices $a_i$. Module 2 analyses the dynamics of the inventory around policy shocks, and Module 3 uses it as the source inventory for river attribution. Evidence is combined by a four-criterion rule, and outputs are subject to the safeguards in \cref{sec:ethics}.](figures/fig2_framework.pdf){#fig:framework width=100% latex-placement=t}

{{include:tables/tab_obsmodel.tex}}

# Module 1: detection and national inventory {#sec:m1}

## Data and features

Module 1 draws on the sensor portfolio in \cref{fig:sensors}. Sentinel-2 [@drusch2012] and Sentinel-1 [@torres2012] form the national backbone at 10--20 m resolution. Thermal products from VIIRS, Landsat 8/9, ECOSTRESS and SDGSAT-1 provide evidence of burning and hot targets [@schroeder2014; @schroeder2016; @fisher2020; @guo2023]; VIIRS Black Marble [@roman2018] and SDGSAT-1 Glimmer capture night-time activity; and the Landsat archive [@masek2020] extends change histories. PlanetScope, THEOS-2 and commercial very-high-resolution (VHR) imagery are used for verification rather than wall-to-wall mapping. Features are computed per 10 m pixel and aggregated to candidate objects. They include seasonal spectral composites and indices, SAR backscatter statistics and interferometric coherence change [@preiss2006], the recurrence and timing of thermal anomalies, night-time radiance trends and texture measures. Embeddings from geospatial foundation models, such as AlphaEarth Foundations [@brown2025] and Prithvi-EO-2.0 [@szwarcman2024], are evaluated as additional features because they can reduce the number of labels required. Processing is implemented in Google Earth Engine [@gorelick2017] and open-source Python.

![Sensor portfolio. Filled circles mark a primary role and open circles a supporting role for each proxy: open burning and hot targets; structures and waste piles; all-weather surface change; night-time activity; material identification; smoke and trace gases; water colour and turbidity; and hydrological connectivity. Bars show nominal spatial resolution, with ranges where modes or bands differ. Revisit values are nominal and vary with acquisition planning, latitude and cloud cover.](figures/fig3_sensor_portfolio.pdf){#fig:sensors width=100% latex-placement=t}

## Reference data and labelling

Positive examples are compiled from enforcement records, NGO and media reports, VHR photo-interpretation and field verification. Because these sources over-represent sites that attracted complaints or enforcement, labelled positives are a biased sample, and unlabelled locations cannot be assumed negative. We therefore treat detection as a positive--unlabelled (PU) learning problem [@bekker2020]. Hard negatives are sampled explicitly from licensed recyclers in the factory registry, industrial estates, agro-industrial facilities such as rice and sugar mills, construction sites and landfills. Each label records its source, date and confidence, and an active-learning loop directs VHR interpretation towards uncertain candidates.

## Models

Detection proceeds in two stages. A national screening stage applies pixel-level segmentation---a U-Net-type network [@ronneberger2015] and gradient-boosted trees on embedding features---to produce a candidate surface, with a focal loss to address extreme class imbalance [@lin2017]. A site-level stage aggregates evidence for each candidate object, including thermal recurrence and night-time activity, and outputs a probability calibrated by isotonic regression [@niculescu2005]. Model selection and error estimation use spatial block cross-validation to avoid optimistic bias from spatial autocorrelation [@roberts2017].

## Accuracy assessment and inventory estimation

Accuracy is estimated by design-based inference from a stratified random sample of map units, interpreted on VHR imagery and verified in the field where feasible [@olofsson2014]. Strata are defined by predicted probability and region. We report user's and producer's accuracies with confidence intervals and estimate the number and area of sites per province with design-based uncertainty, rather than counting map detections.

## Registry gap analysis

Candidates are matched to registered facilities in factory categories 101, 105 and 106 within a spatial tolerance that accounts for geocoding error. The share of high-probability candidates without a registry match, and its geography, are key outputs. Matching results are published only at aggregated resolution (\cref{sec:ethics}).

# Module 2: dynamics and policy displacement {#sec:m2}

## Emergence dating and activity indices

For each candidate site, the emergence date $t_i$ is estimated from dense time series with continuous change detection [@zhu2014], applied to Landsat and Sentinel-2 reflectance and Sentinel-1 backscatter. An annual activity index $a_{it}$ combines thermal recurrence, night-time radiance and roof-area change, standardised within region.

![Policy shocks and Earth-observation capability, 2015--2026. The upper track shows international and national events that define the event-study periods of Module 2 (bottom strip); the lower track shows launches of satellites in the portfolio of \cref{fig:sensors}. The shaded band marks renewed enforcement campaigns reported in the eastern provinces. Event dates are compiled from public sources and will be verified against primary documents.](figures/fig4_timeline.pdf){#fig:timeline width=100% latex-placement=t}

## Identification strategy

Outcomes are aggregated to district--year panels: the number of active sites, new emergences and total activity. Because the policy shocks in \cref{fig:timeline} are common in time, identification relies on differential exposure defined by predetermined characteristics: travel time to Laem Chabang and other gateways, the pre-2018 presence of licensed recyclers and the pre-period industrial land share. The event-study specification is
\begin{equation}
Y_{dt}=\alpha_d+\delta_{r(d)t}+\sum_{k\neq-1}\beta_k\,E_d\,\mathbf{1}[t-T=k]+\mathbf{x}_{dt}^{\top}\bm{\gamma}+\varepsilon_{dt},
\label{eq:es}
\end{equation}
where $Y_{dt}$ is the outcome in district $d$ and year $t$, $\alpha_d$ are district fixed effects, $\delta_{r(d)t}$ are region-by-year effects, $E_d$ is exposure, $T$ is the shock year and $\beta_k$ trace dynamic effects relative to the year before the shock. Pre-period coefficients ($k<-1$) test for differential pre-trends. Where treatment is staggered, as with district-level enforcement episodes, we use estimators that are robust to heterogeneous effects [@callaway2021; @sun2021] and avoid two-way fixed-effects comparisons that use already-treated units as controls [@goodmanbacon2021].

## Displacement

Enforcement in one district may push activity into neighbouring districts, which violates the assumption of no interference between units. Rather than treating this as a nuisance, we estimate spillovers explicitly with rings of neighbouring districts around enforced districts, following designs used for pollution spillovers across jurisdictions [@lipscomb2017]. Net effects are reported as the sum of direct and spillover estimates.

## Trade linkage

Annual imports and exports of e-waste and related scrap are compiled from UN Comtrade, using mirror statistics and HS heading 8549 from 2022 onwards with predecessor codes before then, to test whether changes at import-dependent sites track trade flows.

# Module 3: river source attribution in the Bang Pakong basin {#sec:m3}

## Hydrological network

Flow routing is derived from MERIT Hydro [@yamazaki2019] and FABDEM [@hawker2022] and cross-checked against HydroRIVERS [@lehner2013]. Because DEM-based routing misrepresents canals and pumping in flat floodplains, the network is corrected with irrigation-canal data and field reconnaissance. Each candidate site is linked to its receiving reach, and along-network distances to downstream monitoring points are computed. Sentinel-1 flood maps [@twele2016] identify events that connect otherwise isolated sites to the channel network, and SWOT observations [@biancamaria2016] provide water-surface elevation context for the lower reach.

## Sampling design

Sampling follows a paired upstream--downstream design around candidate sites, with reference stations in tributaries without candidates (\cref{fig:attribution}a). Paired upstream--downstream comparisons are an established design for isolating point-source effects in rivers [@keiser2019]. Surface water (dissolved and particulate fractions), suspended sediment and bed sediment are collected in the dry season, the wet season and after flood pulses. Sediment cores are taken from depositional settings with undisturbed accumulation, such as floodplain ponds and oxbows, rather than from the tidal channel, where resuspension blurs chronologies. Salinity is measured with every sample.

![Schematic of the Module 3 attribution design (illustrative; not data). (a) Paired upstream (U) and downstream (D) stations around candidate sites (S), a reference station (R) in a tributary without candidates, a sediment core (C) in a floodplain pond, a flood-connected area and the tidal limit. (b) Lead-isotope mixing space with geogenic, legacy-gasoline and e-waste end members; downstream samples shift towards the e-waste end member. (c) Expected core chronology, in which marker enrichment begins after the satellite-derived emergence date $t_i$ of upstream candidates.](figures/fig5_attribution_schematic.pdf){#fig:attribution width=100% latex-placement=t}

## Analytes and marker suite

The marker suite (\cref{tab:markers}) combines metals that are abundant in e-waste with organic compounds that are specific to it. Because each metal also has non-e-waste sources, attribution relies on ratios and combinations---for example, covarying Pb and Sn from solder together with polybrominated diphenyl ethers (PBDEs) from flame-retarded plastics---rather than on single elements.

{{include:tables/tab_markers.tex}}

## Statistical attribution

For monitoring point $j$, an upstream e-waste loading index is defined as
\begin{equation}
L_j=\sum_{i\in\mathcal{U}(j)}p_i\,a_i\,\exp\!\left(-\frac{d_{ij}}{\lambda}\right),
\label{eq:load}
\end{equation}
where $\mathcal{U}(j)$ is the set of candidate sites hydrologically upstream of $j$, $d_{ij}$ is the along-network distance and $\lambda$ is a decay length estimated from the data. Concentrations or marker ratios $y_j$ are modelled with an SSN model,
\begin{equation}
y_j=\mathbf{x}_j^{\top}\bm{\beta}+\theta L_j+z_{\mathrm{TU}}(j)+z_{\mathrm{TD}}(j)+\varepsilon_j,
\label{eq:ssn}
\end{equation}
where $\mathbf{x}_j$ are covariates (land use, licensed facilities and wastewater treatment), $z_{\mathrm{TU}}$ and $z_{\mathrm{TD}}$ are tail-up and tail-down spatial random effects [@verhoef2010], and $\theta>0$ indicates an e-waste signal beyond other sources. Uncertainty in $p_i$, $a_i$ and $\lambda$ is propagated by Monte Carlo sampling. Source proportions at each station are estimated with Bayesian mixing models of Pb isotope ratios and marker ratios [@stock2018],
\begin{equation}
\bm{\delta}_j=\sum_{s}f_{js}\,\bm{\mu}_s+\bm{\epsilon}_j,\qquad\sum_s f_{js}=1,\quad f_{js}\ge 0,
\label{eq:mix}
\end{equation}
with end members $\bm{\mu}_s$ for geogenic background, legacy gasoline lead and e-waste materials characterised from local samples (\cref{fig:attribution}b). PMF [@paatero1994; @norris2014] provides an independent, data-driven decomposition.

## Chronology

Core chronologies use the constant-rate-of-supply model for ^210^Pb [@appleby1978], validated with ^137^Cs. The onset of marker enrichment is compared with the satellite-derived emergence dates of upstream candidates (\cref{fig:attribution}c). Agreement within dating uncertainty supports attribution, whereas enrichment that predates all upstream emergences points to other or legacy sources. Because leaded gasoline was phased out in Thailand in the mid-1990s, legacy lead must be separated isotopically from recent inputs.

## The tidal reach

Bidirectional flow in the tidal reach violates the directional assumptions of tail-up models. The tidal reach is therefore analysed separately, using salinity-normalised concentrations and, where needed, hydrodynamic modelling, and the SSN model is restricted to non-tidal reaches. Salinity-dependent partitioning [@dulaing2009] is modelled explicitly rather than ignored.

# Evidence synthesis {#sec:synthesis}

For each candidate site $i$ and receiving reach, four criteria are evaluated:

C1 Detection:
:   $p_i\ge\tau$, with the threshold $\tau$ chosen from the design-based accuracy assessment;

C2 Connectivity:
:   a hydrological path links the site to the reach under base-flow or documented flood conditions;

C3 Geochemical consistency:
:   downstream samples shift towards the e-waste end member relative to paired upstream samples;

C4 Chronology:
:   the onset of marker enrichment in dated sediments follows $t_i$ within dating uncertainty.

\noindent A site is reported as an *attributed* source when all four criteria hold and as a *probable* source when detection, connectivity and geochemistry hold (C1--C3); a site meeting any two criteria is a *possible* source, and otherwise it remains a candidate. This rule replaces an earlier count-based rule, under which any three criteria sufficed for the probable level, because the simulations in \cref{sec:validation} showed that rule to be too permissive. \Cref{tab:hypotheses} lists the hypotheses tested in each module and the evidence used.

{{include:tables/tab_hypotheses.tex}}

# Implementation and simulation-based validation {#sec:validation}

## Software

The framework is implemented in two open programs (see Data and code availability). A Google Earth Engine script screens candidate sites with the four proxies of \cref{tab:obsmodel} and exports, for each site, a heuristic screening score, an activity index and an emergence date, together with a wet-season flood-frequency layer from Sentinel-1. A Python program then performs the registry gap analysis, known-site exclusion and hard-negative filtering; snaps sites and stations to a vector river network (HydroRIVERS or MERIT-Basins); computes along-network distances, the loading index of \cref{eq:load} and marker anomalies; selects $\lambda$ by rank association with a permutation test; and evaluates criteria C1--C4. The screening script has been checked statically and executed against a mock of the Earth Engine API that covers every configuration branch, but it has not yet been run on real imagery. The Python program was tested end to end on synthetic inputs and on the real network described next.

## Network checks on the Bang Pakong river system

We applied the network module to the Bang Pakong system in HydroRIVERS v1.0 [@lehner2013]: {{sim:netReaches}} reaches with a mean discharge of at least 12 m^3^ s^$-1$^, {{sim:netLengthKm}} km of channel and a maximum along-network distance of {{sim:netMaxOutletKm}} km to the outlet (\cref{fig:network}a). The flow orientation inferred from network topology agreed with the digitising direction of the source data for all {{sim:netReaches}} reaches. For {{sim:netPairs}} random pairs of points, along-network distances computed by the pipeline agreed with distances measured along independently merged path lines to within $10^{-9}$ m (\cref{fig:network}b). The public extract used here is geometrically simplified, so its reach lengths are a median {{sim:netShortMed}}% shorter than the HydroRIVERS attribute lengths (5th--95th percentile: {{sim:netShortPfive}}% shorter to {{sim:netLongPninetyfive}}% longer); applications should use full-resolution reaches.

![Network checks on the real Bang Pakong river system (HydroRIVERS v1.0; reaches with a mean discharge of at least 12 m^3^ s^$-1$^). (a) Along-network distance from each reach midpoint to the outlet, computed by the pipeline; line width scales with discharge. (b) Pipeline distances against distances measured along independently merged path lines for {{sim:netPairs}} random point pairs; the dashed line is 1:1.](figures/fig7_network_check.pdf){#fig:network width=100% latex-placement=t}

## Simulation design

To test the statistical components, we generated synthetic worlds on the real network topology; synthetic site locations are not reported. Each replicate placed 60 candidate sites at random positions, 70% within 700 m of a channel and 30% between 700 and 2,500 m away. Each site was a true e-waste source with probability $\pi=0.25$ ($\pi=0$ in a null scenario), and sources were hydrologically connected when within 600 m of a channel or, farther away, with probability 0.3 through flooding. Screening scores were drawn from Beta(5, 2) for sources and Beta(2, 4) for non-sources to mimic imperfect satellite discrimination. Twenty-five stations were placed on the network, and marker concentrations followed
\begin{equation}
C_{jm}=B_m\,e^{\varepsilon_{jm}}\left(1+\kappa_m T_j+\gamma_m K_j\right),\qquad \varepsilon_{jm}\sim\mathcal{N}(0,\,0.25^2),
\label{eq:sim}
\end{equation}
where $T_j=\sum_i A_i\exp(-d_{ij}/\lambda_{\mathrm{true}})$ sums over connected sources, $K_j$ is the corresponding load from three non-e-waste industrial confounders, and the sensitivities $\kappa_m$ and $\gamma_m$ make the confounders raise Cu, Cd, Ni and Zn but not Sn or Sb. Two samples were drawn per station, and reference stations were chosen among stations without upstream loads. Dated cores were simulated at stations with $T_j\geq0.2$, with onsets following the emergence of the dominant source by $0.5\pm1$ years, and at up to three confounder-only stations with legacy onsets between 2005 and 2016. Licensed factories, decoy factories just beyond 500 m, other-category factories, previously reported sites and hard negatives were placed at known distances. Three scenarios ($\lambda_{\mathrm{true}}=3$, 8 and 20 km) and the null scenario were each replicated {{sim:simReps}} times, with 99 permutations per association test.

## Results

Registry, known-site and hard-negative flags matched the geometric truth for every site in all {{sim:simRepsTotal}} replicates ({{sim:flagMismatches}} mismatches). This required replacing polygonal buffers, which slightly under-cover a circle, by exact distance tests: an earlier version misclassified a point lying just inside the 300 m hard-negative radius, and a dedicated test with $2\times10^5$ points concentrated at the boundary found no remaining mismatches.

The selected $\lambda$ was within a factor of 2.5 of the true value in {{sim:lamWithinThree}}%, {{sim:lamWithinEight}}% and {{sim:lamWithinTwenty}}% of replicates for $\lambda_{\mathrm{true}}=3$, 8 and 20 km, with a tendency to select values above the truth (\cref{fig:simulation}a). The association test detected the e-waste signal at $p<0.05$ in {{sim:powerThree}}%, {{sim:powerEight}}% and {{sim:powerTwenty}}% of replicates (\cref{fig:simulation}b). Under the null scenario it rejected in {{sim:typeI}}% of replicates (95% interval {{sim:typeILo}}--{{sim:typeIHi}}%), slightly above the nominal 5%, which is consistent with spatially structured contamination weakening the exchangeability that the permutation test assumes.

For attribution (\cref{fig:simulation}c and \cref{tab:validation}), the original count-based rule was too permissive: sites meeting any three criteria were true sources with a precision of only {{sim:rngPrecCount}}. Requiring geochemical evidence together with detection and connectivity (C1--C3) raised precision to {{sim:rngPrecStrict}}, and the attributed level (C1--C4) reached {{sim:rngPrecAttributed}}, at the cost of recall ({{sim:rngRecStrict}} and {{sim:rngRecAttributed}} of attributable sources). Criterion C3 was met by {{sim:rngCthreeTpr}} of true sources with a downstream station but by only {{sim:rngCthreeFprConf}} of non-sources exposed solely to non-e-waste confounders, which confirms the value of e-waste-specific markers (\cref{fig:simulation}d). Among all non-sources, however, C3 was met by {{sim:rngCthreeFpr}} of sites, rising with $\lambda$, because a site lying between a clean upstream station and a contaminated downstream station inherits the signal of any source between them.

![Simulation-based validation with synthetic sites and stations on the real Bang Pakong network ({{sim:simReps}} replicates per scenario). (a) Selected decay length $\lambda$; triangles mark the grid value closest to each true value. (b) Cumulative distribution of permutation p-values; the dashed line is the null scenario and the dotted line marks $p=0.05$. (c) Precision (filled circles) and recall of attributable sources (open squares) at four evidence thresholds, with 95% Wilson intervals [@wilson1927]. (d) Share of sites meeting criterion C3 among true sources, all non-sources and non-sources exposed only to non-e-waste confounders.](figures/fig8_simulation.pdf){#fig:simulation width=100% latex-placement=t}

{{include:tables/tab_validation.tex}}

## Implications for the analysis plan

Four changes follow. First, the evidence rule in \cref{sec:synthesis} now requires C1--C3 for the probable level. Second, the permutation test is used only for screening and for choosing $\lambda$; inference relies on the SSN model of \cref{eq:ssn}, which represents spatial dependence explicitly. Third, sampling designs should bracket individual candidates, or groups of candidates within one sub-catchment, with paired stations, because C3 cannot separate several candidates that lie between the same pair of stations. Fourth, recall is bounded by station density: only {{sim:attribShareThree}}%, {{sim:attribShareEight}}% and {{sim:attribShareTwenty}}% of true connected sources had a station within $3\lambda_{\mathrm{true}}$ downstream in the three scenarios, so station placement should be optimised against the candidate inventory before fieldwork.

# Ethical, legal and safety safeguards {#sec:ethics}

Mapping suspected illegal activity carries risks for communities, operators and researchers. Outputs are therefore described as candidate sites with calibrated probabilities, never as findings of illegality, and individual facilities are not named. Public products are aggregated to districts or 1 km grids; exact coordinates are shared only with competent authorities, such as the Department of Industrial Works and the Pollution Control Department, under data-sharing agreements. Thailand's criminal defamation provisions have been used against researchers and activists, which reinforces the need for verification before any site-specific statement. Fieldwork is conducted on public land or with permission, in teams and in coordination with local authorities, and no attempt is made to enter facilities. Interviews or surveys, if any, require approval by an institutional ethics committee. Communities near processing sites, including households that depend economically on dismantling, are engaged and receive results in accessible form, and publications avoid stigmatising named villages. Code is released openly; sensitive coordinates are not.

# Expected contributions and limitations {#sec:discussion}

The framework is expected to deliver (i) the first design-based national estimate of e-waste processing and dumping sites in Thailand, with uncertainty; (ii) causal evidence on whether policy shocks reduce or displace processing; and (iii) a transferable chain of attribution from orbit to sediment.

Several limitations are anticipated. Persistent monsoon cloud cover reduces optical availability; SAR and thermal data mitigate but do not remove this gap. Most sites are smaller than a 30 m imaging-spectroscopy pixel, so material identification will be possible only for larger yards and stockpiles. Labels are biased towards sites that attracted complaints or enforcement; PU learning mitigates this bias but cannot fully correct it. Exposure-based identification assumes parallel trends conditional on fixed effects; pre-period coefficients test this assumption but cannot prove it. Legacy contamination and other industries may produce similar marker patterns, and mixing models can be non-unique when end members overlap; the four-criterion rule is designed to make such ambiguity explicit rather than to conceal it. Finally, the inventory captures detectable activity only. Operators adapt, and publication of results may itself change behaviour, which argues for repeated mapping rather than a single snapshot. The simulations in \cref{sec:validation} quantify how station density and nested candidates limit attribution.

# Work plan {#sec:plan}

The work is planned over 36 months (\cref{fig:gantt}). Modules 1 and 2 rely on open satellite archives and can begin immediately. Field campaigns for Module 3 are scheduled across two dry seasons and one wet season to capture hydrological contrasts, with laboratory analyses following each campaign. Each module concludes with a manuscript, so that the three papers can be read independently and together.

![Indicative 36-month work plan. Diamonds mark manuscript submissions for Papers 1--3; field campaigns are aligned with dry and wet seasons.](figures/fig6_workplan.pdf){#fig:gantt width=100% latex-placement=t}

# Conclusion {#sec:conclusion}

E-waste processing in Thailand leaves traces that satellites can detect and contaminants that only field geochemistry can measure. *From Space to Sediment* links the two through a national candidate inventory, a quasi-experimental analysis of how processing responds to policy, and an attribution rule that requires detection, connectivity, geochemistry and chronology to agree before a site is reported as a source. An open implementation computes along-network distances exactly on the real Bang Pakong network, and simulations showed that requiring geochemical evidence keeps the precision of probable and attributed sources at {{sim:rngPrecStrict}} and {{sim:rngPrecAttributed}}, whereas recall depends mainly on the density of sampling stations. By specifying data, designs, hypotheses and safeguards in advance, the framework is intended to make the resulting evidence credible to scientists, regulators and affected communities, and to be transferable to other countries in Southeast Asia that face similar pressures.

# Data and code availability {-}

All satellite data described here are openly available or obtainable through research-access programmes. The maps in \cref{fig:study} use Natural Earth boundaries and coastlines [@naturalearth], HydroRIVERS v1.0 reaches with a mean discharge of at least 12 m^3^ s^$-1$^ [@lehner2013], taken from a public extract for mainland Southeast Asia [@waterways], and district boundaries from the OpenGISData-Thailand repository [@opengis]. The Earth Engine screening script, the verification and attribution program, the simulation code and the scripts that reproduce all figures are provided as ancillary files with this preprint.

# Use of AI tools {-}

Drafting of the text and preparation of the figures were assisted by an AI system (Claude, Anthropic). The author reviewed all content and takes full responsibility for it.

