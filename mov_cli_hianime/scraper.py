from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Iterable, Optional, Dict, List

    from mov_cli import Config
    from mov_cli.http_client import HTTPClient
    from mov_cli.scraper import ScraperOptionsT

import json
from urllib.parse import quote_plus

from mov_cli.utils import EpisodeSelector
from mov_cli import Scraper, Multi, Single, Metadata, MetadataType

__all__ = ("HiAnimeScraper",)

class HiAnimeScraper(Scraper):
    def __init__(self, config: Config, http_client: HTTPClient, options: Optional[ScraperOptionsT] = None) -> None:
        # Base API URL for hianime
        self.base_url = "https://aniwatch-api-7ehn.onrender.com/api/v2/hianime"
        self.search_url = f"{self.base_url}/search"
        self.anime_url = f"{self.base_url}/anime"
        self.episode_url = f"{self.base_url}/episode/sources"

        # Stream player URL
        self.player_url = "https://ubel.to/?url="

        super().__init__(config, http_client, options)

    def _request(self, url: str, params: Optional[Dict] = None) -> Dict:
        """Helper method to make API requests"""
        try:
            response = self.http_client.get(url, params=params)
            return json.loads(response.text)
        except Exception as e:
            self.logger.error(f"Error making request to {url}: {e}")
            return {"data": {}}

    def search(self, query: str, limit: int = None) -> Iterable[Metadata]:
        """Search for anime on hianime"""
        if not query:
            self.logger.error("No search query provided")
            return []

        # Make search request
        response = self._request(f"{self.search_url}?q={quote_plus(query)}")

        # Check if we have results
        if not response or "data" not in response or "animes" not in response["data"]:
            self.logger.warning(f"No results found for query: {query}")
            return []

        animes = response["data"]["animes"]

        # Limit results if specified
        if limit is not None:
            animes = animes[:limit]

        # Convert results to Metadata objects and yield them
        for anime in animes:
            yield Metadata(
                id=anime["id"],
                title=anime["name"],
                type=MetadataType.MULTI if anime["episodes"]["sub"] > 1 else MetadataType.SINGLE,
            )

    def scrape_episodes(self, metadata: Metadata) -> Dict[int | None, int]:
        """Scrape episodes for a given anime"""
        # Request anime details to get episodes
        anime_details = self._request(f"{self.anime_url}/{metadata.id}/episodes")

        if not anime_details or "data" not in anime_details or "episodes" not in anime_details["data"]:
            self.logger.error(f"Failed to fetch episodes for anime ID: {metadata.id}")
            return {None: 1}

        episodes = anime_details["data"]["episodes"]

        # Create a dictionary mapping episode numbers
        episode_map = {}
        for ep in episodes:
            episode_map[ep["number"]] = 1

        # If no episodes were found, return a default
        if not episode_map:
            return {None: 1}

        return episode_map

    def scrape(self, metadata: Metadata, episode: EpisodeSelector) -> Multi | Single:
        """Scrape the actual content for viewing"""
        # Get the episode list
        anime_details = self._request(f"{self.anime_url}/{metadata.id}/episodes")

        if not anime_details or "data" not in anime_details or "episodes" not in anime_details["data"]:
            self.logger.error(f"Failed to fetch episodes for anime ID: {metadata.id}")
            # Return a placeholder Single
            return Single(
                url="",
                title=metadata.title,
                referrer="",
                year=metadata.year
            )

        episodes = anime_details["data"]["episodes"]

        # Find the requested episode
        target_episode = None
        if metadata.type == MetadataType.MULTI:
            episode_num = episode.episode if episode and episode.episode else 1
            for ep in episodes:
                if ep["number"] == episode_num:
                    target_episode = ep
                    break

            if not target_episode:
                self.logger.error(f"Episode {episode_num} not found for anime ID: {metadata.id}")
                # Return a placeholder Multi
                return Multi(
                    url="",
                    title=metadata.title,
                    referrer="",
                    episode=episode,
                    subtitles=None
                )
        else:
            # For a single, just grab the first episode
            if episodes:
                target_episode = episodes[0]
            else:
                self.logger.error(f"No episodes found for anime ID: {metadata.id}")
                # Return a placeholder Single
                return Single(
                    url="",
                    title=metadata.title,
                    referrer="",
                    year=metadata.year
                )

        # Get the sources for the episode
        sources_response = self._request(f"{self.episode_url}?animeEpisodeId={target_episode['episodeId']}")

        if not sources_response or "data" not in sources_response or "sources" not in sources_response["data"]:
            self.logger.error(f"Failed to fetch sources for episode ID: {target_episode['episodeId']}")
            # Return a placeholder based on type
            if metadata.type == MetadataType.MULTI:
                return Multi(
                    url="",
                    title=metadata.title,
                    referrer="",
                    episode=episode,
                    subtitles=None
                )
            else:
                return Single(
                    url="",
                    title=metadata.title,
                    referrer="",
                    year=metadata.year
                )

        # Get the main video source
        video_url = sources_response["data"]["sources"][0]["url"]

        # Get subtitles
        subtitles = {}
        if "tracks" in sources_response["data"]:
            for track in sources_response["data"]["tracks"]:
                if track["kind"] == "captions":
                    subtitles[track["label"]] = track["file"]

        if metadata.type == MetadataType.MULTI:
            return Multi(
                url=video_url,
                title=f"{metadata.title} - Episode {target_episode['number']}",
                referrer="https://hianime.to",
                episode=episode,
                subtitles=subtitles
            )
        else:
            return Single(
                url=video_url,
                title=metadata.title,
                referrer="https://hianime.to",
                year=metadata.year
            )