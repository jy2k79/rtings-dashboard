"""Overview page — high-level KPIs, technology distribution, and pricing."""

import streamlit as st
import pandas as pd
import plotly.express as px

from src.charts import TECH_ORDER, TECH_COLORS, DISPLAY_TYPE_COLORS, friendly, axis_range, PL


def render(fdf, pcfg, *, product_type=None, df=None):
    """Render the Overview page.

    Parameters
    ----------
    fdf : pd.DataFrame
        Filtered DataFrame (after sidebar filters).
    pcfg : dict
        Product-type config (item_label, score_cols, etc.).
    product_type : str | None
        Active product type ("TVs", "Monitors", "All Products").
    df : pd.DataFrame | None
        Full (unfiltered) DataFrame, used for total count in subtitle.
    """
    st.title(f"{pcfg['item_singular']} Display Technology Dashboard")
    _bench_label = "v2.0+" if product_type == "TVs" else "v2.1.2+"
    _total = len(df) if df is not None else len(fdf)
    st.caption(f"Database: {_total} {pcfg['item_label']} — test bench {_bench_label} · "
               f"Data covers RTINGS-reviewed models only, not the full {pcfg['item_singular'].lower()} market")

    priced = fdf[fdf["price_best"].notna()]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(pcfg["item_label"], len(fdf))
    c2.metric("With Pricing", len(priced))
    c3.metric("Brands", fdf["brand"].nunique())
    c4.metric("Avg Price", f"${priced['price_best'].mean():,.0f}" if len(priced) else "N/A")
    c5.metric("Avg $/m\u00b2", f"${priced['price_per_m2'].mean():,.0f}" if len(priced) else "N/A")

    st.divider()

    # --- Hero charts: Pricing & Performance at a glance ---
    hero1, hero2 = st.columns(2)
    with hero1:
        st.subheader("Technology Cost per m\u00b2")
        if len(priced) > 0:
            m2_hero = (priced.dropna(subset=["price_per_m2"])
                       .groupby("color_architecture", observed=False)["price_per_m2"]
                       .mean().reset_index())
            m2_hero.columns = ["Technology", "Avg $/m\u00b2"]
            wled_base = m2_hero.loc[m2_hero["Technology"] == "WLED", "Avg $/m\u00b2"]
            wled_hero = float(wled_base.iloc[0]) if len(wled_base) > 0 else None
            fig = px.bar(m2_hero, x="Technology", y="Avg $/m\u00b2", color="Technology",
                         color_discrete_map=TECH_COLORS, text="Avg $/m\u00b2",
                         category_orders={"Technology": TECH_ORDER})
            fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside",
                              textfont_size=13, textfont_weight=600, cliponaxis=False)
            if wled_hero:
                fig.add_hline(y=wled_hero, line_dash="dot",
                              line_color=TECH_COLORS.get("WLED", "#888"),
                              opacity=0.4)
            fig.update_layout(showlegend=False, height=370, **PL)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"No priced {pcfg['item_label'].lower()} in current filter.")

    with hero2:
        _primary = pcfg["primary_score"]
        _primary_label = friendly(_primary)
        st.subheader(f"{_primary_label} Score by Technology")
        if _primary in fdf.columns:
            fig = px.box(fdf, x="color_architecture", y=_primary,
                         color="color_architecture", color_discrete_map=TECH_COLORS,
                         category_orders={"color_architecture": TECH_ORDER},
                         labels={_primary: f"{_primary_label} Score", "color_architecture": ""},
                         points="all")
            fig.update_layout(showlegend=False, height=370,
                              yaxis=dict(range=axis_range(_primary, fdf)), **PL)
            fig.update_traces(marker=dict(size=7))
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Color Architecture Distribution")
        tech_counts = fdf["color_architecture"].value_counts().reindex(TECH_ORDER).dropna().reset_index()
        tech_counts.columns = ["Technology", "Count"]
        fig = px.bar(tech_counts, x="Technology", y="Count", color="Technology",
                     color_discrete_map=TECH_COLORS, text="Count",
                     category_orders={"Technology": TECH_ORDER})
        fig.update_layout(showlegend=False, height=350, **PL)
        fig.update_traces(textposition="outside", textfont_size=14, textfont_weight=600,
                          cliponaxis=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Display Type & Brand")
        brand_tech = fdf.groupby(["brand", "display_type"]).size().reset_index(name="Count")
        fig = px.bar(brand_tech, x="brand", y="Count", color="display_type",
                     color_discrete_map=DISPLAY_TYPE_COLORS,
                     labels={"brand": "Brand", "display_type": "Display Type"})
        fig.update_layout(height=350, legend_title_text="", **PL)
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.subheader("Price Distribution")
        if len(priced) > 0:
            fig = px.histogram(priced, x="price_best", nbins=25,
                               color="color_architecture", color_discrete_map=TECH_COLORS,
                               category_orders={"color_architecture": TECH_ORDER},
                               labels={"price_best": "Price ($)", "color_architecture": "Technology"})
            fig.update_layout(height=350, barmode="stack", legend_title_text="",
                              xaxis=dict(range=axis_range("price_best", fdf)), **PL)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"No priced {pcfg['item_label'].lower()} in current filter.")

    with col4:
        st.subheader("Price by Technology")
        if len(priced) > 0:
            fig = px.box(priced, x="color_architecture", y="price_best",
                         color="color_architecture", color_discrete_map=TECH_COLORS,
                         category_orders={"color_architecture": TECH_ORDER},
                         labels={"price_best": "Price ($)", "color_architecture": "Technology"},
                         hover_name="fullname", points="all")
            fig.update_layout(showlegend=False, height=350,
                              yaxis=dict(range=axis_range("price_best", priced)), **PL)
            fig.update_traces(marker=dict(size=8))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"No priced {pcfg['item_label'].lower()} in current filter.")

    st.subheader("Usage Score Overview")
    score_cols = [c for c in pcfg["score_cols"] if c in fdf.columns]
    score_data = fdf[["fullname", "color_architecture"] + score_cols].melt(
        id_vars=["fullname", "color_architecture"], value_vars=score_cols,
        var_name="Usage", value_name="Score"
    )
    score_data["Usage"] = score_data["Usage"].map(friendly)
    fig = px.box(score_data, x="Usage", y="Score", color="color_architecture",
                 color_discrete_map=TECH_COLORS,
                 category_orders={"color_architecture": TECH_ORDER},
                 labels={"color_architecture": "Technology"})
    fig.update_layout(height=400, legend_title_text="",
                      yaxis=dict(range=axis_range("mixed_usage", fdf)), **PL)
    fig.update_traces(marker=dict(size=7))
    st.plotly_chart(fig, use_container_width=True)
