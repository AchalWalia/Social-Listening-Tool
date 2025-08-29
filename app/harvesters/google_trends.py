"""
Google Trends harvester for search volume data.
"""

import datetime
from typing import Dict, List, Optional, Tuple

import streamlit as st
from pytrends.request import TrendReq


def harvest_google_trends(company_name: str, timeframe: str = "today 12-m") -> Dict[str, any]:
    """
    Harvest Google Trends data for a company.
    
    Args:
        company_name: Name of the company to search for
        timeframe: Time period for trends data (default: last 12 months)
        
    Returns:
        Dictionary containing trends data including:
        - interest_over_time: DataFrame with search volume over time
        - average_interest: Average search interest score
        - peak_interest: Peak search interest score
        - related_queries: Related search queries
        - regional_interest: Geographic distribution of search interest
        - suggestions: Search term suggestions
    """
    try:
        # Initialize pytrends
        pytrends = TrendReq(hl='en-US', tz=360)
        
        # Build payload for the company name
        kw_list = [company_name]
        pytrends.build_payload(kw_list, cat=0, timeframe=timeframe, geo='', gprop='')
        
        # Get interest over time
        interest_over_time_df = pytrends.interest_over_time()
        
        # Calculate metrics
        average_interest = 0
        peak_interest = 0
        search_volume_data = []
        total_searches = 0
        
        if not interest_over_time_df.empty and company_name in interest_over_time_df.columns:
            company_data = interest_over_time_df[company_name]
            average_interest = round(company_data.mean(), 1)
            peak_interest = int(company_data.max())
            total_searches = int(company_data.sum())
            
            # Convert to list of tuples for easier handling
            for date, value in company_data.items():
                search_volume_data.append({
                    'date': date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
                    'search_volume': int(value)
                })
        
        # Get regional interest (top countries/regions)
        regional_interest = {}
        try:
            regional_data = pytrends.interest_by_region(resolution='COUNTRY', inc_low_vol=True, inc_geo_code=False)
            if not regional_data.empty and company_name in regional_data.columns:
                # Get top 10 countries
                top_regions = regional_data[company_name].sort_values(ascending=False).head(10)
                regional_interest = {
                    region: int(value) for region, value in top_regions.items() if value > 0
                }
        except Exception as e:
            st.warning(f"Could not fetch regional interest: {e}")
            regional_interest = {}
        
        # Get related queries
        related_queries = {}
        try:
            related_queries_data = pytrends.related_queries()
            if company_name in related_queries_data and related_queries_data[company_name]['top'] is not None:
                top_queries = related_queries_data[company_name]['top']
                rising_queries = related_queries_data[company_name]['rising']
                
                related_queries = {
                    'top': top_queries['query'].head(10).tolist() if 'query' in top_queries.columns else [],
                    'rising': rising_queries['query'].head(5).tolist() if rising_queries is not None and 'query' in rising_queries.columns else []
                }
        except Exception as e:
            st.warning(f"Could not fetch related queries: {e}")
            related_queries = {'top': [], 'rising': []}
        
        # Get search suggestions
        suggestions = []
        try:
            suggestions = pytrends.suggestions(keyword=company_name)
            suggestions = [s['title'] for s in suggestions[:5]] if suggestions else []
        except Exception as e:
            st.warning(f"Could not fetch suggestions: {e}")
            suggestions = []
        
        # Calculate estimated absolute volumes (rough approximation)
        # Note: Google Trends provides relative data, absolute volumes are estimated
        estimated_monthly_searches = 0
        if average_interest > 0:
            # Very rough estimation based on typical search volumes
            # This is an approximation - real absolute volumes require paid tools
            if average_interest >= 80:
                estimated_monthly_searches = "1M+"
            elif average_interest >= 60:
                estimated_monthly_searches = "500K-1M"
            elif average_interest >= 40:
                estimated_monthly_searches = "100K-500K"
            elif average_interest >= 20:
                estimated_monthly_searches = "10K-100K"
            elif average_interest >= 10:
                estimated_monthly_searches = "1K-10K"
            elif average_interest >= 5:
                estimated_monthly_searches = "100-1K"
            else:
                estimated_monthly_searches = "<100"
        
        return {
            'company_name': company_name,
            'timeframe': timeframe,
            'search_volume_data': search_volume_data,
            'average_interest': average_interest,
            'peak_interest': peak_interest,
            'total_searches': total_searches,
            'estimated_monthly_searches': estimated_monthly_searches,
            'related_queries': related_queries,
            'regional_interest': regional_interest,
            'suggestions': suggestions,
            'total_data_points': len(search_volume_data),
            'status': 'success'
        }
        
    except Exception as e:
        # Handle rate limiting and other errors gracefully
        error_message = str(e)
        if "429" in error_message or "Too Many Requests" in error_message or "quota" in error_message.lower():
            st.warning("⚠️ Google Trends: Rate limit reached. This is common with Google's API. Skipping trends data for now.")
        elif "timeout" in error_message.lower() or "connection" in error_message.lower():
            st.warning("⚠️ Google Trends: Connection timeout. Skipping trends data for now.")
        else:
            st.warning(f"⚠️ Google Trends: {error_message}")
        
        return {
            'company_name': company_name,
            'timeframe': timeframe,
            'search_volume_data': [],
            'average_interest': 0,
            'peak_interest': 0,
            'total_searches': 0,
            'estimated_monthly_searches': "N/A",
            'related_queries': {'top': [], 'rising': []},
            'regional_interest': {},
            'suggestions': [],
            'total_data_points': 0,
            'status': 'error',
            'error': str(e)
        }


def get_search_volume_summary(trends_data: Dict[str, any]) -> Dict[str, any]:
    """
    Extract key metrics from trends data for dashboard display.
    
    Args:
        trends_data: Output from harvest_google_trends
        
    Returns:
        Dictionary with summary metrics
    """
    if trends_data['status'] != 'success':
        return {
            'avg_search_volume': 0,
            'peak_search_volume': 0,
            'total_search_volume': 0,
            'estimated_monthly_searches': 'N/A',
            'trend_direction': 'No data',
            'data_points': 0,
            'top_regions': {},
            'related_queries': [],
            'rising_queries': []
        }
    
    search_data = trends_data['search_volume_data']
    if not search_data:
        return {
            'avg_search_volume': 0,
            'peak_search_volume': 0,
            'total_search_volume': 0,
            'estimated_monthly_searches': 'N/A',
            'trend_direction': 'No data',
            'data_points': 0,
            'top_regions': {},
            'related_queries': [],
            'rising_queries': []
        }
    
    # Calculate trend direction (compare first and last quarter)
    values = [item['search_volume'] for item in search_data]
    trend_direction = 'Stable'
    
    if len(values) >= 8:  # Need at least 8 weeks of data
        first_quarter = sum(values[:len(values)//4]) / (len(values)//4)
        last_quarter = sum(values[-len(values)//4:]) / (len(values)//4)
        
        if last_quarter > first_quarter * 1.15:
            trend_direction = 'Rising'
        elif last_quarter < first_quarter * 0.85:
            trend_direction = 'Declining'
    
    # Safely extract related queries with proper error handling
    related_queries_data = trends_data.get('related_queries', {})
    related_queries = related_queries_data.get('top', [])[:3] if isinstance(related_queries_data, dict) else []
    rising_queries = related_queries_data.get('rising', [])[:3] if isinstance(related_queries_data, dict) else []
    
    return {
        'avg_search_volume': trends_data.get('average_interest', 0),
        'peak_search_volume': trends_data.get('peak_interest', 0),
        'total_search_volume': trends_data.get('total_searches', 0),
        'estimated_monthly_searches': trends_data.get('estimated_monthly_searches', 'N/A'),
        'trend_direction': trend_direction,
        'data_points': len(search_data),
        'top_regions': trends_data.get('regional_interest', {}),
        'related_queries': related_queries,
        'rising_queries': rising_queries
    } 