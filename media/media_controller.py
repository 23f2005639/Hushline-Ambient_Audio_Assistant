from winrt.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager,
)


PLAYING = 4
PAUSED = 5


class MediaController:
    def __init__(self):
        self.paused_by_us = False

    async def get_session(self):
        manager = await (
            GlobalSystemMediaTransportControlsSessionManager.request_async()
        )
        return manager.get_current_session()

    async def pause_media(self):
        session = await self.get_session()
        if not session:
            return

        playback = session.get_playback_info()
        status = playback.playback_status

        if status == PLAYING:
            print("  MEDIA -> pausing")
            await session.try_pause_async()
            self.paused_by_us = True

    async def resume_media(self):
        if not self.paused_by_us:
            return

        session = await self.get_session()
        if not session:
            return

        playback = session.get_playback_info()
        status = playback.playback_status

        if status == PLAYING:
            self.paused_by_us = False
            return

        if status == PAUSED:
            print("  MEDIA -> resuming")
            await session.try_play_async()
            self.paused_by_us = False

    async def toggle_media(self):
        session = await self.get_session()
        if not session:
            return

        playback = session.get_playback_info()
        status = playback.playback_status

        if status == PLAYING:
            await session.try_pause_async()
        else:
            await session.try_play_async()
        self.paused_by_us = False

    async def next_media(self):
        session = await self.get_session()
        if session:
            await session.try_skip_next_async()

    async def previous_media(self):
        session = await self.get_session()
        if session:
            await session.try_skip_previous_async()

    async def get_media_info(self):
        session = await self.get_session()
        if not session:
            return self._empty_media()

        playback = session.get_playback_info()
        status = playback.playback_status
        title = "Unknown track"
        artist = "Unknown artist"

        try:
            props = await session.try_get_media_properties_async()
            title = props.title or title
            artist = props.artist or artist
        except Exception:
            pass

        progress = 0
        try:
            timeline = session.get_timeline_properties()
            start = getattr(timeline, "start_time", 0)
            end = getattr(timeline, "end_time", 0)
            position = getattr(timeline, "position", 0)
            duration = end - start
            if duration:
                progress = max(0, min(1, position / duration))
        except Exception:
            progress = 0

        return {
            "title": title,
            "artist": artist,
            "playing": status == PLAYING,
            "progress": progress,
        }

    def _empty_media(self):
        return {
            "title": "Nothing playing",
            "artist": "-",
            "playing": False,
            "progress": 0,
        }
