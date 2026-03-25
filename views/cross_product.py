"""Cross-Product Analysis view — combined TV + Monitor analysis."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from src.charts import TECH_ORDER, TECH_COLORS, PL


def render(df):
    """Render Cross-Product Analysis page.

    Parameters
    ----------
    df : pd.DataFrame
        Unfiltered full DataFrame containing both TVs and Monitors.
    """
    st.title("Cross-Product Display Technology Analysis")
    st.caption(f"Combined view: {len(df)} products ({df['product_type'].value_counts().to_dict()}) · "
               "RTINGS-reviewed TVs and Monitors")

    PRODUCT_TYPE_COLORS = {"tv": "#FFC700", "monitor": "#4B40EB"}
    PRODUCT_TYPE_LABELS = {"tv": "TVs", "monitor": "Monitors"}
    df["Product Type"] = df["product_type"].map(PRODUCT_TYPE_LABELS)

    # --- Headline metrics ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Products", len(df))
    _n_qd = df["qd_present"].eq("Yes").sum()
    c2.metric("QD Products", _n_qd)
    c3.metric("QD Adoption", f"{_n_qd / len(df) * 100:.0f}%")
    _priced = df[df["price_per_m2"].notna()]
    c4.metric("With Pricing", len(_priced))

    st.divider()

    # --- Section 0: Master RTINGS Score by Technology ---
    st.subheader("Master RTINGS Score by Technology")
    st.caption("TV: Mixed Usage score · Monitors: mean of PC Gaming, Console Gaming, Office, Editing · "
               "Master: weighted average by product count")

    # Compute composite score per product
    _mon_score_cols = ["pc_gaming", "console_gaming", "office", "editing"]
    _tv_mask = df["product_type"] == "tv"
    _mon_mask = df["product_type"] == "monitor"

    # TV uses mixed_usage, monitor uses mean of 4 scores
    df["_master_score"] = np.nan
    if "mixed_usage" in df.columns:
        df.loc[_tv_mask, "_master_score"] = df.loc[_tv_mask, "mixed_usage"]
    _available_mon_scores = [c for c in _mon_score_cols if c in df.columns]
    if _available_mon_scores:
        df.loc[_mon_mask, "_master_score"] = df.loc[_mon_mask, _available_mon_scores].mean(axis=1)

    _master_by_tech = (df.dropna(subset=["_master_score"])
                       .groupby("color_architecture", observed=False)
                       .agg(_score=("_master_score", "mean"), _n=("_master_score", "size"))
                       .reset_index())
    _master_by_tech.columns = ["Technology", "Master Score", "n"]

    ms1, ms2 = st.columns(2)
    with ms1:
        st.markdown("**Master Score by Technology**")
        fig = px.bar(_master_by_tech, x="Technology", y="Master Score",
                     color="Technology", color_discrete_map=TECH_COLORS,
                     text=_master_by_tech["Master Score"].apply(lambda x: f"{x:.1f}" if pd.notna(x) else ""),
                     category_orders={"Technology": TECH_ORDER},
                     hover_data={"n": True})
        fig.update_traces(textposition="outside", textfont_size=14, textfont_weight=600,
                          cliponaxis=False)
        fig.update_layout(showlegend=False, height=400,
                          yaxis=dict(range=[0, 10.5], title="Avg Score"),
                          **PL)
        st.plotly_chart(fig, use_container_width=True)

    with ms2:
        st.markdown("**Score Breakdown: TVs vs Monitors**")
        _score_by_type = (df.dropna(subset=["_master_score"])
                          .groupby(["color_architecture", "Product Type"], observed=False)["_master_score"]
                          .mean().reset_index())
        _score_by_type.columns = ["Technology", "Product Type", "Avg Score"]
        _score_by_type = _score_by_type.dropna(subset=["Avg Score"])
        if len(_score_by_type) > 0:
            fig = px.bar(_score_by_type, x="Technology", y="Avg Score",
                         color="Product Type",
                         color_discrete_map={"TVs": "#FFC700", "Monitors": "#4B40EB"},
                         barmode="group", text=_score_by_type["Avg Score"].apply(lambda x: f"{x:.1f}"),
                         category_orders={"Technology": TECH_ORDER})
            fig.update_traces(textposition="outside", textfont_size=12, textfont_weight=600,
                              cliponaxis=False)
            fig.update_layout(height=400, legend_title_text="",
                              yaxis=dict(range=[0, 10.5], title="Avg Score"), **PL)
            st.plotly_chart(fig, use_container_width=True)

    # Clean up temp column
    df.drop(columns=["_master_score"], inplace=True)

    st.divider()

    # --- Section 1: QD Adoption ---
    st.subheader("Quantum Dot Adoption")
    qd1, qd2, qd3 = st.columns(3)

    with qd1:
        st.markdown("**Overall QD Adoption**")
        _qd_counts = df["qd_present"].value_counts()
        _qd_pie = pd.DataFrame({
            "QD Status": ["QD (QD-LCD + QD-OLED)", "Non-QD"],
            "Count": [_qd_counts.get("Yes", 0), _qd_counts.get("No", 0)],
        })
        fig = px.pie(_qd_pie, names="QD Status", values="Count",
                     color="QD Status",
                     color_discrete_map={
                         "QD (QD-LCD + QD-OLED)": "#FF009F",
                         "Non-QD": "#A8BDD0",
                     },
                     hole=0.4)
        fig.update_traces(textinfo="percent+value", textfont_size=14, textfont_weight=600)
        fig.update_layout(height=350, showlegend=True, legend_title_text="",
                          margin=dict(l=0, r=0, t=10, b=0), **PL)
        st.plotly_chart(fig, use_container_width=True)

    with qd2:
        st.markdown("**QD Adoption by Product Type**")
        _qd_by_type = (df.groupby(["Product Type", "qd_present"], observed=True)
                        .size().reset_index(name="Count"))
        fig = px.bar(_qd_by_type, x="Product Type", y="Count", color="qd_present",
                     color_discrete_map={"Yes": "#FF009F", "No": "#A8BDD0"},
                     barmode="stack", text="Count",
                     labels={"qd_present": "QD Present"})
        fig.update_traces(textposition="inside", textfont_size=13, textfont_weight=600)
        fig.update_layout(height=350, legend_title_text="QD Present",
                          margin=dict(l=0, r=0, t=10, b=0), **PL)
        st.plotly_chart(fig, use_container_width=True)

    with qd3:
        st.markdown("**QD Adoption by Brand**")
        _qd_brands = (df[df["qd_present"] == "Yes"]
                       .groupby("brand").size().reset_index(name="QD Products")
                       .sort_values("QD Products", ascending=True))
        _total_brands = df.groupby("brand").size().reset_index(name="Total")
        _qd_brands = _qd_brands.merge(_total_brands, on="brand")
        _qd_brands["QD %"] = (_qd_brands["QD Products"] / _qd_brands["Total"] * 100).round(0)
        fig = px.bar(_qd_brands, y="brand", x="QD Products", orientation="h",
                     text=_qd_brands.apply(lambda r: f"{int(r['QD Products'])}/{int(r['Total'])} ({int(r['QD %'])}%)", axis=1),
                     color_discrete_sequence=["#FF009F"])
        fig.update_traces(textposition="outside", textfont_size=12, textfont_weight=600,
                          cliponaxis=False)
        fig.update_layout(height=350, showlegend=False, yaxis_title="",
                          margin=dict(l=0, r=80, t=10, b=0), **PL)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # --- Section 2: Technology Distribution Comparison ---
    st.subheader("Technology Distribution: TVs vs Monitors")
    td1, td2 = st.columns(2)

    with td1:
        st.markdown("**Technology Mix by Product Type**")
        _tech_by_type = (df.groupby(["Product Type", "color_architecture"], observed=False)
                         .size().reset_index(name="Count"))
        # Compute percentages within each product type
        _type_totals = _tech_by_type.groupby("Product Type")["Count"].transform("sum")
        _tech_by_type["Pct"] = (_tech_by_type["Count"] / _type_totals * 100).round(1)
        fig = px.bar(_tech_by_type, x="Product Type", y="Pct", color="color_architecture",
                     color_discrete_map=TECH_COLORS,
                     category_orders={"color_architecture": TECH_ORDER},
                     barmode="stack", text="Pct",
                     labels={"Pct": "% of Products", "color_architecture": "Technology"})
        fig.update_traces(texttemplate="%{text:.0f}%", textposition="inside",
                          textfont_size=12, textfont_weight=600)
        fig.update_layout(height=420, legend_title_text="Technology",
                          yaxis=dict(range=[0, 105], title="% of Products"), **PL)
        st.plotly_chart(fig, use_container_width=True)

    with td2:
        st.markdown("**Product Count by Technology**")
        _tech_counts = (df.groupby(["color_architecture", "Product Type"], observed=False)
                        .size().reset_index(name="Count"))
        fig = px.bar(_tech_counts, x="color_architecture", y="Count", color="Product Type",
                     color_discrete_map={"TVs": "#FFC700", "Monitors": "#4B40EB"},
                     barmode="group", text="Count",
                     category_orders={"color_architecture": TECH_ORDER},
                     labels={"color_architecture": "Technology"})
        fig.update_traces(textposition="outside", textfont_size=12, textfont_weight=600,
                          cliponaxis=False)
        fig.update_layout(height=420, legend_title_text="",
                          yaxis_title="Products", **PL)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # --- Section 3: $/m² Across Form Factors ---
    st.subheader("Price per m\u00b2: TVs vs Monitors")

    pm1, pm2 = st.columns(2)

    with pm1:
        st.markdown("**Avg $/m\u00b2 by Technology & Product Type**")
        _m2_by = (_priced.groupby(["color_architecture", "Product Type"], observed=False)["price_per_m2"]
                  .mean().reset_index())
        _m2_by.columns = ["Technology", "Product Type", "Avg $/m\u00b2"]
        _m2_by = _m2_by.dropna(subset=["Avg $/m\u00b2"])
        if len(_m2_by) > 0:
            fig = px.bar(_m2_by, x="Technology", y="Avg $/m\u00b2", color="Product Type",
                         color_discrete_map={"TVs": "#FFC700", "Monitors": "#4B40EB"},
                         barmode="group", text="Avg $/m\u00b2",
                         category_orders={"Technology": TECH_ORDER})
            fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside",
                              textfont_size=11, textfont_weight=600, cliponaxis=False)
            fig.update_layout(height=420, legend_title_text="", yaxis_title="Avg $/m\u00b2", **PL)
            st.plotly_chart(fig, use_container_width=True)

    with pm2:
        st.markdown("**All Products: Price vs $/m\u00b2**")
        _scatter = _priced.dropna(subset=["price_best", "price_per_m2"]).copy()
        if len(_scatter) > 0:
            fig = px.scatter(_scatter, x="price_best", y="price_per_m2",
                             color="color_architecture", color_discrete_map=TECH_COLORS,
                             symbol="Product Type",
                             symbol_map={"TVs": "circle", "Monitors": "diamond"},
                             category_orders={"color_architecture": TECH_ORDER},
                             hover_name="fullname",
                             hover_data=["brand", "Product Type"],
                             labels={"price_best": "Price ($)", "price_per_m2": "$/m\u00b2"})
            fig.update_layout(height=420, legend_title_text="",
                              xaxis=dict(range=[0, _scatter["price_best"].max() * 1.1]),
                              yaxis=dict(range=[0, _scatter["price_per_m2"].max() * 1.1]),
                              **PL)
            fig.update_traces(marker=dict(size=10))
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # --- Section 4: Brand Strategy ---
    st.subheader("Brand Technology Strategy")
    st.caption("Which brands use which technologies across TVs and Monitors")

    _brand_tech = (df.groupby(["brand", "color_architecture", "Product Type"], observed=True)
                   .size().reset_index(name="Count"))
    _brand_pivot = _brand_tech.pivot_table(index="brand", columns=["color_architecture", "Product Type"],
                                            values="Count", fill_value=0, observed=True)
    # Flatten column names
    _brand_pivot.columns = [f"{tech}\n({pt})" for tech, pt in _brand_pivot.columns]
    # Only show brands with > 1 product
    _brand_pivot = _brand_pivot[_brand_pivot.sum(axis=1) > 1]
    _brand_pivot = _brand_pivot.loc[:, (_brand_pivot > 0).any()]

    if len(_brand_pivot) > 0:
        fig = px.imshow(_brand_pivot, text_auto=True, color_continuous_scale="Viridis",
                        aspect="auto")
        fig.update_layout(height=max(350, len(_brand_pivot) * 30 + 100),
                          xaxis_title="", yaxis_title="",
                          coloraxis_showscale=False, **PL)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # --- Section 5: FWHM Cross-Product ---
    st.subheader("SPD Fingerprints Across Form Factors")
    st.caption("Same panel technology should produce similar FWHM signatures regardless of product type")

    _fwhm = df.dropna(subset=["green_fwhm_nm", "red_fwhm_nm"]).copy()
    if len(_fwhm) > 0:
        fig = px.scatter(_fwhm, x="green_fwhm_nm", y="red_fwhm_nm",
                         color="color_architecture", color_discrete_map=TECH_COLORS,
                         symbol="Product Type",
                         symbol_map={"TVs": "circle", "Monitors": "diamond"},
                         category_orders={"color_architecture": TECH_ORDER},
                         hover_name="fullname",
                         labels={"green_fwhm_nm": "Green FWHM (nm)",
                                 "red_fwhm_nm": "Red FWHM (nm)"})
        fig.update_layout(height=500, legend_title_text="",
                          xaxis=dict(range=[0, max(150, _fwhm["green_fwhm_nm"].max() * 1.1)]),
                          yaxis=dict(range=[0, max(60, _fwhm["red_fwhm_nm"].max() * 1.1)]),
                          **PL)
        fig.update_traces(marker=dict(size=10))
        st.plotly_chart(fig, use_container_width=True)

        st.caption("Circles = TVs, Diamonds = Monitors. Clusters confirm the same underlying "
                   "panel technology is used across form factors.")
