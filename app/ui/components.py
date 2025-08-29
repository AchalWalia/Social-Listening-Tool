"""
Reusable UI components for the Streamlit dashboard.
"""

from typing import Dict, List, Optional

import pandas as pd
import streamlit as st


def render_metrics(df: pd.DataFrame, ratings_summary: Dict[str, Dict[str, float]], search_volume_summary: Optional[Dict[str, any]] = None, review_counts: Optional[Dict[str, int]] = None, store_totals: Optional[Dict[str, int]] = None) -> None:
    """Render key metrics in the dashboard."""
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_mentions = len(df)
        st.metric("Total Mentions", total_mentions)
    
    with col2:
        if not df.empty and "sentiment_label" in df.columns:
            positive_count = len(df[df["sentiment_label"] == "POSITIVE"])
            sentiment_ratio = round((positive_count / total_mentions) * 100, 1) if total_mentions > 0 else 0
            st.metric("Positive Sentiment", f"{sentiment_ratio}%")
        else:
            st.metric("Positive Sentiment", "0%")
    
    with col3:
        # Google Play rating and counts
        gp_rating = ratings_summary.get("Google Play", {}).get("avg_rating", 0.0)
        gp_collected = review_counts.get("Google Play", 0) if review_counts else 0
        gp_total = store_totals.get("Google Play", 0) if store_totals else 0
        def _short(n: int) -> str:
            if n >= 1_000_000:
                return f"{n/1_000_000:.1f}M"
            if n >= 1_000:
                return f"{n/1_000:.1f}k"
            return f"{n}"
        delta = f"{_short(gp_total)} total | {_short(gp_collected)} collected" if gp_total else (f"{_short(gp_collected)} collected" if gp_collected else None)
        if gp_rating > 0:
            st.metric("Google Play Rating", f"{gp_rating}⭐", delta)
        else:
            st.metric("Google Play Rating", "N/A", delta or "No data")
    
    with col4:
        # Apple App Store rating and counts
        as_rating = ratings_summary.get("Apple App Store", {}).get("avg_rating", 0.0)
        as_collected = review_counts.get("Apple App Store", 0) if review_counts else 0
        as_total = store_totals.get("Apple App Store", 0) if store_totals else 0
        delta = f"{_short(as_total)} total | {_short(as_collected)} collected" if as_total else (f"{_short(as_collected)} collected" if as_collected else None)
        if as_rating > 0:
            st.metric("App Store Rating", f"{as_rating}⭐", delta)
        else:
            st.metric("App Store Rating", "N/A", delta or "No data")
    
    with col5:
        # Google Search Volume
        if search_volume_summary and search_volume_summary.get('avg_search_volume', 0) > 0:
            avg_volume = search_volume_summary['avg_search_volume']
            trend_direction = search_volume_summary.get('trend_direction', 'Stable')
            
            # Add trend indicator
            trend_icon = {
                'Rising': '📈',
                'Declining': '📉',
                'Stable': '➡️'
            }.get(trend_direction, '➡️')
            
            st.metric(
                "Avg Search Volume", 
                f"{avg_volume} {trend_icon}",
                help=f"12-month average Google search interest. Trend: {trend_direction}"
            )
        else:
            st.metric("Avg Search Volume", "N/A")
    
    # Display detailed search volume information
    if search_volume_summary and search_volume_summary.get('avg_search_volume', 0) > 0:
        with st.expander("📊 Detailed Search Volume Analytics"):
            # Create two columns for search metrics
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.write("**📈 Search Metrics:**")
                st.write(f"• **Average Interest**: {search_volume_summary['avg_search_volume']}/100")
                st.write(f"• **Peak Interest**: {search_volume_summary['peak_search_volume']}/100")
                st.write(f"• **Total Search Points**: {search_volume_summary['total_search_volume']}")
                st.write(f"• **Estimated Monthly Searches**: {search_volume_summary['estimated_monthly_searches']}")
                st.write(f"• **Trend Direction**: {search_volume_summary['trend_direction']} {trend_icon}")
            
            with col_b:
                st.write("**🌍 Top Search Regions:**")
                top_regions = search_volume_summary.get('top_regions', {})
                if top_regions:
                    for region, interest in list(top_regions.items())[:5]:
                        st.write(f"• **{region}**: {interest}/100")
                else:
                    st.write("• No regional data available")
            
            # Related and rising queries
            st.write("**🔍 Search Query Insights:**")
            col_c, col_d = st.columns(2)
            
            with col_c:
                st.write("*Top Related Queries:*")
                related_queries = search_volume_summary.get('related_queries', [])
                if related_queries:
                    for i, query in enumerate(related_queries, 1):
                        st.write(f"{i}. {query}")
                else:
                    st.write("No related queries found")
            
            with col_d:
                st.write("*Rising Queries:*")
                rising_queries = search_volume_summary.get('rising_queries', [])
                if rising_queries:
                    for i, query in enumerate(rising_queries, 1):
                        st.write(f"{i}. {query} 🔥")
                else:
                    st.write("No rising queries found")
            
            # Note about absolute volumes
            st.info(
                "📝 **Note**: Absolute search volumes are estimated based on relative Google Trends data. "
                "For precise absolute volumes, consider using Google Ads Keyword Planner or paid SEO tools."
            )


def render_themes(df: pd.DataFrame) -> None:
    """Render positive and negative theme analysis."""
    if df.empty or "sentiment_label" not in df.columns:
        st.info("No sentiment data available for theme analysis.")
        return

    from app.analysis.themes import compute_themes

    # Use the correct function signature
    positive_themes, negative_themes = compute_themes(df, top_k=8)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🌟 Positive Themes")
        if positive_themes:
            for theme, count in positive_themes:
                st.write(f"• **{theme}** ({count} mentions)")
        else:
            st.info("No positive themes found.")

    with col2:
        st.subheader("⚠️ Negative Themes")
        if negative_themes:
            for theme, count in negative_themes:
                st.write(f"• **{theme}** ({count} mentions)")
        else:
            st.info("No negative themes found.")


def render_source_filter(df: pd.DataFrame) -> str:
    """Render source filter dropdown and return selected source."""
    if df.empty or "source" not in df.columns:
        return "All Sources"
    
    available_sources = ["All Sources"] + sorted(df["source"].unique().tolist())
    selected_source = st.selectbox("Filter by Source:", available_sources)
    return selected_source


def render_data_explorer(df: pd.DataFrame, selected_source: str) -> None:
    """Render the data explorer section."""
    if df.empty:
        st.info("No data available.")
        return

    # Filter by source if not "All Sources"
    if selected_source != "All Sources":
        df_filtered = df[df["source"] == selected_source]
    else:
        df_filtered = df

    st.subheader("📊 Data Explorer")
    
    # Display summary
    st.write(f"Showing {len(df_filtered)} mentions" + (f" from {selected_source}" if selected_source != "All Sources" else ""))
    
    # Display columns for the table
    display_columns = ["source", "content", "author", "date", "rating", "sentiment_label", "sentiment_score"]
    available_columns = [col for col in display_columns if col in df_filtered.columns]
    
    if available_columns:
        st.dataframe(
            df_filtered[available_columns].head(100),  # Limit to 100 rows for performance
            use_container_width=True
        )
        
        if len(df_filtered) > 100:
            st.info(f"Showing first 100 of {len(df_filtered)} total mentions. Use filters to narrow down results.")
    else:
        st.warning("No displayable columns found in the data.") 