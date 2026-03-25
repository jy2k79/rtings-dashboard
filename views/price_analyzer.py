"""Price Analyzer view — extracted from dashboard.py."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.charts import TECH_ORDER, TECH_COLORS, friendly, axis_range, PL, MARKER


def render(fdf, pcfg, *, history_df=None, prices_df=None, selected_techs=None):
    """Render the Price Analyzer page.

    Parameters
    ----------
    fdf : pd.DataFrame
        Filtered product dataframe (sidebar filters already applied).
    pcfg : dict
        Product configuration (item_label, score_cols, etc.).
    history_df : pd.DataFrame | None
        Weekly price-history snapshots (enriched with price_per_m2, iso columns).
    prices_df : pd.DataFrame | None
        Per-size pricing rows from tv_prices.csv.
    selected_techs : list[str] | None
        Technologies selected in the sidebar (used for Price Trends tab filter).
    """
    if history_df is None:
        history_df = pd.DataFrame()
    if prices_df is None:
        prices_df = pd.DataFrame()
    if selected_techs is None:
        selected_techs = []

    all_techs = fdf["color_architecture"].cat.categories.tolist()

    st.title("Price Analyzer")

    priced = fdf[fdf["price_best"].notna()].copy()
    if len(priced) == 0:
        st.warning(f"No priced {pcfg['item_label'].lower()} match the current filters.")
        return

    # Merge Amazon channels: amazon + amazon_3p → Amazon
    if "price_source" in priced.columns:
        priced["channel"] = priced["price_source"].replace({
            "amazon": "Amazon", "amazon_3p": "Amazon",
            "bestbuy": "Best Buy", "rtings": "RTINGS (affiliate)",
        })

    # --- Headline: Technology Cost per m² with WLED premium ---
    st.subheader("Technology Cost per m²")
    st.caption("Median price per square meter by display technology, with premium over WLED baseline. "
               "Per-product median across all available sizes. Data limited to RTINGS-reviewed models.")

    m2_data = (priced.dropna(subset=["price_per_m2"])
               .groupby("color_architecture", observed=False)["price_per_m2"]
               .mean().reset_index())
    m2_data.columns = ["Technology", "Avg $/m²"]
    wled_baseline = m2_data.loc[m2_data["Technology"] == "WLED", "Avg $/m²"]
    wled_val = float(wled_baseline.iloc[0]) if len(wled_baseline) > 0 else None

    fig = px.bar(m2_data, x="Technology", y="Avg $/m²", color="Technology",
                 color_discrete_map=TECH_COLORS, text="Avg $/m²",
                 category_orders={"Technology": TECH_ORDER})
    fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside",
                      textfont_size=14, textfont_weight=600, cliponaxis=False)
    if wled_val:
        fig.add_hline(y=wled_val, line_dash="dot", line_color=TECH_COLORS.get("WLED", "#888"),
                      opacity=0.4)
    fig.update_layout(showlegend=False, height=400, **PL)
    st.plotly_chart(fig, use_container_width=True)

    # Premium metrics row
    m2_col = "Avg $/m²"
    if wled_val and wled_val > 0:
        techs_with_m2 = m2_data[m2_data["Technology"] != "WLED"].sort_values(m2_col)
        mcols = st.columns(len(techs_with_m2))
        for i, (_, row) in enumerate(techs_with_m2.iterrows()):
            med_val = row[m2_col]
            premium_pct = (med_val - wled_val) / wled_val * 100
            with mcols[i]:
                st.metric(str(row["Technology"]),
                          f"${med_val:,.0f}/m²",
                          delta=f"+{premium_pct:.0f}% vs WLED")

    st.divider()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Value Map", "Price/m²", "Best Deals", "Price Trends", "Channels"])

    with tab1:
        score_metric = st.selectbox(
            "Score metric",
            [c for c in pcfg["score_cols"] if c in fdf.columns],
            format_func=friendly,
            key="value_score",
        )
        score_label = friendly(score_metric)
        st.caption("The dashed \"Value Frontier\" traces the best-performing TV at each price point. "
                   "TVs on the line are the best you can buy at that budget; TVs below it are overpriced for their score.")

        fig = px.scatter(priced, x="price_best", y=score_metric,
                         color="color_architecture", color_discrete_map=TECH_COLORS,
                         category_orders={"color_architecture": TECH_ORDER},
                         hover_name="fullname",
                         hover_data=["brand", "channel", "price_size"],
                         labels={"price_best": "Price ($)", score_metric: score_label})
        fig.update_layout(height=550, legend_title_text="Technology",
                          xaxis=dict(range=axis_range("price_best", fdf)),
                          yaxis=dict(range=axis_range(score_metric, fdf)), **PL)
        fig.update_traces(marker=MARKER)

        sorted_p = priced.dropna(subset=[score_metric]).sort_values(score_metric, ascending=False)
        frontier = []
        min_price = float("inf")
        for _, row in sorted_p.iterrows():
            if row["price_best"] <= min_price:
                frontier.append(row)
                min_price = row["price_best"]
        if frontier:
            frontier_df = pd.DataFrame(frontier).sort_values("price_best")
            fig.add_trace(go.Scatter(
                x=frontier_df["price_best"], y=frontier_df[score_metric],
                mode="lines", name="Value Frontier",
                line=dict(color="rgba(255,255,255,0.4)", dash="dash", width=2),
            ))
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Price per Square Meter")
        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(priced.sort_values("price_per_m2"),
                         x="fullname", y="price_per_m2",
                         color="color_architecture", color_discrete_map=TECH_COLORS,
                         category_orders={"color_architecture": TECH_ORDER},
                         hover_data=["price_best", "price_size", "brand"],
                         labels={"price_per_m2": "$/m²", "fullname": ""})
            fig.update_layout(height=500, showlegend=False, xaxis_tickangle=-45,
                              yaxis=dict(range=axis_range("price_per_m2", fdf)), **PL)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.box(priced, x="color_architecture", y="price_per_m2",
                         color="color_architecture", color_discrete_map=TECH_COLORS,
                         category_orders={"color_architecture": TECH_ORDER},
                         points="all", hover_name="fullname",
                         labels={"price_per_m2": "$/m²", "color_architecture": ""})
            fig.update_layout(height=500, showlegend=False,
                              yaxis=dict(range=axis_range("price_per_m2", fdf)), **PL)
            fig.update_traces(marker=dict(size=8))
            st.plotly_chart(fig, use_container_width=True)

        # Per-size $/m² comparison by technology
        st.divider()
        st.subheader("$/m² by Screen Size and Technology")
        st.caption("Median price per m² at each screen size, broken down by technology. "
                   "Shows whether the cost gap between technologies holds across all sizes.")
        if len(history_df) > 0:
            # Use latest snapshot from price_history (already enriched)
            latest_snap = history_df["snapshot_date"].max()
            snap = history_df[history_df["snapshot_date"] == latest_snap].copy()
            # Apply sidebar filters
            snap = snap[snap["product_id"].astype(str).isin(set(fdf["product_id"].astype(str)))]
            snap = snap.dropna(subset=["price_per_m2", "size_inches"])
            snap["size"] = snap["size_inches"].astype(int)

            if len(snap) > 0:
                # Only show sizes with data from 2+ technologies
                common_sizes = [43, 50, 55, 65, 75, 85, 98]
                snap_common = snap[snap["size"].isin(common_sizes)]

                size_tech = (snap_common.groupby(["size", "color_architecture"])["price_per_m2"]
                             .mean().reset_index())
                size_tech.columns = ["Size", "Technology", "Avg $/m²"]
                size_tech["Size"] = size_tech["Size"].astype(str) + '"'

                fig = px.bar(size_tech, x="Size", y="Avg $/m²",
                             color="Technology", color_discrete_map=TECH_COLORS,
                             barmode="group",
                             category_orders={
                                 "Technology": TECH_ORDER,
                                 "Size": [f'{s}"' for s in common_sizes],
                             },
                             text="Avg $/m²")
                fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside",
                                  textfont_size=10, cliponaxis=False)
                fig.update_layout(height=500, legend_title_text="Technology", **PL)
                st.plotly_chart(fig, use_container_width=True)

                # Also show the raw data table
                pivot = size_tech.pivot(index="Technology", columns="Size", values="Avg $/m²")
                pivot = pivot.reindex([t for t in TECH_ORDER if t in pivot.index])
                pivot = pivot[[f'{s}"' for s in common_sizes if f'{s}"' in pivot.columns]]
                st.dataframe(
                    pivot.style.format("${:,.0f}", na_rep="—"),
                    use_container_width=True,
                )
        else:
            st.info("No price history available for per-size breakdown.")

        if len(prices_df) > 0:
            st.divider()
            st.subheader("Price by Screen Size")
            sized = prices_df[prices_df["best_price"].notna() & prices_df["size_inches"].notna()].copy()
            if len(sized) > 0:
                if "price_source" in sized.columns:
                    sized["channel"] = sized["price_source"].replace({
                        "amazon": "Amazon", "amazon_3p": "Amazon",
                        "bestbuy": "Best Buy", "rtings": "RTINGS (affiliate)",
                    })
                fig = px.scatter(sized, x="size_inches", y="best_price",
                                 color="channel",
                                 hover_data=["amazon_asin", "bestbuy_sku"],
                                 labels={"size_inches": "Screen Size (inches)",
                                         "best_price": "Price ($)"})
                fig.update_layout(height=400, legend_title_text="Source",
                                  xaxis=dict(range=axis_range("size_inches", prices_df)),
                                  yaxis=dict(range=axis_range("best_price", prices_df)), **PL)
                fig.update_traces(marker=MARKER)
                st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.subheader(f"Best Value {pcfg['item_label']}")
        value_metric = st.selectbox(
            "Optimize for",
            [c for c in pcfg["score_cols"] if c in fdf.columns],
            format_func=friendly,
            key="deal_metric",
        )
        value_label = friendly(value_metric)

        priced = priced.copy()
        priced["value_index"] = priced[value_metric] / priced["price_best"] * 1000
        priced = priced.sort_values("value_index", ascending=False)

        st.markdown(f"**Top 15 by {value_label} per $1,000**")
        deal_cols = ["fullname", "color_architecture", "price_best", "price_size",
                     value_metric, "value_index", "channel"]
        display = priced[deal_cols].head(15).copy()
        display.columns = ["TV", "Technology", "Price", "Size", value_label,
                           f"{value_label}/k$", "Source"]
        display["Price"] = display["Price"].apply(lambda x: f"${x:,.0f}")
        display[f"{value_label}/k$"] = display[f"{value_label}/k$"].apply(lambda x: f"{x:.1f}")
        display["Size"] = display["Size"].apply(lambda x: f'{int(x)}"' if pd.notna(x) else "?")
        st.dataframe(display, use_container_width=True, hide_index=True)

        st.markdown("**Best Value per Technology**")
        best_per_tech = []
        for tech in all_techs:
            tech_tvs = priced[priced["color_architecture"] == tech]
            if len(tech_tvs) > 0:
                best = tech_tvs.iloc[0]
                best_per_tech.append({
                    "Technology": tech,
                    "Best Value TV": best["fullname"],
                    "Price": f"${best['price_best']:,.0f}",
                    value_label: f"{best[value_metric]:.1f}",
                    f"{value_label}/k$": f"{best['value_index']:.1f}",
                })
        if best_per_tech:
            st.dataframe(pd.DataFrame(best_per_tech), use_container_width=True, hide_index=True)

    with tab4:
        st.subheader("Avg $/m² by Technology Over Time")

        if len(history_df) == 0:
            st.info("No price history available yet. Run the pricing pipeline "
                    "(ideally every Monday) to accumulate weekly data.")
        else:
            # Time granularity selector
            granularity = st.selectbox(
                "Time granularity",
                ["Weekly", "Monthly", "Quarterly", "YTD"],
                key="price_trend_granularity",
            )

            # Apply same filters as the rest of the dashboard (sidebar + 8K exclusion)
            filtered_pids = set(fdf["product_id"].astype(str))
            hist_filtered = history_df[
                history_df["color_architecture"].isin(selected_techs)
                & history_df["product_id"].astype(str).isin(filtered_pids)
            ].copy()
            if len(hist_filtered) == 0:
                st.info("No price history for selected technologies.")
            else:
                # history_df is pre-enriched with price_per_m2, iso_year, iso_week, month, quarter
                hist_m2 = hist_filtered.dropna(subset=["price_per_m2"])

                # Use only the latest snapshot per week
                latest_per_wk = (hist_m2.groupby(["iso_year", "iso_week"])["snapshot_date"]
                                 .max().reset_index(name="_latest"))
                hist_m2 = hist_m2.merge(latest_per_wk, on=["iso_year", "iso_week"])
                hist_m2 = hist_m2[hist_m2["snapshot_date"] == hist_m2["_latest"]].drop(columns=["_latest"])

                # Set groupby keys based on granularity
                if granularity == "Weekly":
                    time_cols = ["iso_year", "iso_week"]
                elif granularity == "Monthly":
                    time_cols = ["month"]
                elif granularity == "Quarterly":
                    time_cols = ["quarter"]
                else:  # YTD
                    time_cols = ["year"]

                # Per-product mean $/m² across sizes, then per-tech mean across products
                prod_agg = (
                    hist_m2.groupby(time_cols + ["product_id", "color_architecture"])["price_per_m2"]
                    .mean().reset_index()
                )
                period_agg = (
                    prod_agg.groupby(time_cols + ["color_architecture"])["price_per_m2"]
                    .mean().reset_index()
                )

                # Build sortable period label
                if granularity == "Weekly":
                    n_years = period_agg["iso_year"].nunique()
                    if n_years <= 1:
                        period_agg["Period"] = "Wk " + period_agg["iso_week"].astype(str)
                        period_agg["_sort"] = period_agg["iso_week"]
                    else:
                        period_agg["Period"] = period_agg["iso_year"].astype(str) + " Wk " + period_agg["iso_week"].astype(str)
                        period_agg["_sort"] = period_agg["iso_year"] * 100 + period_agg["iso_week"]
                elif granularity == "Monthly":
                    period_agg["Period"] = period_agg["month"]
                    period_agg["_sort"] = period_agg["month"]
                elif granularity == "Quarterly":
                    period_agg["Period"] = period_agg["quarter"]
                    period_agg["_sort"] = period_agg["quarter"]
                else:  # YTD
                    period_agg["Period"] = period_agg["year"].astype(str)
                    period_agg["_sort"] = period_agg["year"]

                period_agg = period_agg.sort_values("_sort")
                period_agg.rename(columns={"color_architecture": "Technology",
                                           "price_per_m2": "Avg $/m²"}, inplace=True)

                n_periods = period_agg["Period"].nunique()

                fig = px.line(
                    period_agg, x="Period", y="Avg $/m²",
                    color="Technology", color_discrete_map=TECH_COLORS,
                    markers=True,
                    labels={"Avg $/m²": "Avg $/m²", "Period": ""},
                    category_orders={"Period": period_agg["Period"].unique().tolist(),
                                     "Technology": TECH_ORDER},
                )
                fig.update_traces(marker=dict(size=10))
                fig.update_layout(height=500, legend_title_text="Technology",
                                  xaxis=dict(type="category"), **PL)
                if n_periods == 1:
                    st.caption(f"Only one {granularity.lower()} period of data.")
                st.plotly_chart(fig, use_container_width=True)

                # Optional size filter for a second chart
                available_sizes = sorted(hist_m2["size_inches"].dropna().unique())
                if len(available_sizes) > 1:
                    size_filter = st.selectbox(
                        "Filter by screen size",
                        ["All sizes"] + [f'{int(s)}"' for s in available_sizes],
                        key="history_size_filter",
                    )
                    if size_filter != "All sizes":
                        size_val = int(size_filter.replace('"', ''))
                        hist_sized = hist_m2[hist_m2["size_inches"] == size_val]
                        sized_agg = (
                            hist_sized.groupby(time_cols + ["color_architecture"])["price_per_m2"]
                            .mean().reset_index()
                        )
                        # Reuse same period labeling logic
                        if granularity == "Weekly":
                            if sized_agg["iso_year"].nunique() <= 1:
                                sized_agg["Period"] = "Wk " + sized_agg["iso_week"].astype(str)
                                sized_agg["_sort"] = sized_agg["iso_week"]
                            else:
                                sized_agg["Period"] = sized_agg["iso_year"].astype(str) + " Wk " + sized_agg["iso_week"].astype(str)
                                sized_agg["_sort"] = sized_agg["iso_year"] * 100 + sized_agg["iso_week"]
                        elif granularity == "Monthly":
                            sized_agg["Period"] = sized_agg["month"]
                            sized_agg["_sort"] = sized_agg["month"]
                        elif granularity == "Quarterly":
                            sized_agg["Period"] = sized_agg["quarter"]
                            sized_agg["_sort"] = sized_agg["quarter"]
                        else:
                            sized_agg["Period"] = sized_agg["year"].astype(str)
                            sized_agg["_sort"] = sized_agg["year"]
                        sized_agg = sized_agg.sort_values("_sort")
                        sized_agg.rename(columns={"color_architecture": "Technology",
                                                  "price_per_m2": "Avg $/m²"}, inplace=True)
                        fig2 = px.line(
                            sized_agg, x="Period", y="Avg $/m²",
                            color="Technology", color_discrete_map=TECH_COLORS,
                            markers=True,
                            labels={"Avg $/m²": f'Avg $/m² \u2014 {size_filter}', "Period": ""},
                            category_orders={"Period": sized_agg["Period"].unique().tolist(),
                                             "Technology": TECH_ORDER},
                        )
                        fig2.update_traces(marker=dict(size=10))
                        fig2.update_layout(height=450, legend_title_text="Technology",
                                          xaxis=dict(type="category"), **PL)
                        st.plotly_chart(fig2, use_container_width=True)

    with tab5:
        st.subheader("Channel Analysis")
        st.caption("Where to find the best prices by display technology. "
                   "Amazon combines 1P (sold by Amazon) and 3P (third-party sellers). "
                   "RTINGS affiliate prices are used as fallback when no live API data is available.")

        if "channel" not in priced.columns:
            st.info("No channel data available.")
        else:
            # --- Channel wins by technology ---
            chan_tech = (priced.groupby(["color_architecture", "channel"], observed=True)
                        .size().reset_index(name="count"))
            # Compute % within each technology
            tech_totals = chan_tech.groupby("color_architecture", observed=True)["count"].transform("sum")
            chan_tech["pct"] = (chan_tech["count"] / tech_totals * 100).round(0)

            CHANNEL_COLORS = {
                "Amazon": "#FF9900",
                "Best Buy": "#0046BE",
                "RTINGS (affiliate)": "#666666",
            }

            fig = px.bar(chan_tech, x="color_architecture", y="pct", color="channel",
                         color_discrete_map=CHANNEL_COLORS,
                         category_orders={"color_architecture": TECH_ORDER},
                         text="pct", barmode="stack",
                         labels={"color_architecture": "Technology", "pct": "% of Best Prices",
                                 "channel": "Channel"})
            fig.update_traces(texttemplate="%{text:.0f}%", textposition="inside",
                              textfont_size=12)
            fig.update_layout(height=400, legend_title_text="Channel",
                              yaxis=dict(range=[0, 105], title="% of Best Prices"), **PL)
            st.plotly_chart(fig, use_container_width=True)

            # --- QD channel breakdown ---
            st.markdown("**Best Channel for QD-Based TVs**")
            qd_techs = ["QD-LCD", "QD-OLED", "Pseudo QD"]
            qd_priced = priced[priced["color_architecture"].isin(qd_techs)]
            if len(qd_priced) > 0:
                qd_channels = (qd_priced.groupby("channel")
                               .agg(wins=("channel", "size"),
                                    avg_price=("price_best", "mean"),
                                    median_price=("price_best", "median"))
                               .sort_values("wins", ascending=False)
                               .reset_index())
                qd_channels["avg_price"] = qd_channels["avg_price"].apply(lambda x: f"${x:,.0f}")
                qd_channels["median_price"] = qd_channels["median_price"].apply(lambda x: f"${x:,.0f}")
                qd_channels.columns = ["Channel", "Best Price Wins", "Avg Price", "Median Price"]
                st.dataframe(qd_channels, use_container_width=True, hide_index=True)

            # --- Size-level channel analysis from tv_prices.csv ---
            if len(prices_df) > 0:
                st.markdown("**Channel Coverage by Size**")
                st.caption("Number of size/model combinations with pricing from each channel, "
                           "across the full tv_prices dataset.")
                sized = prices_df[prices_df["best_price"].notna()].copy()
                if "price_source" in sized.columns:
                    sized["channel"] = sized["price_source"].replace({
                        "amazon": "Amazon", "amazon_3p": "Amazon",
                        "bestbuy": "Best Buy", "rtings": "RTINGS (affiliate)",
                    })
                    size_chan = (sized.groupby(["size_inches", "channel"])
                                .size().reset_index(name="count"))
                    fig = px.bar(size_chan, x="size_inches", y="count", color="channel",
                                 color_discrete_map=CHANNEL_COLORS,
                                 barmode="group",
                                 labels={"size_inches": "Screen Size (inches)",
                                         "count": "Price Points", "channel": "Channel"})
                    fig.update_layout(height=400, legend_title_text="Channel", **PL)
                    st.plotly_chart(fig, use_container_width=True)
