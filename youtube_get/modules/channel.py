# -*- coding: utf-8 -*-
"""Module for interacting with a user's youtube channel."""
import json
import logging
from collections.abc import Sequence
from typing import Dict, Iterable, List, Optional, Tuple, Union

from youtube_get.modules.youtube import YouTube
from youtube_get.utils import extract, request
from youtube_get.utils.helpers import cache, DeferredGeneratorList, install_proxy, uniqueify

logger = logging.getLogger(__name__)


class Channel:
    """Load a YouTube channel with URL"""

    def __init__(self, url: str, proxies: Optional[Dict[str, str]] = None):
        """Construct a Channel object`.
        
        Args:
            url (str): A valid YouTube channel URL.
            proxies: (Optional) A dictionary of proxies to use for web requests.
        """
        super().__init__()
        
        if proxies:
            install_proxy(proxies)

        self._input_url = url

        self.channel_uri = extract.channel_name(url)
        self.channel_url = f"https://www.youtube.com{self.channel_uri}"

        # These need to be initialized as None for the properties.
        self._html = None
        self._ytcfg = None
        self._initial_data = None

        self.videos_url = self.channel_url + '/videos'
        self.playlists_url = self.channel_url + '/playlists'
        self.community_url = self.channel_url + '/community'
        self.featured_channels_url = self.channel_url + '/channels'
        self.about_url = self.channel_url + '/about'
        
        # Possible future additions
        self._playlists_html = None
        self._community_html = None
        self._featured_channels_html = None
        self._about_html = None

    @property
    def channel_name(self):
        """Get the name of the YouTube channel.

        Returns:
            A string which is the name of the YouTube channel.
        """
        return self.initial_data['metadata']['channelMetadataRenderer']['title']

    @property
    def channel_id(self):
        """Get the ID of the YouTube channel.

        This will return the underlying ID, not the vanity URL.
        """
        return self.initial_data['metadata']['channelMetadataRenderer']['externalId']

    @property
    def vanity_url(self):
        """Get the vanity URL of the YouTube channel.

        Returns None if it doesn't exist.
        """
        return self.initial_data['metadata']['channelMetadataRenderer'].get('vanityChannelUrl', None)  # noqa:E501

    @property
    def html(self):
        """Get the html for the /videos page.
        """
        if self._html:
            return self._html
        self._html = request.get(self.videos_url)
        return self._html

    @property
    def playlists_html(self):
        """Get the html for the /playlists page.

        Currently unused for any functionality.
        """
        if self._playlists_html:
            return self._playlists_html
        else:
            self._playlists_html = request.get(self.playlists_url)
            return self._playlists_html

    @property
    def community_html(self):
        """Get the html for the /community page.

        Currently unused for any functionality.
        """
        if self._community_html:
            return self._community_html
        else:
            self._community_html = request.get(self.community_url)
            return self._community_html

    @property
    def featured_channels_html(self):
        """Get the html for the /channels page.

        Currently unused for any functionality.
        """
        if self._featured_channels_html:
            return self._featured_channels_html
        else:
            self._featured_channels_html = request.get(self.featured_channels_url)
            return self._featured_channels_html

    @property
    def about_html(self):
        """Get the html for the /about page.

        Currently unused for any functionality.
        """
        if self._about_html:
            return self._about_html
        else:
            self._about_html = request.get(self.about_url)
            return self._about_html

    @property
    def ytcfg(self) -> dict:
        """Extract the ytcfg from the playlist page html.
        """
        if self._ytcfg:
            return self._ytcfg
        self._ytcfg = extract.get_ytcfg(self.html)
        return self._ytcfg

    @property
    def initial_data(self) -> dict:
        """Extract the initial data from the playlist page html.
        """
        if self._initial_data:
            return self._initial_data
        else:
            self._initial_data = extract.initial_data(self.html)
            return self._initial_data

    @property
    def yt_api_key(self) -> str:
        """Extract the INNERTUBE_API_KEY from the playlist ytcfg.
        """
        return self.ytcfg['INNERTUBE_API_KEY']

    def _paginate(self) -> Iterable[List[str]]:
        """Parse the video Ids from the page source, and yields the list of videoID

        Yields:
            Iterable of lists of YouTube watch ids
        """
        videos_Ids, continuation = self._extract_videos(
            json.dumps(extract.initial_data(self.html))
        )
        yield videos_Ids

        # Extraction from a playlist only returns 100 videos at a time
        # if self._extract_videos returns a continuation there are more
        # than 100 songs inside a playlist, so we need to add further requests
        # to gather all of them
        if continuation:
            load_more_url, headers, data = self._build_continuation_url(continuation)
        else:
            load_more_url, headers, data = None, None, None

        while load_more_url and headers and data:  # there is an url found
            logger.debug("load more url: {}".format(load_more_url))
            # requesting the next page of videos with the url generated from the
            # previous page, needs to be a post
            req = request.post(load_more_url, extra_headers=headers, data=data)
            # extract up to 100 songs from the page loaded
            # returns another continuation if more videos are available
            videos_Ids, continuation = self._extract_videos(req)
            yield videos_Ids

            if continuation:
                load_more_url, headers, data = self._build_continuation_url(continuation)
            else:
                load_more_url, headers, data = None, None, None

    def _build_continuation_url(self, continuation: str) -> Tuple[str, dict, dict]:
        """Helper method to build the url and headers required to request the next page of videos
        
        Args:
            continuation (str): Continuation extracted from the json response of the last page
        
        Returns: 
            Tuple of an url and required headers for the next http request
        """
        return (
            # was changed to this format (and post requests)
            # between 2021.03.02 and 2021.03.03
            f"https://www.youtube.com/youtubei/v1/browse?key={self.yt_api_key}",

            {
                "X-YouTube-Client-Name": "1",
                "X-YouTube-Client-Version": "2.20200720.00.02",
            },

            # extra data required for post request
            {
                "continuation": continuation,
                "context": {
                    "client": {
                        "clientName": "WEB",
                        "clientVersion": "2.20200720.00.02"
                    }
                }
            }
        )

    @staticmethod
    def _extract_videos(raw_json: str) -> Tuple[List[str], Optional[str]]:
        """Extracts videos from a raw json page

        Args:
            raw_json (str): Input json extracted from the page or the last server response
        
        Returns: 
            Tuple containing a list of up to 100 video watch ids and a continuation token, 
            if more videos are available
        """
        initial_data = json.loads(raw_json)
        # this is the json tree structure, if the json was extracted from html

        try:
            videos_tab = initial_data["contents"]["twoColumnBrowseResultsRenderer"]["tabs"][1]
            assert videos_tab["tabRenderer"]["title"] == "Videos"
            items_list = videos_tab["tabRenderer"]["content"]["richGridRenderer"]["contents"]
            video_Ids = [item["richItemRenderer"]["content"]["videoRenderer"]["videoId"] for item in items_list[:-1]] # the last one is for continuation
        except (KeyError, IndexError, TypeError, AssertionError) as err1:
            try:
                items_list = initial_data['onResponseReceivedActions'][0][
                        'appendContinuationItemsAction']['continuationItems']
                video_Ids = video_Ids = [item["richItemRenderer"]["content"]["videoRenderer"]["videoId"] for item in items_list[:-1]]
            except (KeyError, IndexError, TypeError) as err2:
                logger.error(f"parse videos firstly -> {repr(err1)}")
                logger.error(f"parse videos secondly -> {repr(err2)}")
                # with open("./show-initial-data.json", "w", encoding="utf-8") as file:
                #     json.dump(initial_data, file, indent=4, ensure_ascii=False)
                return [], None
        
        try:
            continuation = items_list[-1]['continuationItemRenderer'][
                'continuationEndpoint']['continuationCommand']['token']
        except (KeyError, IndexError) as err:
            # if there is an error, no continuation is available
            logger.error(f"parse continuation -> {repr(err)}")
            continuation = None

        video_Ids = uniqueify(video_Ids)

        return video_Ids, continuation

    def url_generator(self):
        """Generator that yields video URLs.
        """
        for page in self._paginate():
            for videoID in page:
                yield f"https://www.youtube.com/watch?v={videoID}"

    @property  # type: ignore
    @cache
    def video_urls(self) -> DeferredGeneratorList:
        """Complete links of all the videos in playlist
        """
        return DeferredGeneratorList(self.url_generator())

    def videos_generator(self):
        for url in self.video_urls:
            yield YouTube(url)
    
    @property
    def videos(self) -> Iterable[YouTube]:
        """Yields YouTube objects of videos in this playlist
        """
        return DeferredGeneratorList(self.videos_generator())

