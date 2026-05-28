class ConfidenceEngine:
    """
    Converts a stream of per-frame speech booleans into
    high-level events: "user_speaking" and "user_silent".

    Only fires an event when the state actually changes —
    not repeatedly while the state stays the same.
    """

    def __init__(self, speech_trigger=5, silence_trigger=40):

        # how many consecutive speech frames before confirming speech
        # 5 frames × 30ms = 150ms
        self.speech_trigger  = speech_trigger

        # how many consecutive silent frames before confirming silence
        # 40 frames × 30ms = 1.2 seconds
        self.silence_trigger = silence_trigger

        self.speech_frames  = 0
        self.silence_frames = 0

        # track current state so we only fire on transitions
        # starts as None — neither speaking nor silent yet
        self.current_state = None

    def process(self, is_speech):
        """
        Call this every frame with the VAD result.
        Returns an event string, or None if nothing changed.

        Possible return values:
          "user_speaking" — user just started speaking
          "user_silent"   — user just stopped speaking
          None            — no state change
        """

        if is_speech:
            self.speech_frames  += 1
            self.silence_frames  = 0
        else:
            self.silence_frames += 1
            self.speech_frames   = 0

        # check if speech threshold crossed
        if self.speech_frames >= self.speech_trigger:
            if self.current_state != "speaking":
                # state changed — fire event
                self.current_state = "speaking"
                return "user_speaking"

        # check if silence threshold crossed
        if self.silence_frames >= self.silence_trigger:
            if self.current_state != "silent":
                # state changed — fire event
                self.current_state = "silent"
                return "user_silent"

        return None