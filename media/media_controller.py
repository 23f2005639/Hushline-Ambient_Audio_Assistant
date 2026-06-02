import sys
import asyncio

IS_WINDOWS = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux")

if IS_WINDOWS:
    from winrt.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager,
    )

    PLAYING = 4
    PAUSED = 5


class MediaController:
    def __init__(self):
        self.paused_by_us = False

    # Windows
    if IS_WINDOWS:

        async def _get_session(self):
            manager = await (
                GlobalSystemMediaTransportControlsSessionManager.request_async()
            )
            return manager.get_current_session()

    # Linux
    if IS_LINUX:

        async def _run_playerctl(self, *args):
            try:
                proc = await asyncio.create_subprocess_exec(
                    "playerctl",
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await proc.communicate()
                if proc.returncode == 0:
                    return stdout.decode().strip()
            except Exception:
                pass
            return None

    # Unified Interface
    async def pause_media(self):
        if IS_WINDOWS:
            session = await self._get_session()
            if not session:
                return
            playback = session.get_playback_info()
            if playback.playback_status == PLAYING:
                print("  MEDIA -> pausing")
                await session.try_pause_async()
                self.paused_by_us = True

        elif IS_LINUX:
            status = await self._run_playerctl("status")
            if status and status.lower() == "playing":
                print("  MEDIA -> pausing")
                await self._run_playerctl("pause")
                self.paused_by_us = True

    async def resume_media(self):
        if not self.paused_by_us:
            return

        if IS_WINDOWS:
            session = await self._get_session()
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

        elif IS_LINUX:
            status = await self._run_playerctl("status")
            if status:
                if status.lower() == "playing":
                    self.paused_by_us = False
                    return
                if status.lower() == "paused":
                    print("  MEDIA -> resuming")
                    await self._run_playerctl("play")
                    self.paused_by_us = False

    async def toggle_media(self):
        if IS_WINDOWS:
            session = await self._get_session()
            if not session:
                return
            playback = session.get_playback_info()
            if playback.playback_status == PLAYING:
                await session.try_pause_async()
            else:
                await session.try_play_async()
            self.paused_by_us = False

        elif IS_LINUX:
            await self._run_playerctl("play-pause")
            self.paused_by_us = False

    async def next_media(self):
        if IS_WINDOWS:
            session = await self._get_session()
            if session:
                await session.try_skip_next_async()
        elif IS_LINUX:
            await self._run_playerctl("next")

    async def previous_media(self):
        if IS_WINDOWS:
            session = await self._get_session()
            if session:
                await session.try_skip_previous_async()
        elif IS_LINUX:
            await self._run_playerctl("previous")

    async def get_media_info(self):
        if IS_WINDOWS:
            session = await self._get_session()
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

        elif IS_LINUX:
            status = await self._run_playerctl("status")
            if not status:
                return self._empty_media()

            meta_str = await self._run_playerctl(
                "metadata",
                "--format",
                "{{title}};;{{artist}};;{{position}};;{{mpris:length}}",
            )
            title = "Unknown track"
            artist = "Unknown artist"
            progress = 0

            if meta_str:
                parts = meta_str.split(";;")
                if len(parts) >= 2:
                    title = parts[0] or title
                    artist = parts[1] or artist
                if len(parts) >= 4:
                    try:
                        pos = float(parts[2]) if parts[2] else 0
                        # mpris:length returns microseconds; position returns seconds
                        length = float(parts[3]) / 1_000_000 if parts[3] else 0
                        if length > 0:
                            progress = max(0.0, min(1.0, pos / length))
                    except ValueError:
                        pass

            return {
                "title": title,
                "artist": artist,
                "playing": status.lower() == "playing",
                "progress": progress,
            }

        return self._empty_media()

    def _empty_media(self):
        return {
            "title": "Nothing playing",
            "artist": "-",
            "playing": False,
            "progress": 0,
        }
