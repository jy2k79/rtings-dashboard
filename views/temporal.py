"""Temporal Analysis view — year-over-year technology trends."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from src.charts import TECH_ORDER, TECH_COLORS, friendly, PL


def render(tdf, pcfg):
    """Render the Temporal Analysis page.

    Parameters
    ----------
    tdf : pd.DataFrame
        Temporal dataframe (no year filter applied).
    pcfg : dict
        Product-category config (TV or Monitor).
    """
    st.title("Temporal Analysis")
    st.caption(
        "Year-over-year technology trends. This page ignores the sidebar "
        "Model Year filter so all years are always visible for comparison."
    )

    MIN_SAMPLES = 1  # minimum TVs per (tech, year) group to show aggregated data

    # Valid years present in the temporal dataframe
    _year_counts = tdf["model_year"].dropna().value_counts().sort_index()
    _valid_years = sorted(_year_counts[_year_counts >= 1].index.astype(int).tolist())
    _n_valid_years = len(_valid_years)

    if _n_valid_years == 0:
        st.warning(f"No {pcfg['item_label'].lower()} with release date information available.")
        return

    # Build per-(tech, year) aggregation used across multiple charts
    _avail_scores = [c for c in pcfg["score_cols"] if c in tdf.columns]
    _score_agg = {f"avg_{c}": (c, "mean") for c in _avail_scores}
    _ty = (
        tdf.dropna(subset=["model_year"])
        .groupby(["color_architecture", "model_year"])
        .agg(n=("fullname", "size"), avg_price_m2=("price_per_m2", "mean"), **_score_agg)
        .reset_index()
    )
    _ty["model_year"] = _ty["model_year"].astype(int)
    # Filter to groups meeting minimum sample threshold
    _ty = _ty[_ty["n"] >= MIN_SAMPLES].copy()

    tab_perf, tab_price, tab_qd = st.tabs(["Performance Trends", "Pricing Trends", "QD Material Trends"])

    # ------------------------------------------------------------------
    # Tab 1: Performance Trends
    # ------------------------------------------------------------------
    with tab_perf:
        # Chart 1 — Avg primary score by Technology by Year (grouped bar)
        _ps = pcfg["primary_score"]
        _ps_agg = f"avg_{_ps}"
        _ps_label = friendly(_ps)
        st.subheader(f"Average {_ps_label} by Technology & Year")
        _ch1 = _ty.dropna(subset=[_ps_agg]).copy() if _ps_agg in _ty.columns else pd.DataFrame()
        if len(_ch1) == 0:
            st.info(f"Not enough scored {pcfg['item_label'].lower()} per technology/year.")
        else:
            _ch1["year_str"] = _ch1["model_year"].astype(str)
            _ch1["label"] = _ch1[_ps_agg].apply(lambda v: f"{v:.1f}")
            fig1 = px.bar(
                _ch1,
                x="year_str",
                y=_ps_agg,
                color="color_architecture",
                barmode="group",
                text="label",
                hover_data={"n": True, "color_architecture": True, "year_str": False},
                color_discrete_map=TECH_COLORS,
                category_orders={
                    "color_architecture": TECH_ORDER,
                    "year_str": [str(y) for y in _valid_years],
                },
                labels={
                    "year_str": "Model Year",
                    _ps_agg: f"Avg {_ps_label} Score",
                    "color_architecture": "Technology",
                    "n": "Sample Size",
                },
            )
            fig1.update_traces(textposition="outside")
            fig1.update_layout(
                yaxis=dict(range=[0, 10.5]),
                height=480,
                **PL,
            )
            st.plotly_chart(fig1, use_container_width=True)

        st.divider()

        # Chart 2 — Score Trajectory (line + strip, user-selectable metric)
        st.subheader("Score Trajectory by Technology")
        _metric_options = {friendly(c): c for c in _avail_scores}
        _selected_metric_label = st.selectbox(
            "Metric", list(_metric_options.keys()), index=0
        )
        _selected_metric = _metric_options[_selected_metric_label]

        _dots = tdf.dropna(subset=[_selected_metric, "model_year"]).copy()
        _dots["model_year"] = _dots["model_year"].astype(int)

        if len(_dots) == 0:
            st.info(f"No data for {_selected_metric_label}.")
        else:
            # Per-tech mean line data
            _agg_col = f"avg_{_selected_metric}"
            _line = _ty.dropna(subset=[_agg_col]).copy()

            fig2 = go.Figure()
            for tech in TECH_ORDER:
                color = TECH_COLORS.get(tech, "#888")
                # Individual dots (semi-transparent)
                td = _dots[_dots["color_architecture"] == tech]
                if len(td) > 0:
                    fig2.add_trace(go.Scatter(
                        x=td["model_year"],
                        y=td[_selected_metric],
                        mode="markers",
                        marker=dict(color=color, size=8, opacity=0.3),
                        name=tech,
                        legendgroup=tech,
                        hovertext=td["fullname"],
                        hoverinfo="text+y",
                        showlegend=False,
                    ))
                # Mean line
                tl = _line[_line["color_architecture"] == tech].sort_values("model_year")
                if len(tl) > 0:
                    fig2.add_trace(go.Scatter(
                        x=tl["model_year"],
                        y=tl[_agg_col],
                        mode="lines+markers",
                        marker=dict(color=color, size=10),
                        line=dict(color=color, width=3),
                        name=tech,
                        legendgroup=tech,
                    ))
            fig2.update_layout(
                xaxis=dict(
                    title="Model Year",
                    tickmode="array",
                    tickvals=_valid_years,
                    ticktext=[str(y) for y in _valid_years],
                ),
                yaxis=dict(title=_selected_metric_label, range=[0, 10.5]),
                height=480,
                **PL,
            )
            st.plotly_chart(fig2, use_container_width=True)

    # ------------------------------------------------------------------
    # Tab 2: Pricing Trends
    # ------------------------------------------------------------------
    with tab_price:
        # Chart 3 — Avg $/m² by Technology by Year (grouped bar)
        st.subheader("Average Price per m\u00b2 by Technology & Year")
        _ch3 = _ty.dropna(subset=["avg_price_m2"]).copy()
        if len(_ch3) == 0:
            st.info(f"Not enough priced {pcfg['item_label'].lower()} per technology/year.")
        else:
            _ch3["year_str"] = _ch3["model_year"].astype(str)
            _ch3["label"] = _ch3["avg_price_m2"].apply(lambda v: f"${v:,.0f}")

            # WLED baseline (overall mean across all years)
            _wled_all = tdf[tdf["color_architecture"] == "WLED"]["price_per_m2"].dropna()
            _wled_baseline = float(_wled_all.mean()) if len(_wled_all) > 0 else None

            fig3 = px.bar(
                _ch3,
                x="year_str",
                y="avg_price_m2",
                color="color_architecture",
                barmode="group",
                text="label",
                hover_data={"n": True, "color_architecture": True, "year_str": False},
                color_discrete_map=TECH_COLORS,
                category_orders={
                    "color_architecture": TECH_ORDER,
                    "year_str": [str(y) for y in _valid_years],
                },
                labels={
                    "year_str": "Model Year",
                    "avg_price_m2": "Avg $/m\u00b2",
                    "color_architecture": "Technology",
                    "n": "Sample Size",
                },
            )
            fig3.update_traces(textposition="outside")
            if _wled_baseline:
                fig3.add_hline(
                    y=_wled_baseline,
                    line_dash="dot",
                    line_color=TECH_COLORS["WLED"],
                    opacity=0.5,
                    annotation_text=f"WLED avg ${_wled_baseline:,.0f}",
                    annotation_position="top right",
                    annotation_font_color=TECH_COLORS["WLED"],
                )
            fig3.update_layout(
                yaxis=dict(title="Avg Price per m\u00b2"),
                height=480,
                **PL,
            )
            st.plotly_chart(fig3, use_container_width=True)

        st.divider()

        # Chart 4 — Year-over-Year Change Summary (metric cards)
        st.subheader("Year-over-Year Change Summary")
        if _n_valid_years < 2:
            st.info(
                "Need at least two model years with sufficient data to show "
                "year-over-year changes. Currently only "
                f"{_n_valid_years} year(s) available."
            )
        else:
            _latest_yr = _valid_years[-1]
            _prev_yr = _valid_years[-2]
            _prev = _ty[_ty["model_year"] == _prev_yr].set_index("color_architecture")
            _curr = _ty[_ty["model_year"] == _latest_yr].set_index("color_architecture")
            _common_techs = [t for t in TECH_ORDER if t in _prev.index and t in _curr.index]

            if not _common_techs:
                st.info(
                    f"No technologies have enough data in both {_prev_yr} and "
                    f"{_latest_yr} to compare (need n >= {MIN_SAMPLES} each year)."
                )
            else:
                st.caption(f"Comparing {_prev_yr} vs {_latest_yr} model years")
                for tech in _common_techs:
                    color = TECH_COLORS.get(tech, "#888")
                    p_score = _prev.loc[tech, _ps_agg] if _ps_agg in _prev.columns else np.nan
                    c_score = _curr.loc[tech, _ps_agg] if _ps_agg in _curr.columns else np.nan
                    score_delta = c_score - p_score
                    p_n = int(_prev.loc[tech, "n"])
                    c_n = int(_curr.loc[tech, "n"])

                    p_m2 = _prev.loc[tech, "avg_price_m2"]
                    c_m2 = _curr.loc[tech, "avg_price_m2"]

                    st.markdown(
                        f"<span style='color:{color}; font-weight:700; font-size:1.1rem'>"
                        f"{tech}</span> &nbsp; "
                        f"<span style='color:#999; font-size:0.85rem'>"
                        f"n={p_n} \u2192 {c_n}</span>",
                        unsafe_allow_html=True,
                    )
                    cols = st.columns(3)
                    with cols[0]:
                        if pd.notna(c_score):
                            st.metric(
                                _ps_label,
                                f"{c_score:.1f}",
                                delta=f"{score_delta:+.1f}" if pd.notna(score_delta) else None,
                            )
                        else:
                            st.metric(_ps_label, "N/A")
                    with cols[1]:
                        if pd.notna(c_m2):
                            m2_delta = None
                            if pd.notna(p_m2) and p_m2 > 0:
                                pct = (c_m2 - p_m2) / p_m2 * 100
                                m2_delta = f"{pct:+.0f}%"
                            st.metric(
                                "Avg $/m\u00b2",
                                f"${c_m2:,.0f}",
                                delta=m2_delta,
                                delta_color="inverse",
                            )
                        else:
                            st.metric("Avg $/m\u00b2", "N/A")
                    with cols[2]:
                        if pd.notna(c_m2) and c_score > 0:
                            val = c_m2 / c_score
                            prev_val = (p_m2 / p_score) if pd.notna(p_m2) and p_score > 0 else None
                            val_delta = None
                            if prev_val:
                                val_pct = (val - prev_val) / prev_val * 100
                                val_delta = f"{val_pct:+.0f}%"
                            st.metric(
                                "$/m\u00b2 per Point",
                                f"${val:,.0f}",
                                delta=val_delta,
                                delta_color="inverse",
                            )

    # ------------------------------------------------------------------
    # Tab 3: QD Material Trends
    # ------------------------------------------------------------------
    with tab_qd:
        st.subheader("Quantum Dot Material by Model Year")
        st.caption(
            "CdSe vs InP (Cd-Free) classification based on red peak FWHM. "
            "CdSe QDs have narrow red emission (<28nm), InP QDs are wider (>34nm)."
        )
        _qd_df = tdf.dropna(subset=["model_year"]).copy()
        _qd_df = _qd_df[_qd_df["qd_material"].isin(["CdSe", "InP"])]
        if len(_qd_df) == 0:
            st.info("No QD-equipped TVs with model year data.")
        else:
            _qd_df["model_year"] = _qd_df["model_year"].astype(int)
            _qd_counts = (
                _qd_df.groupby(["model_year", "qd_material"])
                .size()
                .reset_index(name="Count")
            )
            _qd_counts["year_str"] = _qd_counts["model_year"].astype(str)
            _qd_colors = {"CdSe": "#e74c3c", "InP": "#2ecc71"}
            fig_qd = px.bar(
                _qd_counts,
                x="year_str",
                y="Count",
                color="qd_material",
                barmode="stack",
                text="Count",
                color_discrete_map=_qd_colors,
                category_orders={
                    "qd_material": ["CdSe", "InP"],
                    "year_str": [str(y) for y in sorted(_qd_counts["model_year"].unique())],
                },
                labels={
                    "year_str": "Model Year",
                    "qd_material": "QD Material",
                },
            )
            fig_qd.update_traces(textposition="inside")
            fig_qd.update_layout(height=420, **PL)
            st.plotly_chart(fig_qd, use_container_width=True)

        # Breakdown table
        st.subheader("QD Material by Brand")
        _qd_brand = tdf[tdf["qd_material"].isin(["CdSe", "InP"])]
        if len(_qd_brand) > 0:
            _qd_pivot = (
                _qd_brand.groupby(["brand", "qd_material"])
                .size()
                .unstack(fill_value=0)
            )
            _qd_pivot["Total"] = _qd_pivot.sum(axis=1)
            _qd_pivot = _qd_pivot.sort_values("Total", ascending=False)
            st.dataframe(_qd_pivot, use_container_width=True)
