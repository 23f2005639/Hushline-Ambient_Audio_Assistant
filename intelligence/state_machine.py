import asyncio
import time


class StateMachine:

    def __init__(self, media_controller):
        self.media_controller = media_controller
        self.last_speech_time = 0
        self.resume_delay     = 0.5
        self.pending_resume_time = None
        self.state            = "idle"

    def process_event(self, event):
        current_time = time.time()

        if event == "user_speaking":
            self._on_speaking(current_time)

        elif event == "user_silent":
            self._on_silent(current_time)

        elif event == "user_present":
            self._on_present()

        elif event == "user_absent":
            self._on_absent()

    def _on_speaking(self, current_time):
        self.last_speech_time = current_time
        self.pending_resume_time = None
        self.state            = "speaking"
        print("  STATE -> speaking")
        asyncio.run(self.media_controller.pause_media())

    def _on_silent(self, current_time):
        self.state = "silent"
        elapsed = current_time - self.last_speech_time
        print("  STATE -> silent")

        if elapsed >= self.resume_delay:
            self.pending_resume_time = None
            asyncio.run(self.media_controller.resume_media())
        else:
            self.pending_resume_time = self.last_speech_time + self.resume_delay
            remaining = self.pending_resume_time - current_time
            print(
                f"  STATE -> waiting "
                f"({remaining:.1f}s remaining)"
            )

    def tick(self, current_time: float | None = None):
        if current_time is None:
            current_time = time.time()
        if self.state != "silent" or self.pending_resume_time is None:
            return
        if current_time >= self.pending_resume_time:
            self.pending_resume_time = None
            print("  STATE -> resume timeout, resuming")
            asyncio.run(self.media_controller.resume_media())

    def _on_present(self):
        self.state = "present"
        print("  STATE -> user present")
        asyncio.run(self.media_controller.resume_media())

    def _on_absent(self):
        self.state = "absent"
        print("  STATE -> user absent")
        asyncio.run(self.media_controller.pause_media())
