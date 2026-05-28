import numpy as np
import webrtcvad
import config


class VADEngine:
    """
    Two-stage speech detector:
      Stage 1 — webrtcvad: is this frame speech-shaped?
      Stage 2 — spectral flatness: is this a hum? if so, reject it.

    Both stages must pass for a frame to be confirmed as speech.
    """

    def __init__(self, aggressiveness=2):
        # webrtcvad instance — aggressiveness 0-3
        self.aggressiveness = aggressiveness
        self.vad = webrtcvad.Vad(aggressiveness)

        # spectral flatness threshold
        # below this value = energy too concentrated = probably a hum
        # 0.05 means "at least 5% as flat as pure white noise"
        self.flatness_threshold = 0.05

        # minimum zero crossing rate for speech
        # hums have very low ZCR, speech has high ZCR
        self.min_zcr = 0.02

    def _check_vad(self, audio_int16):
        """
        Ask webrtcvad if this frame contains speech.
        Requires int16 PCM bytes — we convert from float32.
        """
        try:
            return self.vad.is_speech(
                audio_int16.tobytes(),
                config.SAMPLE_RATE
            )
        except Exception:
            return False

    def _check_not_hum(self, audio_float):
        """
        Returns True if the audio is NOT a hum.
        Uses two independent checks — both must agree it's not a hum.
        """

        # --- SPECTRAL FLATNESS ---
        # FFT gives us the frequency spectrum
        spectrum = np.abs(np.fft.rfft(audio_float))

        # avoid log(0) — add tiny value
        spectrum = spectrum + 1e-10

        # geometric mean — sensitive to spikes, pulled down by near-zeros
        log_mean = np.mean(np.log(spectrum))
        geometric_mean = np.exp(log_mean)

        # arithmetic mean — not sensitive to distribution shape
        arithmetic_mean = np.mean(spectrum)

        # flatness ratio — close to 1 = spread out (speech), close to 0 = spiky (hum)
        flatness = geometric_mean / arithmetic_mean

        if flatness < self.flatness_threshold:
            # energy too concentrated in one frequency — reject as hum
            return False

        # --- ZERO CROSSING RATE ---
        # count how often the signal crosses zero
        # speech: frequent crossings due to consonants
        # hums: very few crossings — smooth sustained tone
        signs = np.sign(audio_float)
        crossings = np.sum(np.abs(np.diff(signs)) > 0)
        zcr = crossings / len(audio_float)

        if zcr < self.min_zcr:
            # too smooth — likely a hum or sustained tone
            return False

        return True

    def detect_speech(self, indata, volume_threshold):
        """
        Main method — called every frame from the audio callback.

        Returns True only if:
          1. Volume is above threshold
          2. webrtcvad confirms speech pattern
          3. Spectral analysis confirms it's not a hum

        indata          : numpy array shape (FRAME_SIZE, 1), float32
        volume_threshold: float, from NoiseTracker.get_threshold()
        """

        # extract mono channel
        audio_float = indata[:, 0]

        # --- GATE 1: volume ---
        rms = np.sqrt(np.mean(audio_float ** 2)) * 1000
        if rms < volume_threshold:
            return False

        # convert to int16 for webrtcvad
        # webrtcvad expects 16-bit PCM, not float
        audio_int16 = (audio_float * 32767).astype(np.int16)

        # --- GATE 2: webrtcvad ---
        if not self._check_vad(audio_int16):
            return False

        # --- GATE 3: hum rejection ---
        if not self._check_not_hum(audio_float):
            return False

        return True