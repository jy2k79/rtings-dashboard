#!/usr/bin/env python3
"""
Build the display technology schema for all monitors.

Reads:
    - data/rtings_monitor_data.csv (scraper output)
    - data/spd_monitor_analysis_results.csv (SPD classification results)

Produces:
    - data/monitor_database.csv (enriched dataset with schema columns)

Schema columns match TV schema where concepts overlap (for future master dashboard):
    1. display_type:       OLED | LCD
    2. backlight_type:     Edge-lit | Direct-lit (LCD only)
    3. color_architecture: WLED | KSF | QD-LCD | QD-OLED | WOLED
    4. qd_present:         Yes | No
    5. qd_material:        CdSe | InP | Unknown (if qd_present=Yes)
    6. spd_verified:       Yes | No | Pending
    7. product_type:       monitor (constant — enables pd.concat with TV data)
"""

import pandas as pd
import numpy as np
from pathlib import Path

from silo_config import MONITOR

DATA_DIR = Path("data")


def map_backlight_type(rtings_value, panel_type):
    """Map RTINGS backlight_type to schema backlight_type."""
    if panel_type == 'OLED':
        return None
    mapping = {
        'Full-Array': 'Direct-lit',
        'Direct': 'Direct-lit',
        'Edge': 'Edge-lit',
        'No Backlight': None,
    }
    return mapping.get(rtings_value, rtings_value)


def determine_qd_material(row):
    """Determine quantum dot material from SPD red peak FWHM.

    Same logic as TV schema builder:
      CdSe:    red FWHM < 28nm (narrow)
      InP:     red FWHM > 34nm (wider)
      Unknown: 28-34nm (ambiguous — between clusters)
      QD-OLED: always InP
    """
    color_arch = row['color_architecture']
    if color_arch not in ('QD-LCD', 'QD-OLED'):
        return None

    if color_arch == 'QD-OLED':
        return 'InP'

    CDSE_UPPER = 28   # nm — CdSe cluster tops out here
    INP_LOWER = 34    # nm — InP cluster starts here
    try:
        r_fwhm = float(row.get('red_fwhm_nm', ''))
        if r_fwhm < CDSE_UPPER:
            return 'CdSe'
        elif r_fwhm > INP_LOWER:
            return 'InP'
        else:
            return 'Unknown'
    except (ValueError, TypeError):
        return 'Unknown'


def determine_marketing_label(row):
    """Derive marketing label from monitor product name and brand conventions."""
    name = row['fullname']
    brand = row['brand']
    color_arch = row['color_architecture']

    # Samsung monitors
    if brand == 'Samsung':
        if 'Odyssey OLED' in name:
            return 'Odyssey OLED'
        if 'Odyssey Neo' in name:
            return 'Odyssey Neo'
        if 'Odyssey' in name:
            return 'Odyssey'
        return ''

    # Dell / Alienware
    if brand == 'Dell':
        if 'Alienware' in name:
            if color_arch == 'QD-OLED':
                return 'Alienware QD-OLED'
            return 'Alienware'
        if 'UltraSharp' in name:
            return 'UltraSharp'
        return ''

    # ASUS
    if brand == 'ASUS':
        if 'ROG Swift OLED' in name:
            return 'ROG Swift OLED'
        if 'ROG Strix OLED' in name:
            return 'ROG Strix OLED'
        if 'ROG' in name:
            return 'ROG'
        if 'ProArt' in name:
            return 'ProArt'
        return ''

    # LG
    if brand == 'LG':
        if 'OLED' in name or color_arch in ('WOLED', 'QD-OLED'):
            return 'UltraGear OLED'
        return 'UltraGear'

    # MSI
    if brand == 'MSI':
        if 'QD-OLED' in name:
            return 'QD-OLED'
        if 'MPG' in name:
            return 'MPG'
        if 'MAG' in name:
            return 'MAG'
        return ''

    # Gigabyte
    if brand == 'Gigabyte':
        if 'AORUS' in name:
            return 'AORUS'
        return ''

    # AOC
    if brand == 'AOC':
        if 'AGON' in name:
            return 'AGON'
        return ''

    return ''


def build_monitor_schema():
    """Build the display technology schema for monitors."""
    paths = MONITOR["paths"]

    # Load data
    monitor_df = pd.read_csv(paths["scraped_csv"])
    spd_df = pd.read_csv(paths["spd_results"])

    print(f"Loaded {len(monitor_df)} monitors from scraper data")
    print(f"Loaded {len(spd_df)} SPD analysis results")

    # Merge SPD results
    spd_cols = ['product_id', 'spd_classification', 'spd_confidence',
                'ground_truth_tech', 'ground_truth_qd_type', 'match_status',
                'blue_peak_nm', 'blue_fwhm_nm', 'green_peak_nm', 'green_fwhm_nm',
                'red_peak_nm', 'red_fwhm_nm', 'num_peaks']
    merged = monitor_df.merge(spd_df[spd_cols], on='product_id', how='left')

    # Normalize panel_sub_type
    if 'panel_sub_type' in merged.columns:
        merged['panel_sub_type'] = merged['panel_sub_type'].str.extract(
            r'^([\w-]+)', expand=False)

    # =========================================================================
    # display_type — already LCD or OLED from scraper (panel_type_normalization)
    # =========================================================================
    merged['display_type'] = merged['panel_type'].map({
        'OLED': 'OLED',
        'LCD': 'LCD',
    }).fillna('LCD')

    # =========================================================================
    # panel_type_detail — preserve the original IPS/VA/TN for monitors
    # =========================================================================
    if 'panel_sub_type' in merged.columns:
        merged['panel_type_detail'] = merged['panel_sub_type']
    else:
        merged['panel_type_detail'] = merged['panel_type']

    # =========================================================================
    # backlight_type
    # =========================================================================
    merged['backlight_type_schema'] = merged.apply(
        lambda r: map_backlight_type(r['backlight_type'], r['panel_type']), axis=1
    )

    # =========================================================================
    # color_architecture — from SPD classification
    # =========================================================================
    merged['color_architecture'] = merged['spd_classification']

    # Override OLED color_architecture from panel_sub_type (higher confidence)
    if 'panel_sub_type' in merged.columns:
        oled_mask = merged['display_type'] == 'OLED'
        has_sub = oled_mask & merged['panel_sub_type'].isin(['QD-OLED', 'WOLED'])
        override_count = has_sub.sum()
        if override_count > 0:
            mismatches = has_sub & (merged['color_architecture'] != merged['panel_sub_type'])
            if mismatches.any():
                print(f"\nOLED classification overrides (panel_sub_type vs SPD):")
                for _, row in merged[mismatches].iterrows():
                    print(f"  {row['fullname']:45s} SPD={row['color_architecture']!r:10s} "
                          f"-> API={row['panel_sub_type']!r}")
            merged.loc[has_sub, 'color_architecture'] = merged.loc[has_sub, 'panel_sub_type']
            merged.loc[has_sub, 'spd_confidence'] = 'high'
            print(f"\nApplied panel_sub_type override for {override_count} OLEDs")

    # =========================================================================
    # marketing_label
    # =========================================================================
    merged['marketing_label'] = merged.apply(determine_marketing_label, axis=1)

    # No KSF → Pseudo QD reclassification for monitors
    # (monitors don't use QLED/QNED/ULED marketing terms)

    # =========================================================================
    # qd_present / qd_material / spd_verified
    # =========================================================================
    merged['qd_present'] = merged['color_architecture'].map(
        lambda x: 'Yes' if x in ('QD-LCD', 'QD-OLED') else 'No'
    )
    merged['qd_material'] = merged.apply(determine_qd_material, axis=1)
    merged['spd_verified'] = merged['spd_classification'].map(
        lambda x: 'Yes' if x and x not in ('NO_SPD_IMAGE', '') and not str(x).startswith('ERROR') else 'No'
    )

    # =========================================================================
    # product_type — for future master dashboard compatibility
    # =========================================================================
    merged['product_type'] = 'monitor'

    # =========================================================================
    # Select and order output columns
    # =========================================================================
    schema_cols = [
        # Identity
        'product_id', 'fullname', 'brand', 'url_part', 'review_url',
        'test_bench_id', 'test_bench_version', 'released_at', 'first_published_at',
        'last_updated_at', 'sizes_available', 'product_type',

        # Display Technology Schema
        'display_type',
        'panel_type_detail',
        'backlight_type_schema',
        'color_architecture',
        'qd_present',
        'qd_material',
        'spd_verified',
        'marketing_label',

        # RTINGS panel metadata
        'panel_type', 'panel_sub_type', 'backlight_type',

        # SPD analysis details
        'spd_classification', 'spd_confidence',
        'blue_peak_nm', 'blue_fwhm_nm',
        'green_peak_nm', 'green_fwhm_nm',
        'red_peak_nm', 'red_fwhm_nm',

        # Monitor scores
        'pc_gaming', 'console_gaming', 'office', 'editing',

        # Picture quality scores
        'color_accuracy', 'brightness_score',

        # Color measurements
        'sdr_dci_p3_coverage_pct', 'sdr_bt2020_coverage_pct',
        'hdr_bt2020_coverage_itp_pct',

        # Brightness measurements
        'hdr_peak_10pct_nits', 'hdr_peak_2pct_nits',

        # Contrast
        'native_contrast',

        # Response time
        'first_response_time_ms', 'total_response_time_ms',
        'input_lag_native_ms',

        # Display specs
        'display_size', 'native_refresh_rate', 'resolution',
        'aspect_ratio', 'pixel_density',
        'local_dimming',

        # Ground truth comparison
        'ground_truth_tech', 'ground_truth_qd_type', 'match_status',

        # Metadata
        'scraped_at', 'spd_image', 'spd_image_local',
    ]

    available_cols = [c for c in schema_cols if c in merged.columns]
    output = merged[available_cols].copy()

    # Rename for clarity (match TV schema naming convention)
    output = output.rename(columns={
        'backlight_type_schema': 'backlight_type_v2',
        'backlight_type': 'backlight_type_rtings',
    })

    # Save
    csv_out = paths["database"]
    output.to_csv(csv_out, index=False)
    print(f"\nSaved: {csv_out}")

    xlsx_out = paths["database_xlsx"]
    output.to_excel(xlsx_out, index=False, sheet_name="Monitor Database")
    print(f"Saved: {xlsx_out}")

    # Print schema summary
    print("\n" + "=" * 70)
    print("MONITOR DISPLAY TECHNOLOGY SCHEMA SUMMARY")
    print("=" * 70)

    print(f"\nTotal Monitors: {len(output)}")

    print(f"\n1. display_type:")
    for val, count in output['display_type'].value_counts().items():
        print(f"     {val}: {count}")

    print(f"\n2. panel_type_detail:")
    for val, count in output['panel_type_detail'].value_counts(dropna=False).items():
        print(f"     {val}: {count}")

    print(f"\n3. color_architecture:")
    for val, count in output['color_architecture'].value_counts().items():
        print(f"     {val}: {count}")

    print(f"\n4. qd_present:")
    for val, count in output['qd_present'].value_counts().items():
        print(f"     {val}: {count}")

    print(f"\n5. qd_material (where qd_present=Yes):")
    qd_yes = output[output['qd_present'] == 'Yes']
    for val, count in qd_yes['qd_material'].value_counts(dropna=False).items():
        print(f"     {val}: {count}")

    print(f"\n6. spd_verified:")
    for val, count in output['spd_verified'].value_counts().items():
        print(f"     {val}: {count}")

    print(f"\n{'='*70}")
    print("COLOR ARCHITECTURE BY BRAND")
    print("=" * 70)
    pivot = pd.crosstab(output['brand'], output['color_architecture'])
    print(pivot.to_string())

    return output


if __name__ == '__main__':
    build_monitor_schema()
