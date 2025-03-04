from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Iterable, Optional, Dict, List, Any

    from mov_cli import Config
    from mov_cli.http_client import HTTPClient
    from mov_cli.scraper import ScraperOptionsT

import json
import re
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

from mov_cli.utils import EpisodeSelector
from mov_cli import Scraper, Multi, Single, Metadata, MetadataType

__all__ = ("AnimePaheScraper",)

class AnimePaheScraper(Scraper):
    def __init__(self, config: Config, http_client: HTTPClient, options: Optional[ScraperOptionsT] = None) -> None:
        self.base_url = "https://animepahe.ru"
        self.api_url = f"{self.base_url}/api"
        self.search_url = f"{self.api_url}?m=search&q="
        self.release_url = f"{self.api_url}?m=release&id="
        self.play_url = f"{self.base_url}/play"
        self.headers = {"Referer": self.base_url}
        super().__init__(config, http_client, options)
        
    def _request(self, url: str, params: Optional[Dict] = None) -> Dict:
        response = self.http_client.get(url, headers=self.headers, params=params)
        return json.loads(response.text)
    
    def _request_html(self, url: str, params: Optional[Dict] = None) -> str:
        response = self.http_client.get(url, headers=self.headers, params=params)
        return response.text
        
    def search(self, query: str, limit: int = None) -> Iterable[Metadata]:
        response = self._request(f"{self.search_url}{quote_plus(query)}")
        animes = response.get("data", [])
        
        if limit is not None:
            animes = animes[:limit]
            
        for anime in animes:
            yield Metadata(
                id=anime["session"],
                title=anime["title"],
                type=MetadataType.MULTI if anime["episodes"] > 1 else MetadataType.SINGLE,
            )
    
    def scrape_episodes(self, metadata: Metadata) -> Dict[int | None, int]:
        # Get first page of episodes
        response = self._request(f"{self.release_url}{metadata.id}&sort=episode_asc&page=1")
        episodes = response.get("data", [])
        
        # Here we're not dealing with seasons, just mapping episode numbers
        episode_map = {}
        for ep in episodes:
            # Extract episode number from the title (e.g., "Episode 1" -> 1)
            episode_number = int(re.search(r"Episode (\d+)", ep.get("episode", "Episode 1")).group(1))
            episode_map[1] = episode_number  # Map to season 1
            
        if not episode_map:
            return {None: 1}
            
        return episode_map
    
    def _parse_kwik_link(self, url: str) -> str:
        # This follows the logic in animepahe.py to extract direct video URL
        # In a real implementation, you would use the CHARACTER_MAP, KWIK_PARAMS_RE, etc.
        # and implement the decrypt function as shown in animepahe.py
        
        # Simplified placeholder - in actual implementation you'd need the full kwik extraction logic
        html = self._request_html(url)
        soup = BeautifulSoup(html, "html.parser")
        
        # Find the Kwik URL
        script_tag = soup.find("script")
        match = re.search(r"https://kwik\.si/f/\w+", script_tag.string)
        
        # This would be a placeholder for the actual implementation
        # In reality, we would need to follow through with the kwik decryption
        # as shown in the animepahe.py file
        return match.group() if match else None
    
    def _extract_stream_url(self, kwik_url: str) -> str:
        # This is a placeholder for the kwik extraction process
        # In an actual implementation, you would implement the full decryption process from animepahe.py
        # Including the parse_m3u8_link logic
        return kwik_url  # Placeholder - would be the actual stream URL in implementation
    
    def scrape(self, metadata: Metadata, episode: EpisodeSelector) -> Multi | Single:
        # Get episodes list
        response = self._request(f"{self.release_url}{metadata.id}&sort=episode_asc&page=1")
        episodes_data = response.get("data", [])
        
        # Find the requested episode
        target_episode = None
        if metadata.type == MetadataType.MULTI:
            episode_num = episode.episode if episode and episode.episode else 1
            
            # Find the episode that matches the requested number
            for ep in episodes_data:
                ep_num = int(re.search(r"Episode (\d+)", ep.get("episode", "Episode 1")).group(1))
                if ep_num == episode_num:
                    target_episode = ep
                    break
        else:
            # For a single, just grab the first episode
            if episodes_data:
                target_episode = episodes_data[0]
        
        if not target_episode:
            raise ValueError(f"Episode {episode.episode} not found")
            
        # Get the episode page
        episode_session = target_episode["session"]
        episode_page_url = f"{self.play_url}/{metadata.id}/{episode_session}"
        episode_page_html = self._request_html(episode_page_url)
        
        # Parse the episode page to get download options
        soup = BeautifulSoup(episode_page_html, "html.parser")
        download_options = soup.find("div", {"id": "pickDownload"}).findAll("a")
        embed_sources = soup.find("div", {"id": "resolutionMenu"}).findAll("button")
        
        # Get the first download option (usually highest quality)
        if not download_options:
            raise ValueError("No download options found")
            
        download_url = download_options[0].get("href")
        embed_url = embed_sources[0].get("data-src")
        
        # In a full implementation, we would:
        # 1. Extract the kwik URL from the download page
        # 2. Decrypt the kwik URL to get the final mp4 URL
        # 3. Also extract the m3u8 stream URL from the embed source
        
        # For demonstration, we'll use a placeholder
        video_url = self._extract_stream_url(download_url)
        
        # Get subtitles (if available)
        subtitles = []  # Would extract subtitle links here if available
        
        # Episode title text
        episode_title = target_episode.get("episode", f"Episode {episode.episode}")
        
        if metadata.type == MetadataType.MULTI:
            return Multi(
                url=video_url,
                title=f"{metadata.title} - {episode_title}",
                episode=episode,
                subtitles=subtitles
            )
        else:
            return Single(
                url=video_url,
                title=metadata.title,
                subtitles=subtitles
            )