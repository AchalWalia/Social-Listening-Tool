"""
Intelligent app mapping service for company-to-app identification.
Handles cases where company names differ from app developers or app names.
"""

from typing import Dict, List, Optional, Set
import re


class AppMappingService:
    """
    Service to intelligently map company names to their mobile apps.
    Handles various naming conventions and aliases.
    """
    
    def __init__(self):
        # Known company-to-app mappings
        self.company_mappings = {
            # Social Media
            "meta": {
                "aliases": ["facebook", "meta platforms", "facebook inc"],
                "google_play": ["com.facebook.katana", "com.instagram.android", "com.whatsapp", "com.facebook.orca"],
                "app_store_terms": ["facebook", "instagram", "whatsapp", "messenger"],
                "developers": ["Meta Platforms, Inc.", "Facebook, Inc.", "WhatsApp Inc."]
            },
            "bytedance": {
                "aliases": ["tiktok", "byte dance"],
                "google_play": ["com.zhiliaoapp.musically", "com.ss.android.ugc.trill"],
                "app_store_terms": ["tiktok", "capcut"],
                "developers": ["TikTok Ltd.", "ByteDance Ltd."]
            },
            "twitter": {
                "aliases": ["x", "x corp"],
                "google_play": ["com.twitter.android"],
                "app_store_terms": ["twitter", "x"],
                "developers": ["Twitter, Inc.", "X Corp."]
            },
            
            # Streaming
            "netflix": {
                "aliases": ["netflix inc"],
                "google_play": ["com.netflix.mediaclient"],
                "app_store_terms": ["netflix"],
                "developers": ["Netflix, Inc."]
            },
            "disney": {
                "aliases": ["walt disney", "disney plus", "disney+"],
                "google_play": ["com.disney.disneyplus"],
                "app_store_terms": ["disney", "disney+", "disney plus"],
                "developers": ["Disney"]
            },
            "spotify": {
                "aliases": ["spotify ab", "spotify technology"],
                "google_play": ["com.spotify.music"],
                "app_store_terms": ["spotify"],
                "developers": ["Spotify AB"]
            },
            
            # Tech Giants
            "google": {
                "aliases": ["alphabet", "alphabet inc"],
                "google_play": ["com.google.android.apps.maps", "com.google.android.youtube", "com.android.chrome", "com.google.android.gm"],
                "app_store_terms": ["google", "youtube", "gmail", "chrome", "google maps"],
                "developers": ["Google LLC"]
            },
            "apple": {
                "aliases": ["apple inc"],
                "google_play": ["com.apple.android.music"],
                "app_store_terms": ["apple", "apple music", "apple tv"],
                "developers": ["Apple"]
            },
            "microsoft": {
                "aliases": ["microsoft corporation"],
                "google_play": ["com.microsoft.office.outlook", "com.microsoft.teams", "com.skype.raider"],
                "app_store_terms": ["microsoft", "outlook", "teams", "skype", "office"],
                "developers": ["Microsoft Corporation"]
            },
            "amazon": {
                "aliases": ["amazon.com", "amazon inc"],
                "google_play": ["com.amazon.mShop.android.shopping", "com.amazon.avod.thirdpartyclient"],
                "app_store_terms": ["amazon", "prime video", "kindle"],
                "developers": ["Amazon Mobile LLC", "AMZN Mobile LLC"]
            },
            
            # Gaming
            "activision": {
                "aliases": ["activision blizzard", "blizzard"],
                "google_play": ["com.activision.callofduty.shooter"],
                "app_store_terms": ["call of duty", "activision"],
                "developers": ["Activision Publishing, Inc."]
            },
            "electronic arts": {
                "aliases": ["ea", "ea sports"],
                "google_play": ["com.ea.gp.fifamobile"],
                "app_store_terms": ["ea", "fifa", "madden"],
                "developers": ["Electronic Arts"]
            },
            
            # Finance
            "paypal": {
                "aliases": ["paypal holdings"],
                "google_play": ["com.paypal.android.p2pmobile"],
                "app_store_terms": ["paypal"],
                "developers": ["PayPal, Inc."]
            },
            "square": {
                "aliases": ["block", "block inc"],
                "google_play": ["com.squareup.cash"],
                "app_store_terms": ["cash app", "square"],
                "developers": ["Square, Inc.", "Block, Inc."]
            },
            
            # Ride Sharing
            "uber": {
                "aliases": ["uber technologies"],
                "google_play": ["com.ubercab", "com.ubercab.eats"],
                "app_store_terms": ["uber", "uber eats"],
                "developers": ["Uber Technologies, Inc."]
            },
            "lyft": {
                "aliases": ["lyft inc"],
                "google_play": ["me.lyft.android"],
                "app_store_terms": ["lyft"],
                "developers": ["Lyft, Inc."]
            },
            
            # E-commerce
            "shopify": {
                "aliases": ["shopify inc"],
                "google_play": ["com.shopify.mobile", "com.shopify.arrive"],
                "app_store_terms": ["shopify", "arrive"],
                "developers": ["Shopify Inc."]
            },
            
            # Communication
            "zoom": {
                "aliases": ["zoom video", "zoom communications"],
                "google_play": ["us.zoom.videomeetings"],
                "app_store_terms": ["zoom"],
                "developers": ["Zoom"]
            },
            "slack": {
                "aliases": ["slack technologies"],
                "google_play": ["com.Slack"],
                "app_store_terms": ["slack"],
                "developers": ["Slack Technologies, Inc."]
            },
            
            # Indian Companies
            "flipkart": {
                "aliases": ["flipkart internet"],
                "google_play": ["com.flipkart.android"],
                "app_store_terms": ["flipkart"],
                "developers": ["Flipkart"]
            },
            "paytm": {
                "aliases": ["one97 communications"],
                "google_play": ["net.one97.paytm"],
                "app_store_terms": ["paytm"],
                "developers": ["Paytm"]
            },
            "zomato": {
                "aliases": ["zomato limited"],
                "google_play": ["com.application.zomato"],
                "app_store_terms": ["zomato"],
                "developers": ["Zomato"]
            },
            "swiggy": {
                "aliases": ["bundl technologies"],
                "google_play": ["in.swiggy.android"],
                "app_store_terms": ["swiggy"],
                "developers": ["Swiggy"]
            },
            "ola": {
                "aliases": ["ani technologies", "ola cabs"],
                "google_play": ["com.olacabs.customer"],
                "app_store_terms": ["ola", "ola cabs"],
                "developers": ["ANI Technologies Pvt. Ltd."]
            }
        }
    
    def get_company_mapping(self, company_name: str) -> Optional[Dict]:
        """Get mapping data for a company name."""
        company_lower = company_name.lower().strip()
        
        # Direct match
        if company_lower in self.company_mappings:
            return self.company_mappings[company_lower]
        
        # Check aliases
        for company, data in self.company_mappings.items():
            aliases = [alias.lower() for alias in data.get("aliases", [])]
            if company_lower in aliases:
                return data
            
            # Partial match for company names
            if any(company_lower in alias or alias in company_lower for alias in aliases):
                return data
        
        return None
    
    def get_google_play_packages(self, company_name: str) -> List[str]:
        """Get known Google Play package IDs for a company."""
        mapping = self.get_company_mapping(company_name)
        return mapping.get("google_play", []) if mapping else []
    
    def get_app_store_search_terms(self, company_name: str) -> List[str]:
        """Get search terms for Apple App Store."""
        mapping = self.get_company_mapping(company_name)
        terms = mapping.get("app_store_terms", []) if mapping else []
        return terms + [company_name]  # Always include original company name
    
    def get_developer_names(self, company_name: str) -> List[str]:
        """Get known developer names for filtering search results."""
        mapping = self.get_company_mapping(company_name)
        developers = mapping.get("developers", []) if mapping else []
        return developers + [company_name]  # Always include original company name
    
    def generate_search_variations(self, company_name: str) -> List[str]:
        """Generate search term variations for a company."""
        variations = [company_name]
        
        # Add known aliases
        mapping = self.get_company_mapping(company_name)
        if mapping:
            variations.extend(mapping.get("aliases", []))
        
        # Add common variations
        base_name = company_name.lower()
        
        # Remove common suffixes
        suffixes_to_remove = [" inc", " corp", " corporation", " ltd", " limited", " llc", " technologies", " technology"]
        for suffix in suffixes_to_remove:
            if base_name.endswith(suffix):
                clean_name = base_name[:-len(suffix)].strip()
                variations.append(clean_name)
        
        # Add "app" suffix
        variations.append(f"{company_name} app")
        variations.append(f"{company_name} mobile")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for var in variations:
            if var.lower() not in seen:
                unique_variations.append(var)
                seen.add(var.lower())
        
        return unique_variations
    
    def is_likely_match(self, company_name: str, app_title: str, developer_name: str) -> bool:
        """
        Determine if an app is likely from the given company.
        Uses fuzzy matching and known patterns.
        """
        company_lower = company_name.lower()
        app_title_lower = app_title.lower()
        developer_lower = developer_name.lower()
        
        # Get known mapping
        mapping = self.get_company_mapping(company_name)
        if mapping:
            # Check against known developers
            known_developers = [dev.lower() for dev in mapping.get("developers", [])]
            if any(dev in developer_lower or developer_lower in dev for dev in known_developers):
                return True
            
            # Check against known aliases
            aliases = [alias.lower() for alias in mapping.get("aliases", [])]
            if any(alias in app_title_lower or alias in developer_lower for alias in aliases):
                return True
        
        # Fallback to basic matching
        if (company_lower in app_title_lower or 
            company_lower in developer_lower or
            any(word in app_title_lower for word in company_lower.split() if len(word) > 2)):
            return True
        
        return False


# Global instance
app_mapping_service = AppMappingService() 