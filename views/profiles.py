"""Product Profile view – single-product detail page with specs and pricing."""

import streamlit as st
import pandas as pd
import plotly.express as px

from src.charts import friendly, PL


def render(fdf, pcfg, *, prices_df=None):
    """Render the Product Profile page.

    Parameters
    ----------
    fdf : pd.DataFrame
        Filtered product dataframe.
    pcfg : dict
        Product-category configuration (score_cols, primary_score, etc.).
    prices_df : pd.DataFrame | None
        Full per-size pricing dataframe (optional).
    """
    st.title(f"{pcfg['item_singular']} Profile")

    selected_tv = st.selectbox(f"Select a {pcfg['item_singular'].lower()}", sorted(fdf["fullname"].tolist()))
    tv = fdf[fdf["fullname"] == selected_tv].iloc[0]

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.header(tv["fullname"])
        st.caption(f"{tv['brand']} | Released: {tv['released_at'].strftime('%Y-%m-%d') if pd.notna(tv.get('released_at')) else 'Unknown'}")
    with col2:
        st.metric("Price", f"${tv['price_best']:,.0f}" if pd.notna(tv.get("price_best")) else "N/A")
        if pd.notna(tv.get("price_per_m2")):
            st.metric("$/m\u00b2", f"${tv['price_per_m2']:,.0f}")
    with col3:
        _ps = pcfg["primary_score"]
        _ps_val = tv.get(_ps)
        st.metric(friendly(_ps), f"{_ps_val:.1f}/10" if pd.notna(_ps_val) else "N/A")
        if pd.notna(tv.get("marketing_label")):
            st.markdown(f"*{tv['marketing_label']}*")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Display Technology")
        tech_info = {
            "Display Type": tv.get("display_type"),
            "Color Architecture": tv.get("color_architecture"),
            "Backlight": tv.get("backlight_type_v2"),
            "Dimming Zones": f"{int(tv['dimming_zone_count']):,}" if pd.notna(tv.get("dimming_zone_count")) else "N/A",
            "QD Present": tv.get("qd_present"),
            "QD Material": tv.get("qd_material", "N/A"),
            "SPD Verified": tv.get("spd_verified"),
            "SPD Classification": tv.get("spd_classification"),
            "Marketing Label": tv.get("marketing_label", "N/A"),
            "Panel Type": tv.get("panel_type"),
            "Panel Sub Type": tv.get("panel_sub_type"),
        }
        for k, v in tech_info.items():
            st.markdown(f"**{k}:** {v}")

    with col2:
        st.subheader("Usage Scores")
        scores = {friendly(c): tv.get(c) for c in pcfg["score_cols"]}
        score_df = pd.DataFrame([{"Usage": k, "Score": v} for k, v in scores.items() if pd.notna(v)])
        if len(score_df) > 0:
            fig = px.bar(score_df, x="Score", y="Usage", orientation="h",
                         range_x=[0, 10], text="Score",
                         color_discrete_sequence=["#4B40EB"])
            fig.update_traces(texttemplate="%{text:.1f}", textposition="outside",
                              textfont_size=14, textfont_weight=600)
            fig.update_layout(height=250, showlegend=False,
                              margin=dict(l=0, r=50, t=0, b=0), **PL)
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Performance Metrics")
    perf_col1, perf_col2, perf_col3 = st.columns(3)

    with perf_col1:
        st.markdown("**Brightness**")
        for k, v in {
            "HDR Peak (2%)": f"{tv.get('hdr_peak_2pct_nits', 'N/A')} nits",
            "HDR Peak (10%)": f"{tv.get('hdr_peak_10pct_nits', 'N/A')} nits",
            "SDR Real Scene": f"{tv.get('sdr_real_scene_peak_nits', 'N/A')} nits",
            "Brightness Score": f"{tv.get('brightness_score', 'N/A')}",
        }.items():
            st.markdown(f"**{k}:** {v}")

    with perf_col2:
        st.markdown("**Contrast & Color**")
        for k, v in {
            "Native Contrast": f"{int(tv['native_contrast']):,}:1" if pd.notna(tv.get("native_contrast")) else "N/A",
            "Contrast Score": tv.get("contrast_ratio_score", "N/A"),
            "BT.2020 (ITP)": f"{tv.get('hdr_bt2020_coverage_itp_pct', 'N/A')}%",
            "DCI-P3": f"{tv.get('sdr_dci_p3_coverage_pct', 'N/A')}%",
            "Color Score": tv.get("color_score", "N/A"),
        }.items():
            st.markdown(f"**{k}:** {v}")

    with perf_col3:
        st.markdown("**Gaming & Response**")
        for k, v in {
            "4K Input Lag": f"{tv.get('input_lag_4k_ms', 'N/A')} ms",
            "1080p Input Lag": f"{tv.get('input_lag_1080p_ms', 'N/A')} ms",
            "Response Time": f"{tv.get('total_response_time_ms', 'N/A')} ms",
            "HDMI 2.1": tv.get("hdmi_21_speed", "N/A"),
            "VRR": tv.get("vrr_support", "N/A"),
            "HDMI Ports": tv.get("hdmi_ports", "N/A"),
        }.items():
            st.markdown(f"**{k}:** {v}")

    st.subheader("SPD Spectral Peaks")
    spd_col1, spd_col2, spd_col3 = st.columns(3)
    with spd_col1:
        st.metric("Blue Peak", f"{tv.get('blue_peak_nm', 'N/A')} nm")
        st.metric("Blue FWHM", f"{tv.get('blue_fwhm_nm', 'N/A')} nm")
    with spd_col2:
        st.metric("Green Peak", f"{tv.get('green_peak_nm', 'N/A')} nm")
        st.metric("Green FWHM", f"{tv.get('green_fwhm_nm', 'N/A')} nm")
    with spd_col3:
        if pd.notna(tv.get("red_peak_nm")):
            st.metric("Red Peak", f"{tv['red_peak_nm']} nm")
            st.metric("Red FWHM", f"{tv['red_fwhm_nm']} nm")
        else:
            st.metric("Red Peak", "N/A")
            st.metric("Red FWHM", "N/A")

    if pd.notna(tv.get("price_best")):
        st.subheader("Pricing")
        price_cols = st.columns(4)
        with price_cols[0]:
            st.metric("Best Price", f"${tv['price_best']:,.0f}")
        with price_cols[1]:
            st.metric("Source", tv.get("channel", tv.get("price_source", "N/A")))
        with price_cols[2]:
            st.metric("Size", f"{int(tv['price_size'])}\"" if pd.notna(tv.get("price_size")) else "N/A")
        with price_cols[3]:
            st.metric("$/m\u00b2", f"${tv['price_per_m2']:,.0f}" if pd.notna(tv.get("price_per_m2")) else "N/A")

        if prices_df is not None and len(prices_df) > 0:
            tv_sizes = prices_df[
                (prices_df["product_id"] == tv["product_id"])
                & prices_df["best_price"].notna()
            ].sort_values("size_inches")
            if len(tv_sizes) > 0:
                st.markdown("**All Available Sizes**")
                tv_sizes_disp = tv_sizes.copy()
                if "price_source" in tv_sizes_disp.columns:
                    tv_sizes_disp["channel"] = tv_sizes_disp["price_source"].replace({
                        "amazon": "Amazon", "amazon_3p": "Amazon",
                        "bestbuy": "Best Buy", "rtings": "RTINGS (affiliate)",
                    })
                size_display = tv_sizes_disp[["size_inches", "best_price", "channel",
                                               "amazon_price", "bestbuy_price", "rtings_price"]].copy()
                size_display.columns = ["Size", "Best Price", "Source", "Amazon", "Best Buy", "RTINGS"]
                size_display["Size"] = size_display["Size"].apply(
                    lambda x: f'{int(x)}"' if pd.notna(x) else "?")
                for col in ["Best Price", "Amazon", "Best Buy", "RTINGS"]:
                    size_display[col] = size_display[col].apply(
                        lambda x: f"${x:,.0f}" if pd.notna(x) else "\u2014")
                st.dataframe(size_display, use_container_width=True, hide_index=True)

    if pd.notna(tv.get("review_url")):
        st.markdown(f"[View full review]({tv['review_url']})")
