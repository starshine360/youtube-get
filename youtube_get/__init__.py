"""
YouTube-Get: a very serious Python library for downloading YouTube Videos.
"""

__title__ = "YouTube-Get"
__author__ = "starshine"
__license__ = "MIT License"
__js__ = None
__js_url__ = None

from youtube_get.version import __version__

from youtube_get.contrib.channel import Channel
from youtube_get.contrib.playlist import Playlist
from youtube_get.contrib.youtube import YouTube
from youtube_get.utils.captions import Caption
from youtube_get.utils.streams import Stream
from youtube_get.utils.query import CaptionQuery

