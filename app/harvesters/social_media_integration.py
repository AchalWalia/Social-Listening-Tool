"""
Social Media Integration Harvester

This module integrates discovered social media links from website analysis
with existing harvesters to provide more targeted data collection.
"""

from typing import Dict, List, Optional
import re
from urllib.parse import urlparse

from app.harvesters.youtube import harvest_youtube
from app.harvesters.reddit import harvest_reddit


class SocialMediaIntegrator:
    """Integrates discovered social media links with existing harvesters"""
    
    def __init__(self):
        self.supported_platforms = {
            'youtube': self._extract_youtube_info,
            'twitter': self._extract_twitter_info,
            'instagram': self._extract_instagram_info
        }
    
    def _extract_youtube_info(self, url: str) -> Dict[str, str]:
        """Extract YouTube channel/user information from URL"""
        info = {}
        
        # Pattern matching for different YouTube URL formats
        patterns = [
            r'youtube\.com/channel/([^/?]+)',      # /channel/UCxxxxx
            r'youtube\.com/c/([^/?]+)',            # /c/channelname
            r'youtube\.com/user/([^/?]+)',         # /user/username
            r'youtube\.com/@([^/?]+)',             # /@username
            r'youtube\.com/([^/?]+)',              # /channelname (direct)
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                identifier = match.group(1)
                if pattern.startswith(r'youtube\.com/channel/'):
                    info['channel_id'] = identifier
                    info['type'] = 'channel'
                elif pattern.startswith(r'youtube\.com/@'):
                    info['handle'] = identifier
                    info['type'] = 'handle'
                else:
                    info['username'] = identifier
                    info['type'] = 'user'
                break
        
        info['url'] = url
        return info
    
    def _extract_twitter_info(self, url: str) -> Dict[str, str]:
        """Extract Twitter/X account information from URL"""
        info = {}
        
        # Extract username from Twitter/X URL
        patterns = [
            r'(?:twitter\.com|x\.com)/([^/?]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                username = match.group(1)
                # Filter out common non-username paths
                if username.lower() not in ['intent', 'share', 'home', 'explore', 'notifications']:
                    info['username'] = username
                    info['url'] = url
                break
        
        return info
    
    def _extract_instagram_info(self, url: str) -> Dict[str, str]:
        """Extract Instagram account information from URL"""
        info = {}
        
        # Extract username from Instagram URL
        pattern = r'instagram\.com/([^/?]+)'
        match = re.search(pattern, url, re.IGNORECASE)
        
        if match:
            username = match.group(1)
            # Filter out common non-username paths
            if username.lower() not in ['p', 'reel', 'tv', 'stories', 'explore']:
                info['username'] = username
                info['url'] = url
        
        return info
    
    def extract_social_targets(self, social_links: Dict[str, str]) -> Dict[str, Dict[str, str]]:
        """
        Extract actionable information from discovered social media links
        
        Args:
            social_links: Dictionary of platform -> URL from website analysis
            
        Returns:
            Dictionary of platform -> extracted info for harvesting
        """
        targets = {}
        
        for platform, url in social_links.items():
            if platform in self.supported_platforms:
                extractor = self.supported_platforms[platform]
                info = extractor(url)
                
                if info:  # Only include if we successfully extracted info
                    targets[platform] = info
        
        return targets
    
    def harvest_from_social_links(
        self, 
        connection, 
        company_id: int, 
        company_name: str, 
        social_links: Dict[str, str]
    ) -> Dict[str, int]:
        """
        Harvest data from discovered social media links
        
        Args:
            connection: Database connection
            company_id: Company ID in database
            company_name: Company name
            social_links: Dictionary of platform -> URL from website analysis
            
        Returns:
            Dictionary of platform -> number of items harvested
        """
        results = {}
        
        # Extract actionable targets from social links
        targets = self.extract_social_targets(social_links)
        
        if not targets:
            print("🔍 No actionable social media targets found")
            return results
        
        print(f"🎯 Found {len(targets)} social media targets: {list(targets.keys())}")
        
        # YouTube harvesting with discovered channel info
        if 'youtube' in targets:
            youtube_info = targets['youtube']
            print(f"📺 Harvesting YouTube: {youtube_info}")
            
            try:
                # Use the existing YouTube harvester with enhanced search terms
                search_terms = [company_name]
                
                # Add channel-specific search terms
                if 'username' in youtube_info:
                    search_terms.append(youtube_info['username'])
                elif 'handle' in youtube_info:
                    search_terms.append(youtube_info['handle'])
                
                # For now, use the existing harvester (could be enhanced to use channel ID directly)
                youtube_count = harvest_youtube(connection, company_id, company_name)
                results['youtube'] = youtube_count
                print(f"✅ YouTube: {youtube_count} comments harvested")
                
            except Exception as e:
                print(f"❌ YouTube harvesting failed: {e}")
                results['youtube'] = 0
        
        # Twitter/X integration (placeholder for future implementation)
        if 'twitter' in targets:
            twitter_info = targets['twitter']
            print(f"🐦 Twitter target identified: @{twitter_info.get('username', 'unknown')}")
            print("ℹ️ Twitter integration not yet implemented (requires API access)")
            results['twitter'] = 0
        
        # Instagram integration (placeholder for future implementation)  
        if 'instagram' in targets:
            instagram_info = targets['instagram']
            print(f"📸 Instagram target identified: @{instagram_info.get('username', 'unknown')}")
            print("ℹ️ Instagram integration not yet implemented (requires API access)")
            results['instagram'] = 0
        
        # Reddit harvesting (enhanced with social context)
        print(f"🔍 Enhancing Reddit search with social media context")
        try:
            # Use existing Reddit harvester (could be enhanced with social context)
            reddit_count = harvest_reddit(connection, company_id, company_name)
            results['reddit'] = reddit_count
            print(f"✅ Reddit: {reddit_count} posts/comments harvested")
            
        except Exception as e:
            print(f"❌ Reddit harvesting failed: {e}")
            results['reddit'] = 0
        
        return results


def harvest_with_social_integration(
    connection, 
    company_id: int, 
    company_name: str, 
    social_links: Optional[Dict[str, str]] = None
) -> Dict[str, int]:
    """
    Main function to harvest social media data using discovered links
    
    Args:
        connection: Database connection
        company_id: Company ID in database
        company_name: Company name
        social_links: Optional dictionary of discovered social media links
        
    Returns:
        Dictionary of platform -> number of items harvested
    """
    integrator = SocialMediaIntegrator()
    
    if social_links:
        print(f"🌐 Using discovered social media links: {list(social_links.keys())}")
        return integrator.harvest_from_social_links(
            connection, company_id, company_name, social_links
        )
    else:
        print("🔍 No social media links provided, using standard harvesting")
        # Fallback to standard harvesting
        results = {}
        
        try:
            youtube_count = harvest_youtube(connection, company_id, company_name)
            results['youtube'] = youtube_count
        except Exception as e:
            print(f"❌ YouTube harvesting failed: {e}")
            results['youtube'] = 0
        
        try:
            reddit_count = harvest_reddit(connection, company_id, company_name)
            results['reddit'] = reddit_count
        except Exception as e:
            print(f"❌ Reddit harvesting failed: {e}")
            results['reddit'] = 0
        
        return results 