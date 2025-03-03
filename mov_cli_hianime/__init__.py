from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mov_cli.plugins import PluginHookData

from .scraper import *

plugin: PluginHookData = {
    "version": 1,
    "package_name": "mov-cli-hianime",
    "scrapers": {
        "DEFAULT": HiAnimeScraper,
        "hianime": HiAnimeScraper
    }
}

__version__ = "0.1.0"