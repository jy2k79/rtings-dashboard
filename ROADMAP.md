# TV Dashboard Roadmap

## Backlog

### 1. SPD image cache staleness detection
**Priority: Medium | Effort: Low**

Basic `actions/cache` for `spd_images/` is implemented. Scraper skips existing files. Remaining work:

**Plan:**
- Add HTTP `HEAD` requests to compare `Content-Length` with cached file size
- Only re-download images whose size changed (catches re-published measurements)

**Future:** Check RTINGS review changelogs for SPD-related corrections; track `spd_last_verified` per TV in registry.

---

---

### 4. Monthly Display Technology Intelligence Report
**Priority: High | Effort: High**

Automated monthly analyst report delivered via email on the first Monday of each month. Three sections with data-driven insights, charts, and editorial analysis. Written in an engaging Wired-style voice -- factual but compelling.

#### Schedule & Integration
- Runs on first Monday of each month, after the weekly data pull completes
- Add a second GitHub Actions workflow (`monthly-report.yml`) triggered by `workflow_dispatch` + cron
- Cron runs every Monday; script checks `if today.day <= 7` to only execute on first Monday
- Uses latest data from the weekly pipeline (tv_database, price_history, changelog, registry)

#### Section 1: Display Technology Overview
- **New devices**: TVs added since last report (from changelog + registry `first_seen_date`)
- **Removed devices**: TVs dropped from RTINGS coverage
- **Performance trends**: Score changes (mixed_usage, gaming, home_theater) by technology
- **Technology shifts**: Are QD gamuts getting wider? Is WOLED closing the gap? FWHM trends over time
- **Model year comparisons**: 2026 vs 2025 models on key metrics as new reviews arrive
- **Charts**: Score distributions by tech (box plots), FWHM trend lines, new model scorecards

#### Section 2: Pricing Intelligence
- **Price trends by technology**: Month-over-month, quarter-over-quarter price movement
- **New vs. old model pricing**: Are 2026 models launching higher/lower than 2025 equivalents?
- **Technology price gaps**: QD-LCD vs WOLED vs QD-OLED price/performance spread
- **Value frontier shifts**: Has the efficient frontier moved? New best-value picks?
- **Seasonal patterns**: As data accumulates, identify sale cycles (Black Friday, Prime Day, etc.)
- **Charts**: Price trend lines by tech, price/performance scatter evolution, value frontier overlay

#### Section 3: Macro & Industry Context
- **Display industry news**: Panel factory output, supply chain developments, new product announcements
- **Macro economics**: Consumer spending trends, tariff impacts, currency effects on pricing
- **Technology roadmap**: Upcoming display technologies (microLED, tandem OLED, perovskite QD)
- **Competitive landscape**: Brand strategy shifts, market share indicators
- **Sources**: Web search for recent industry reporting (Display Supply Chain Consultants, Omdia, Display Daily, LEDinside, etc.)
- **Editorial voice**: Synthesize data + context into "so what" takeaways for the team

#### Implementation Plan

**New files:**
- `monthly_report.py` -- Report generator orchestrator
- `report_templates/` -- HTML/CSS templates for PDF rendering
- `.github/workflows/monthly-report.yml` -- Monthly workflow

**Technical approach:**
1. **Data collection** (`monthly_report.py`):
   - Load tv_database, changelog, registry, price_history CSVs
   - Compute all metrics: deltas, trends, rankings, comparisons
   - Web search for macro/industry context (via API or scraping)

2. **Analysis & narrative** (Claude API):
   - Pass structured data + metrics to Claude API
   - Prompt for each section with tone/style guidelines
   - Claude generates narrative text with specific data citations
   - Requires `ANTHROPIC_API_KEY` as a GitHub Secret

3. **Visualization** (matplotlib/plotly):
   - Generate charts as PNG/SVG embedded in report
   - Consistent styling matching dashboard aesthetic (dark theme)
   - Product images pulled from RTINGS (cached)

4. **PDF generation** (weasyprint or reportlab):
   - HTML template with CSS styling → PDF
   - Nanosys/company branding (colors, logo if provided)
   - Professional layout: cover page, table of contents, sections, charts inline

5. **Delivery**:
   - Email PDF attachment to jeff@jeffyurek.com via existing Gmail SMTP
   - Also save PDF to `data/reports/` (gitignored, large binaries)
   - Summary excerpt in email body for quick scanning

**Dependencies to add:**
- `anthropic` (Claude API for narrative generation)
- `weasyprint` (HTML → PDF) or `fpdf2` (lighter weight)
- Possibly `jinja2` (HTML templating, already installed via streamlit)

**Secrets to add:**
- `ANTHROPIC_API_KEY` for Claude API calls

**Cost estimate:**
- Claude API: ~$0.50-2.00 per report (Sonnet for analysis, ~10k input + 5k output tokens per section)
- Runs once per month, so ~$6-24/year

**Report length target:** 4-8 pages PDF, ~2000-3000 words + 6-10 charts

---

### 6. Model year sort order (reverse chronological)
**Priority: Low | Effort: Low**

TV model years in the filter menu should be sorted newest-first (e.g. 2026, 2025, 2024…).

---

### 7. PDF download missing on live Streamlit Cloud page
**Priority: Medium | Effort: Low**

The monthly report PDF download button works locally but is missing on the deployed Streamlit Cloud app. Investigate — likely a missing data file or path issue in the cloud environment.

---

### 8. SPD FWHM calibration check — KSF green & QD-LCD red
**Priority: High | Effort: Medium**

Sony KSF models show suspiciously narrow green FWHM. QD-LCD reds are spread over a broad range — expected to cluster into two groups (~35nm InP and ~20-25nm CdSe) rather than a continuous spread. Investigate whether peak detection or FWHM measurement has a systematic bias for these cases.

**Investigation plan:**
- Pull per-TV FWHM values for KSF green and QD-LCD red from `spd_analysis_results.csv`
- Compare against reference spectra / published literature values
- Check if peak detection is picking the wrong peak or measuring a shoulder
- Look for two distinct clusters in QD-LCD red (InP vs CdSe)

---

## Completed

### panel_sub_type extracted from RTINGS API (2026-03-06)
Closed roadmap item #2. Added test ID 216 (`panel_sub_type`) to scraper. API returns clean values: `QD-OLED`, `WOLED`, `VA`, `IPS`, `VA (except 75")` for all 85 TVs. `build_schema.py` now uses `panel_sub_type` as high-confidence override for OLED `color_architecture` (19 OLEDs classified). SPD analysis confirmed 100% agreement — no mismatches.

### WOLED FWHM measurement confirmed correct (2026-03-06)
Closed roadmap item #3. FWHM from zero baseline is correct for WOLED. Tandem WOLED (LG G5, Panasonic Z95B) has discrete R/G emitters producing genuinely narrower peaks (green 33-54nm) vs traditional WOLED (B4/C4/C5: green 70-110nm). This is a real structural advantage, not a measurement artifact. Expect G6/C6 to follow G5 pattern.

### Panasonic W95A confirmed CdSe (2026-03-06)
Closed roadmap item #5. SPD shows unambiguous CdSe signature (green 23.9nm, red 17.7nm). Classified as QD-LCD CdSe. Panasonic's "Cd-Free" claim contradicted by spectral data.

### FWHM zero-baseline fix + CdSe/InP subclassification (2026-03-06)
Closed roadmap items #6, #7, #8. Switched FWHM from scipy prominence-based to absolute zero baseline. Added CdSe vs InP QD material tracking via red FWHM threshold (30nm). Fixed model year sort, PDF download on Streamlit Cloud, pricing charts switched to median.

### WLED red FWHM propagation verified (2026-02-19)
Investigated ROADMAP item #6 — WLED red FWHM values are now correct at every stage: `spd_analysis_results.csv` → `tv_database.csv` → `tv_database_with_prices.csv` → dashboard. Samsung U8000F shows 77.4nm (correct). Issue was stale data prior to pipeline re-run.

### FWHM overlap correction (2026-02-19)
Added HWHM mirroring for overlapping peaks in `spd_analyzer.py`. WLED red FWHM corrected from 24-34nm (artificially narrow due to prominence-based measurement) to 76-86nm (physically correct). QD-LCD measurements unchanged.

### Pipeline code review fixes (2026-02-19)
- Fixed timeout log message (10 → 20 min)
- Removed unused import
- Guarded pricing pipeline against empty snapshot IndexError

### Security + deployment (prior session)
- Password gate on dashboard
- Removed RTINGS branding
- Email notifications via Gmail SMTP
- GitHub Actions weekly automation
