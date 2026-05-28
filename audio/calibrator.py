import time
import numpy as np
import sounddevice as sd
import config


class Calibrator:
    """
    Runs at startup to measure two things:
      - what silence sounds like on this mic in this room
      - what the user's voice sounds like on this mic

    From those two measurements it computes the right threshold
    multiplier automatically, so the system works on any microphone.
    """

    def __init__(self):
        self.silence_samples = []
        self.voice_samples   = []

    def _collect(self, duration_seconds, label, on_countdown=None):
        """
        Opens the mic for `duration_seconds` and collects
        RMS volume readings into a list, then returns it.
        """
        print(label)

        samples = []

        def callback(indata, frames, time_info, status):
            audio  = indata[:, 0]
            rms    = np.sqrt(np.mean(audio ** 2)) * 1000
            samples.append(rms)

        stream = sd.InputStream(
            samplerate=config.SAMPLE_RATE,
            blocksize=config.FRAME_SIZE,
            channels=1,
            dtype='float32',
            callback=callback
        )

        with stream:
            # countdown so the user knows how long to wait
            for remaining in range(duration_seconds, 0, -1):
                if on_countdown:
                    on_countdown(remaining)
                print(f"  {remaining}...")
                time.sleep(1)

        print()
        return samples

    def run(self, noise_tracker, on_phase=None):
        """
        Full calibration sequence.
        Measures silence, then voice, then sets the multiplier
        on the noise_tracker.

        Returns True if calibration succeeded, False if
        something went wrong (e.g. user didn't speak).
        """
        print("=" * 40)
        print("  CALIBRATION")
        print("=" * 40)

        # --- PHASE 1: silence ---
        if on_phase:
            on_phase("silence", 3)
        silence_samples = self._collect(
            duration_seconds=3,
            label="\nPhase 1 - Stay silent...",
            on_countdown=lambda remaining: on_phase and on_phase("silence", remaining),
        )

        silence_avg = np.mean(silence_samples) if silence_samples else 10.0
        print(f"  Silence level : {silence_avg:.1f}")

        # --- PHASE 2: voice ---
        if on_phase:
            on_phase("voice", 3)
        voice_samples = self._collect(
            duration_seconds=3,
            label="Phase 2 - Speak normally until the countdown ends...",
            on_countdown=lambda remaining: on_phase and on_phase("voice", remaining),
        )

        # ignore the quietest frames - those are pauses between words
        # we want the average of the louder half, which is the actual voice
        voice_samples.sort(reverse=True)
        top_half      = voice_samples[:len(voice_samples) // 2]
        voice_avg     = np.mean(top_half) if top_half else silence_avg * 4

        print(f"  Voice level   : {voice_avg:.1f}")

        # --- SANITY CHECK ---
        # if voice and silence are too close, calibration failed
        # (user probably didn't speak, or mic isn't working)
        if voice_avg < silence_avg * 1.5:
            print("\n  Could not distinguish voice from silence.")
            print("  Check your microphone and try again.\n")
            return False

        # --- COMPUTE MULTIPLIER ---
        # threshold sits halfway between silence and voice
        # dividing by silence_avg gives us the multiplier relative to floor
        multiplier = (voice_avg / silence_avg) / 2

        # clamp to a sane range - never below 1.2 or above 10
        multiplier = max(1.2, min(multiplier, 10.0))

        noise_tracker.set_multiplier(multiplier)

        # seed the noise floor from what we actually measured
        noise_tracker.noise_floor = silence_avg

        noise_tracker.maximum_noise_floor = silence_avg * 3

        print(f"  Calibration complete.")
        print(f"  Threshold will sit at: {silence_avg * multiplier:.1f}")
        print("=" * 40)
        print()

        return True
