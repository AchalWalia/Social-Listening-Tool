"""
UI Components for Website-Based Company Onboarding

This module provides Streamlit UI components for the enhanced company onboarding
workflow that uses website URLs instead of company names.
"""

import streamlit as st
import requests
from typing import Dict, Optional, Tuple
from app.services.website_analyzer import analyze_website


def render_website_input_form() -> Optional[str]:
    """
    Render the website URL input form
    
    Returns:
        The entered URL if submitted, None otherwise
    """
    st.markdown("Enter your company's website URL to automatically discover apps, social media, and value proposition:")
    
    with st.form("website_url_form"):
        url_input = st.text_input(
            "Company Website URL",
            placeholder="e.g., glowwidget.com or https://www.example.com",
            help="We'll analyze your website to automatically find your apps, social media profiles, and create a value proposition summary."
        )
        
        submitted = st.form_submit_button("🔍 Analyze Website", type="primary")
        
        if submitted and url_input.strip():
            return url_input.strip()
    
    return None


def render_website_analysis_progress(url: str) -> Dict[str, any]:
    """
    Show progress during website analysis and return results
    
    Args:
        url: The website URL being analyzed
        
    Returns:
        Analysis results dictionary
    """
    progress_container = st.container()
    
    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Step 1: URL Validation
        status_text.text("🔍 Validating website URL...")
        progress_bar.progress(25)
        
        # Perform the analysis
        results = analyze_website(url)
        
        if not results['success']:
            progress_bar.progress(100)
            if results['stage'] == 'validation':
                status_text.error(f"❌ URL Validation Failed: {results['error']}")
            else:
                status_text.error(f"❌ Website Analysis Failed: {results['error']}")
            return results
        
        # Step 2: Content Scraping
        status_text.text("📄 Scraping website content...")
        progress_bar.progress(50)
        
        # Step 3: Analyzing Content
        status_text.text("🤖 Analyzing content and extracting links...")
        progress_bar.progress(75)
        
        # Step 4: Complete
        status_text.text("✅ Analysis complete!")
        progress_bar.progress(100)
        
        # Clear progress after a moment
        import time
        time.sleep(1)
        progress_container.empty()
    
    return results


def render_website_analysis_results(results: Dict[str, any]) -> None:
    """
    Display the website analysis results
    
    Args:
        results: The analysis results from analyze_website()
    """
    if not results['success']:
        st.error(f"Analysis failed: {results['error']}")
        return
    
    st.success(f"✅ Successfully analyzed: {results['url']}")
    
    # Value Proposition Summary
    st.markdown("### 💡 Value Proposition")
    st.info(results['value_proposition'])
    
    # Social Media Links
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📱 Social Media Presence")
        social_links = results['social_links']
        
        if social_links:
            # Enhanced emoji mapping
            platform_emojis = {
                'twitter': '🐦',
                'x': '❌',  # X (formerly Twitter)
                'instagram': '📸', 
                'youtube': '📺',
                'facebook': '📘',
                'linkedin': '💼',
                'tiktok': '🎵',
                'snapchat': '👻'
            }
            
            for platform, url in social_links.items():
                platform_emoji = platform_emojis.get(platform.lower(), '🔗')
                platform_name = platform.replace('_', ' ').title()
                st.markdown(f"{platform_emoji} **{platform_name}**: [{url}]({url})")
            
            st.success(f"🎉 Found {len(social_links)} social media links!")
        else:
            st.markdown("🔍 No social media links found on the website.")
    
    with col2:
        st.markdown("### 📱 App Store Presence")
        app_links = results['app_store_links']
        
        if app_links:
            # Display Apple App Store links
            if 'apple_app_id' in app_links:
                st.markdown(f"🍎 **Apple App Store**: [View App]({app_links['apple_url']})")
                st.code(f"App ID: {app_links['apple_app_id']}")
            elif 'apple_url' in app_links:
                st.markdown(f"🍎 **Apple App Store**: [View App]({app_links['apple_url']})")
            
            # Display Google Play Store links
            if 'google_play_package' in app_links:
                st.markdown(f"🤖 **Google Play Store**: [View App]({app_links['google_play_url']})")
                st.code(f"Package: {app_links['google_play_package']}")
            elif 'google_play_url' in app_links:
                st.markdown(f"🤖 **Google Play Store**: [View App]({app_links['google_play_url']})")
            
            # Display smart links and other app store links
            for key, value in app_links.items():
                if key not in ['apple_app_id', 'apple_url', 'google_play_package', 'google_play_url']:
                    # Format the key for display
                    display_name = key.replace('_', ' ').title()
                    if 'smart' in key.lower():
                        st.markdown(f"🔗 **{display_name}**: [Universal App Link]({value})")
                    elif 'uber' in key.lower():
                        st.markdown(f"🚗 **{display_name}**: [Uber App Link]({value})")
                    else:
                        st.markdown(f"📱 **{display_name}**: [View App]({value})")
            
            st.success("🎉 Found app store links! Ready to analyze app reviews.")
        else:
            st.markdown("🔍 No app store links found on the website.")


def render_enhanced_manual_app_form(company_name: Optional[str] = None, discovered_ids: Optional[Dict[str, str]] = None) -> Optional[Dict[str, str]]:
    """
    Render enhanced manual app store ID form that's always available
    
    Args:
        company_name: Company name from website analysis (if available)
        discovered_ids: App IDs discovered from website analysis (if any)
    
    Returns:
        Dictionary with app store IDs and company name if submitted, None otherwise
    """
    st.markdown("### 📱 App Store Configuration")
    
    if discovered_ids:
        st.markdown("**Found apps from website analysis - you can modify or add more:**")
    else:
        st.markdown("**Enter your app store identifiers to analyze app reviews:**")
        st.markdown("💡 *You can proceed directly with app analysis without website analysis*")
    
    # Help section with examples
    with st.expander("📋 How to find App Store IDs", expanded=False):
        st.markdown("""
        **Apple App Store ID:**
        - Go to your app's App Store page
        - Look for the URL pattern: `apps.apple.com/.../id**123456789**`
        - Copy the numbers after "id": 
          - `apps.apple.com/in/app/pop-upi-credit-card-rewards/id**6443502397**` → `6443502397`
          - `apps.apple.com/us/app/spotify/id**324684580**` → `324684580`
        
        **Google Play Package Name:**
        - Go to your app's Play Store page  
        - Look for URL pattern: `play.google.com/store/apps/details?id=**com.company.appname**`
        - Copy the reverse domain format:
          - `...details?id=**com.popclub.android**` → `com.popclub.android`
          - `...details?id=**com.spotify.music**` → `com.spotify.music`
        """)
    
    with st.form("enhanced_app_form"):
        # Company name input (only if not already available)
        company_name_input = None
        if not company_name:
            company_name_input = st.text_input(
                "Company Name",
                placeholder="e.g., Spotify, Uber, Netflix",
                help="Enter your company name for the analysis"
            )
        
        # Pre-populate with discovered IDs if available
        default_apple_id = discovered_ids.get('apple_app_id', '') if discovered_ids else ''
        default_google_package = discovered_ids.get('google_play_package', '') if discovered_ids else ''
        
        apple_app_id = st.text_input(
            "Apple App Store ID",
            value=default_apple_id,
            placeholder="e.g., 324684580 (numbers only)",
            help="The numerical ID from your App Store URL (apps.apple.com/app/id123456789)"
        )
        
        google_play_package = st.text_input(
            "Google Play Package Name", 
            value=default_google_package,
            placeholder="e.g., com.spotify.music (reverse domain format)",
            help="The package name from your Play Store URL (play.google.com/store/apps/details?id=com.example)"
        )
        
        # Different button text based on context
        if discovered_ids:
            button_text = "🔄 Update & Analyze Apps"
        else:
            button_text = "📊 Analyze Apps"
        
        submitted = st.form_submit_button(button_text, type="primary")
        
        # Allow submission if we have either company name (existing or new) and at least one app ID
        has_company_name = company_name or (company_name_input and company_name_input.strip())
        has_app_ids = apple_app_id.strip() or google_play_package.strip()
        
        if submitted and has_app_ids:
            st.info(f"🔍 **FORM SUBMITTED** - has_company_name: {has_company_name}, has_app_ids: {has_app_ids}")
            st.info(f"Apple ID entered: '{apple_app_id.strip()}', Google package: '{google_play_package.strip()}'")
            
            # Validate app IDs before returning
            validation_errors = []
            validated_apple_id = None
            validated_google_package = None
            
            # Validate Apple App Store ID
            if apple_app_id.strip():
                if not apple_app_id.strip().isdigit():
                    validation_errors.append("❌ Apple App Store ID must contain only numbers")
                else:
                    validated_apple_id = apple_app_id.strip()
                    # Quick validation check with regional support
                    with st.spinner("🔍 Validating Apple App Store ID..."):
                        try:
                            # Try multiple regions for better coverage
                            found_app = False
                            regions = ['us', 'in', 'gb']  # US, India, UK
                            
                            for region in regions:
                                resp = requests.get(f"https://itunes.apple.com/lookup?id={validated_apple_id}&country={region}", timeout=10)
                                data = resp.json()
                                if data.get("results"):
                                    app_name = data["results"][0].get("trackName", "Unknown")
                                    country_name = {"us": "US", "in": "India", "gb": "UK"}.get(region, region.upper())
                                    st.success(f"✅ Found Apple app: **{app_name}** (Available in {country_name})")
                                    found_app = True
                                    break
                            
                            if not found_app:
                                # Still try without region for global apps
                                resp = requests.get(f"https://itunes.apple.com/lookup?id={validated_apple_id}", timeout=10)
                                data = resp.json()
                                if data.get("results"):
                                    app_name = data["results"][0].get("trackName", "Unknown")
                                    st.success(f"✅ Found Apple app: **{app_name}**")
                                    found_app = True
                            
                            if not found_app:
                                st.warning(f"⚠️ Could not validate Apple App Store ID '{validated_apple_id}' in common regions. The app may be region-specific or the ID might be incorrect.")
                                # Don't block the user - let them proceed if they're confident
                                
                        except Exception as e:
                            st.warning(f"⚠️ Could not validate Apple App Store ID due to network issues: {str(e)}. Proceeding anyway...")
            
            # Validate Google Play package name
            if google_play_package.strip():
                if not ('.' in google_play_package.strip() and len(google_play_package.strip().split('.')) >= 2):
                    validation_errors.append("❌ Google Play package name must contain dots (e.g., com.company.app)")
                else:
                    validated_google_package = google_play_package.strip()
                    # Quick validation check
                    with st.spinner("🔍 Validating Google Play package..."):
                        try:
                            from google_play_scraper import app as gp_app
                            app_data = gp_app(validated_google_package)
                            if app_data:
                                st.success(f"✅ Found Google Play app: **{app_data.get('title', 'Unknown')}**")
                        except Exception as e:
                            validation_errors.append(f"❌ Google Play package '{validated_google_package}' not found: {str(e)}")
            
            # Show validation errors or return valid data
            if validation_errors:
                for error in validation_errors:
                    st.error(error)
                st.warning("💡 **Tip**: Make sure your app IDs are correct. Use the help section above for guidance.")
                st.error("🚫 **FORM RETURNING NONE** - Validation failed")
                return None
            else:
                result = {
                    'apple_app_id': validated_apple_id,
                    'google_play_package': validated_google_package
                }
                
                # Add company name if we got it from the form
                if company_name_input and company_name_input.strip():
                    result['company_name'] = company_name_input.strip()
                
                st.success(f"✅ **FORM RETURNING DATA**: {result}")
                return result
        elif submitted and not has_app_ids:
            st.error("Please enter at least one app store identifier to proceed.")
            st.error("🚫 **FORM RETURNING NONE** - No app IDs provided")
    
    if submitted:
        st.error("🚫 **FORM RETURNING NONE** - Submitted but conditions not met")
    return None


def render_manual_app_override_form() -> Optional[Dict[str, str]]:
    """
    Render the manual app store ID override form
    
    Returns:
        Dictionary with app store IDs if submitted, None otherwise
    """
    st.markdown("### 📱 Manual App Store Configuration")
    st.markdown("If we couldn't find your app store links automatically, you can enter them manually below:")
    
    with st.form("manual_app_form"):
        st.markdown("**Optional: Enter your app store identifiers**")
        
        apple_app_id = st.text_input(
            "Apple App Store ID",
            placeholder="e.g., 472335316",
            help="The numerical ID from your App Store URL (apps.apple.com/app/id123456789)"
        )
        
        google_play_package = st.text_input(
            "Google Play Package Name", 
            placeholder="e.g., com.company.appname",
            help="The package name from your Play Store URL (play.google.com/store/apps/details?id=com.example)"
        )
        
        submitted = st.form_submit_button("📊 Analyze Apps", type="primary")
        
        if submitted and (apple_app_id.strip() or google_play_package.strip()):
            return {
                'apple_app_id': apple_app_id.strip() if apple_app_id.strip() else None,
                'google_play_package': google_play_package.strip() if google_play_package.strip() else None
            }
    
    return None


def render_website_onboarding_flow() -> Tuple[Optional[str], Optional[Dict[str, str]], Optional[Dict[str, any]]]:
    """
    Render the complete website-based onboarding flow with optional website analysis
    and always-available manual app ID input
    
    Returns:
        Tuple of (company_name, app_store_ids, website_analysis_results)
    """
    # Initialize session state
    if 'website_analysis_results' not in st.session_state:
        st.session_state.website_analysis_results = None
    if 'website_analysis_complete' not in st.session_state:
        st.session_state.website_analysis_complete = False
    
    company_name = None
    app_store_ids = None
    results = None
    
    # Step 1: Optional Website Analysis
    st.markdown("### 🌐 Website Analysis (Optional)")
    st.markdown("Analyze your company's website to automatically discover apps and social media:")
    
    if not st.session_state.website_analysis_complete:
        url_input = render_website_input_form()
        
        if url_input:
            # Perform website analysis
            with st.spinner("Analyzing website..."):
                results = render_website_analysis_progress(url_input)
                st.session_state.website_analysis_results = results
                st.session_state.website_analysis_complete = True
                st.rerun()
    else:
        # Display existing results
        results = st.session_state.website_analysis_results
        
        if results and results['success']:
            # Show analysis results
            render_website_analysis_results(results)
            
            # Extract company name from URL
            from urllib.parse import urlparse
            parsed_url = urlparse(results['url'])
            company_name = parsed_url.netloc.replace('www.', '').split('.')[0].title()
            
            # Check for discovered app store links
            if results['has_app_store_links']:
                st.success("🎉 Found app store links from website analysis!")
                discovered_ids = {
                    'apple_app_id': results['app_store_links'].get('apple_app_id'),
                    'google_play_package': results['app_store_links'].get('google_play_package')
                }
            
            # Add reset button
            if st.button("🔄 Analyze Different Website", type="secondary"):
                st.session_state.website_analysis_complete = False
                st.session_state.website_analysis_results = None
                st.rerun()
        else:
            # Reset and show error
            st.session_state.website_analysis_complete = False
            st.session_state.website_analysis_results = None
            if results:
                st.error(f"Website analysis failed: {results['error']}")
    
    # Step 2: Always Show Manual App ID Input
    st.markdown("---")
    manual_ids = render_enhanced_manual_app_form(
        company_name, 
        results['app_store_links'] if (results and results.get('has_app_store_links')) else None
    )
    
    # Determine final app_store_ids and company_name
    if manual_ids:
        app_store_ids = manual_ids
        # If no company name from website, ask for it
        if not company_name and 'company_name' in manual_ids:
            company_name = manual_ids['company_name']
    elif results and results.get('has_app_store_links'):
        app_store_ids = {
            'apple_app_id': results['app_store_links'].get('apple_app_id'),
            'google_play_package': results['app_store_links'].get('google_play_package')
        }
    
    return company_name, app_store_ids, results


def render_legacy_company_input() -> Optional[str]:
    """
    Render the legacy company name input (fallback option)
    
    Returns:
        Company name if entered, None otherwise
    """
    st.markdown("### 🏢 Quick Company Analysis")
    st.markdown("Enter a company name for basic analysis (legacy mode):")
    
    company_name = st.text_input(
        "Company Name",
        placeholder="e.g., Netflix, Spotify, Uber",
        help="Enter the company name for basic social listening analysis"
    )
    
    if company_name.strip():
        return company_name.strip()
    
    return None 