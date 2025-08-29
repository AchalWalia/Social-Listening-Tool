from __future__ import annotations

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import time
from typing import Optional

import pandas as pd
import streamlit as st

from app.analysis.sentiment import analyze_unlabeled_mentions
from app.config import BASE_DIR
from app.db.database import (
    fetch_mentions_dataframe,
    get_connection,
    get_or_create_company,
    get_platform_rating_summary,
    get_platform_store_review_totals,
    get_platform_review_counts,
)
from app.harvesters.apple_app_store import harvest_apple_app_store
from app.harvesters.google_play import harvest_google_play
from app.harvesters.google_trends import harvest_google_trends, get_search_volume_summary
from app.harvesters.reddit import harvest_reddit
from app.harvesters.youtube import harvest_youtube
from app.harvesters.social_media_integration import harvest_with_social_integration
from app.ui.components import render_data_explorer, render_metrics, render_source_filter, render_themes

st.set_page_config(page_title="Aura - Social Listening Tool", page_icon="👂", layout="wide")

st.title("👂 Aura - Social Listening Tool")
st.markdown("*Monitor what people are saying about your company across the web*")

# Initialize database connection
connection = get_connection()

# Sidebar for company selection with enhanced options
with st.sidebar:
    st.header("🎯 Company Analysis")
    
    # User guidance
    st.info("**Two ways to analyze:**\n"
            "1. 🌐 **Website Analysis**: Automatically discover apps & social media\n"  
            "2. 📱 **Manual App Analysis**: Enter app IDs directly")
    
    # Website Analysis Mode
    selected_company = None
    app_store_ids = None
    website_results = None
    
    # PRIMARY OPTION: Website Analysis with Auto-Detection
    st.markdown("### 🌐 **Website Analysis** (Recommended)")
    st.markdown("**Automatically discover your apps and social media from your website:**")
    
    website_url = st.text_input(
        "Company Website URL",
        placeholder="e.g., https://popclub.co or spotify.com",
        help="We'll analyze your website to automatically find your apps, social media, and value proposition"
    )
    
    if website_url and st.button("🔍 **Analyze Website**", type="primary"):
        try:
            from app.services.website_analyzer import analyze_website
            with st.spinner("🔍 Analyzing website for apps and social media..."):
                website_results = analyze_website(website_url)
                
                if website_results['success']:
                    st.success("✅ **Website analysis complete!**")
                    
                    # Extract company name from URL
                    from urllib.parse import urlparse
                    parsed_url = urlparse(website_results['url'])
                    company_name = parsed_url.netloc.replace('www.', '').split('.')[0].title()
                    
                    # Create company object
                    class CompanyCandidate:
                        def __init__(self, name, domain=None):
                            self.name = name
                            self.domain = domain
                    
                    domain = parsed_url.netloc.replace('www.', '')
                    selected_company = CompanyCandidate(company_name, domain)
                    
                    # Show discovered information
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**💡 Value Proposition**")
                        st.info(website_results['value_proposition'])
                        
                        st.markdown("**🔗 Social Media**")
                        social_links = website_results.get('social_links', {})
                        if social_links:
                            for platform, url in social_links.items():
                                st.markdown(f"• [{platform.title()}]({url})")
                        else:
                            st.markdown("*No social media found*")
                    
                    with col2:
                        st.markdown("**📱 App Store Links**")
                        if website_results.get('has_app_store_links'):
                            app_store_ids = {
                                'apple_app_id': website_results['app_store_links'].get('apple_app_id'),
                                'google_play_package': website_results['app_store_links'].get('google_play_package')
                            }
                            
                            if app_store_ids.get('apple_app_id'):
                                st.success(f"🍎 **Apple App Store**: {app_store_ids['apple_app_id']}")
                            if app_store_ids.get('google_play_package'):
                                st.success(f"🤖 **Google Play**: {app_store_ids['google_play_package']}")
                            
                            st.success(f"✅ **Ready to analyze {company_name}** with auto-detected apps!")
                        else:
                            st.warning("⚠️ No app store links found on website")
                            st.info("👇 You can enter app IDs manually below")
                            app_store_ids = None
                else:
                    st.error(f"❌ Website analysis failed: {website_results['error']}")
        except Exception as e:
            st.error(f"❌ Website analysis error: {e}")
    
    # SECONDARY OPTION: Manual App ID Entry
    st.markdown("---")
    st.markdown("### 📱 **Manual App Analysis** (Fallback)")
    st.markdown("**Enter app store identifiers directly:**")
    
    with st.form("direct_app_analysis"):
        company_name_input = st.text_input(
            "Company Name",
            placeholder="e.g., POP Club",
            help="Enter your company name"
        )
        
        apple_app_id_input = st.text_input(
            "Apple App Store ID",
            placeholder="e.g., 6443502397",
            help="Numerical ID from App Store URL"
        )
        
        google_package_input = st.text_input(
            "Google Play Package Name",
            placeholder="e.g., com.popclub.android", 
            help="Package name from Play Store URL"
        )
        
        submitted = st.form_submit_button("📊 **START MANUAL ANALYSIS**", type="secondary")
        
        if submitted and (apple_app_id_input.strip() or google_package_input.strip()):
            if not company_name_input.strip():
                st.error("Please enter a company name")
            else:
                # Create company object
                class CompanyCandidate:
                    def __init__(self, name, domain=None):
                        self.name = name
                        self.domain = domain
                
                selected_company = CompanyCandidate(company_name_input.strip())
                app_store_ids = {
                    'apple_app_id': apple_app_id_input.strip() if apple_app_id_input.strip() else None,
                    'google_play_package': google_package_input.strip() if google_package_input.strip() else None
                }
                
                st.success(f"✅ **Ready to analyze**: {selected_company.name}")
                st.success(f"📱 **App IDs**: {app_store_ids}")
        elif submitted:
            st.error("Please enter at least one app store identifier")

    # THIRD OPTION: Standalone Google Search Analytics
    st.markdown("---")
    st.markdown("### 🔎 **Run Google Search Analytics** (Standalone)")
    st.markdown("**Analyze Google search interest for any keyword:**")
    
    with st.form("google_search_analysis"):
        trends_keyword = st.text_input(
            "Keyword to analyze",
            placeholder="e.g., POP Club, Spotify, food delivery",
            help="Enter a brand, product, or topic keyword"
        )
        timeframe = st.selectbox(
            "Timeframe",
            ["today 12-m", "today 3-m", "today 5-y", "all"],
            index=0,
            help="Select the Google Trends timeframe"
        )
        run_trends = st.form_submit_button("📈 **RUN GOOGLE SEARCH ANALYSIS**", type="secondary")
        if run_trends:
            if not trends_keyword.strip():
                st.error("Please enter a keyword to analyze")
            else:
                try:
                    with st.spinner("Fetching Google Trends data (India)..."):
                        trends_data = harvest_google_trends(trends_keyword.strip(), timeframe=timeframe, geo="IN")
                        # Persist in session for rendering on the main panel
                        st.session_state["trends_keyword"] = trends_keyword.strip()
                        st.session_state["trends_timeframe"] = timeframe
                        st.session_state["trends_data"] = trends_data
                        st.success("✅ Google search analysis complete. See results in the main panel below.")
                except Exception as e:
                    st.error(f"❌ Google Trends error: {e}")

# Continue with data collection if we have a selected company
if selected_company:
    st.success(f"Selected: **{selected_company.name}**")
    
    # Get or create company in database
    company_id = get_or_create_company(
        connection, 
        selected_company.name, 
        getattr(selected_company, 'domain', None)
    )
    
    st.info(f"🏢 Company ID: {company_id}")
    
    st.header("📊 Data Collection")
    
    # DIRECT COLLECTION - No complex button logic
    if app_store_ids and (app_store_ids.get('apple_app_id') or app_store_ids.get('google_play_package')):
        
        st.info("🚀 **Starting data collection automatically...**")
        
        # Collection results
        collection_results = {'google_play': 0, 'apple_app_store': 0, 'total': 0}
        
        # Collect from Google Play
        if app_store_ids.get('google_play_package'):
            with st.spinner("Collecting Google Play reviews..."):
                try:
                    gp_count = harvest_google_play(
                        connection, 
                        company_id, 
                        selected_company.name, 
                        package_ids=[app_store_ids['google_play_package']]
                    )
                    collection_results['google_play'] = gp_count
                    st.success(f"✅ Google Play: **{gp_count}** reviews collected")
                except Exception as e:
                    st.error(f"❌ Google Play error: {e}")
        
        # Collect from Apple App Store
        if app_store_ids.get('apple_app_id'):
            with st.spinner("Collecting Apple App Store reviews..."):
                try:
                    apple_count = harvest_apple_app_store(
                        connection,
                        company_id,
                        selected_company.name,
                        app_ids=[app_store_ids['apple_app_id']]
                    )
                    collection_results['apple_app_store'] = apple_count
                    st.success(f"✅ Apple App Store: **{apple_count}** reviews collected")
                except Exception as e:
                    st.error(f"❌ Apple App Store error: {e}")
        
        # Summary
        collection_results['total'] = collection_results['google_play'] + collection_results['apple_app_store']
        
        if collection_results['total'] > 0:
            st.success(f"🎉 **COLLECTION COMPLETE!** Total: **{collection_results['total']}** reviews")
            
            # Show metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Google Play Reviews", collection_results['google_play'])
            with col2:
                st.metric("Apple App Store Reviews", collection_results['apple_app_store'])  
            with col3:
                st.metric("Total Reviews", collection_results['total'])
            
            st.info("📊 **Dashboard will load below with your collected data**")
        else:
            st.warning("No reviews were collected. Please check your app IDs.")
    else:
        st.info("👆 **Enter your app IDs above to start data collection**")

# Main dashboard
if 'selected_company' in locals() and selected_company and 'company_id' in locals():
    st.header("🎛️ Aura Dashboard")
    
    # Show website analysis results if available
    if 'website_results' in locals() and website_results and website_results.get('success'):
        with st.expander("🌐 Website Analysis Results", expanded=False):
            st.markdown("### 💡 Value Proposition")
            st.info(website_results['value_proposition'])
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**🔗 Social Media Links**")
                social_links = website_results.get('social_links', {})
                if social_links:
                    for platform, url in social_links.items():
                        st.markdown(f"• [{platform.title()}]({url})")
                else:
                    st.markdown("*No social media links found*")
            
            with col2:
                st.markdown("**📱 App Store Links**")
                app_links = website_results.get('app_store_links', {})
                if app_links:
                    if 'apple_url' in app_links:
                        st.markdown(f"• [Apple App Store]({app_links['apple_url']})")
                    if 'google_play_url' in app_links:
                        st.markdown(f"• [Google Play Store]({app_links['google_play_url']})")
                else:
                    st.markdown("*No app store links found*")
    
    # Fetch current data
    df = fetch_mentions_dataframe(connection, company_id)
    ratings_summary = get_platform_rating_summary(connection, company_id)
    review_counts = get_platform_review_counts(connection, company_id)
    store_totals = get_platform_store_review_totals(connection, company_id)
    
    st.info(f"📊 Dashboard for: **{selected_company.name}** | Found **{len(df)}** mentions")
    
    # Do not auto-run Google Trends here; only show if user ran it
    trends_data = st.session_state.get('trends_data')
    search_volume_summary = None
    if trends_data:
        try:
            search_volume_summary = get_search_volume_summary(trends_data)
        except Exception:
            search_volume_summary = None
    
    # Show dashboard based on data availability
    if len(df) == 0:
        st.warning("📊 **No data available yet**")
        st.info("👆 Use the form above to collect reviews!")
        
        # Show empty metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Mentions", "0")
        with col2:
            st.metric("Positive Sentiment", "0%")
        with col3:
            st.metric("Google Play Rating", "N/A", "0 reviews")
        with col4:
            st.metric("App Store Rating", "N/A", "0 reviews")
        with col5:
            st.metric("Avg Search Volume", "N/A")
    else:
        # Normal dashboard with data
        st.success(f"✅ **Dashboard loaded with {len(df)} mentions**")
        
        # Source filter
        selected_source = render_source_filter(df)
        
        # Filter dataframe based on selected source
        if selected_source != "All Sources" and not df.empty:
            df_display = df[df["source"] == selected_source]
        else:
            df_display = df
        
        # Render metrics (search volume shown only if available from standalone run)
        render_metrics(df_display, ratings_summary, search_volume_summary, review_counts, store_totals)
        
        # Render themes analysis
        render_themes(df_display)
        
        # Data explorer
        render_data_explorer(df_display, selected_source)

else:
    # Welcome message for new users
    st.markdown("## 🚀 Welcome to Aura!")
    st.markdown("""
    **Get started by choosing an analysis method in the sidebar:**
    
    ### 🌐 Website Analysis (Recommended)
    - **Automatic Discovery**: Finds your apps, social media, and value proposition
    - **Comprehensive**: Analyzes your website as the source of truth
    - **Smart**: Extracts app store links and package IDs automatically
    
    ### 📱 Manual App Analysis  
    - **Direct**: Enter app store identifiers manually
    - **Quick**: Fast setup when you know your app IDs
    - **Flexible**: Works for any app store configuration
    
    👈 **Choose your preferred method in the sidebar to begin!**
    """)
    
    # Show example of what website analysis can do
    with st.expander("🔍 See what Website Analysis can discover", expanded=False):
        st.markdown("""
        **From your website URL, we automatically extract:**
        
        ✅ **Value Proposition** - AI-generated summary of what your company does  
        ✅ **Social Media Links** - Twitter, Instagram, YouTube profiles  
        ✅ **App Store Links** - Apple App Store and Google Play Store apps  
        ✅ **Package IDs** - Automatic extraction for seamless app review analysis  
        
        **Example**: Enter `spotify.com` and we'll find:
        - Value proposition about music streaming
        - Links to @spotify on Twitter, Instagram
        - Spotify app on both app stores with correct package IDs
        - Ready for immediate review analysis!
        """) 

# Standalone Google Trends results section (always visible if session has data)
if st.session_state.get("trends_data"):
    td = st.session_state["trends_data"]
    st.markdown("---")
    st.header("📈 Google Search Analytics")
    st.info(f"Keyword: **{st.session_state.get('trends_keyword', td.get('company_name',''))}** | Timeframe: **{st.session_state.get('trends_timeframe', td.get('timeframe',''))}**")
    summary = get_search_volume_summary(td)
    colA, colB, colC, colD = st.columns(4)
    with colA:
        st.metric("Avg Interest", summary.get('avg_search_volume', 0))
    with colB:
        st.metric("Peak Interest", summary.get('peak_search_volume', 0))
    with colC:
        st.metric("Data Points", summary.get('data_points', 0))
    with colD:
        st.metric("Trend", summary.get('trend_direction', 'N/A'))

    # Show related queries and top regions
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**🔍 Top Related Queries**")
        for q in summary.get('related_queries', [])[:5]:
            st.markdown(f"• {q}")
    with c2:
        label = "**🌍 Top States (India)**" if td.get('geo') == 'IN' else "**🌍 Top Regions**"
        st.markdown(label)
        for region, score in list(summary.get('top_regions', {}).items())[:10]:
            st.markdown(f"• {region}: {score}/100")