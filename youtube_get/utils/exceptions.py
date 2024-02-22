"""Library specific exception definitions."""

from typing import Pattern, Union


class YouTubeError(Exception):
    """Base youtube exception that all others inherit.
    """


class MaxRetriesExceeded(YouTubeError):
    """Maximum number of retries exceeded."""


class HTMLParseError(YouTubeError):
    """HTML could not be parsed"""


class ExtractError(YouTubeError):
    """Data extraction based exception."""


class RegexMatchError(ExtractError):
    """Regex pattern did not return any matches."""

    def __init__(self, caller: str, pattern: Union[str, Pattern]):
        """
        Arguments:
            caller (str): Calling function
            pattern (str): Pattern that failed to match
        """
        super().__init__(f"{caller}: could not find match for {pattern}")
        self.caller = caller
        self.pattern = pattern


class VideoUnavailable(YouTubeError):
    """Base video unavailable error."""
    def __init__(self, video_id: str, reason: str = None):
        """
        :param str video_id:
            A YouTube video identifier.
        :param str reason:
            Specify the reason of this error.
        """
        self.video_id = video_id
        self.reason = reason
        super().__init__(self.error_string)

    @property
    def error_string(self):
        if self.reason is not None:
            message = f'{self.video_id} is unavailable (reason: {self.reason})'
        else:
            message = f'{self.video_id} is unavailable'
        return message



    def __init__(self, video_id: str):
        """
        :param str video_id:
            A YouTube video identifier.
        """
        self.video_id = video_id
        super().__init__(self.video_id)

    @property
    def error_string(self):
        return f'{self.video_id} is not available in your region'