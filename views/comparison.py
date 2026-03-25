"""Comparison Tool view – side-by-side product comparison with radar chart."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.charts import TECH_ORDER, friendly, PL


def render(fdf, pcfg):
    """Render the Comparison Tool page.

    Parameters
    ----------
    fdf : pd.DataFrame
        Filtered product dataframe.
    pcfg : dict
        Product-category configuration (score_cols, primary_score, etc.).
    """
    st.title(f"{pcfg['item_singular']} Comparison Tool")

    all_names = sorted(fdf["fullname"].tolist())
    selected = st.multiselect(
        f"Select {pcfg['item_label'].lower()} to compare (up to 5)", all_names, max_selections=5,
        default=all_names[:2] if len(all_names) >= 2 else all_names[:1],
    )

    if not selected:
        st.info(f"Select at least one {pcfg['item_singular'].lower()} to compare.")
        return

    comp = fdf[fdf["fullname"].isin(selected)].copy()

    cols = st.columns(len(selected))
    for i, (_, row) in enumerate(comp.iterrows()):
        with cols[i]:
            st.markdown(f"**{row['fullname']}**")
            st.caption(f"{row['brand']} | {row['display_type']}")
            st.markdown(f"**{row['color_architecture']}**")
            if pd.notna(row.get("price_best")):
                st.metric("Price", f"${row['price_best']:,.0f}")
            else:
                st.metric("Price", "N/A")
            _ps = pcfg["primary_score"]
            if _ps in row and pd.notna(row.get(_ps)):
                st.metric(friendly(_ps), f"{row[_ps]:.1f}")

    st.divider()

    st.subheader("Usage Score Comparison")
    score_keys = [c for c in pcfg["score_cols"] if c in comp.columns]
    categories = [friendly(c) for c in score_keys]

    fig = go.Figure()
    for _, row in comp.iterrows():
        values = [row.get(k, 0) for k in score_keys]
        values.append(values[0])
        fig.add_trace(go.Scatterpolar(
            r=values, theta=categories + [categories[0]],
            fill="toself", name=row["fullname"], opacity=0.6,
        ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 10], tickfont=dict(size=12)),
            angularaxis=dict(tickfont=dict(size=14, weight=600)),
        ),
        height=520,
        font=dict(family="Inter, sans-serif", size=14),
        legend=dict(font=dict(size=13)),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Detailed Specs")
    detail_rows = [
        ("Display Type", "display_type"),
        ("Color Architecture", "color_architecture"),
        ("Backlight", "backlight_type_v2"),
        ("Dimming Zones", "dimming_zone_count"),
        ("QD Material", "qd_material"),
        ("Marketing Label", "marketing_label"),
        ("Panel Type", "panel_type"),
        ("Panel Sub Type", "panel_sub_type"),
        ("Resolution", "resolution"),
        ("Refresh Rate", "native_refresh_rate"),
        ("Price", "price_best"),
        ("Price Size", "price_size"),
        ("Price Source", "channel"),
        ("$/m\u00b2", "price_per_m2"),
    ] + [(friendly(c), c) for c in pcfg["score_cols"]] + [
        ("Native Contrast", "native_contrast"),
        ("HDR Peak (10%)", "hdr_peak_10pct_nits"),
        ("HDR Peak (2%)", "hdr_peak_2pct_nits"),
        ("SDR Peak", "sdr_real_scene_peak_nits"),
        ("BT.2020 Coverage", "hdr_bt2020_coverage_itp_pct"),
        ("DCI-P3 Coverage", "sdr_dci_p3_coverage_pct"),
        (friendly(pcfg["input_lag_col"]), pcfg["input_lag_col"]),
        ("Response Time", "total_response_time_ms"),
    ]

    table_data = {"Spec": [r[0] for r in detail_rows]}
    for _, row in comp.iterrows():
        values = []
        for label, col in detail_rows:
            val = row.get(col)
            if pd.isna(val):
                values.append("\u2014")
            elif col in ("price_best", "price_per_m2"):
                values.append(f"${float(val):,.0f}")
            elif col == "price_size":
                values.append(f'{int(val)}"')
            elif col == "dimming_zone_count":
                values.append(f"{int(val):,}")
            elif isinstance(val, float):
                values.append(f"{val:.1f}")
            else:
                values.append(str(val))
        table_data[row["fullname"]] = values

    st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True, height=800)
