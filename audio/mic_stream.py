import time
import numpy as np
import sounddevice as sd
import config
from audio.noise_tracker import NoiseTracker
from audio.calibrator import Calibrator
from audio.vad_engine import VADEngine
from intelligence.confidence_engine import ConfidenceEngine
from intelligence.event_queue import EventQueue


noise_tracker     = NoiseTracker()
vad_engine        = VADEngine(aggressiveness=2)
confidence_engine = ConfidenceEngine(speech_trigger=5, silence_trigger=40)
event_queue       = EventQueue()


def calculate_rms(indata):
    samples = indata[:, 0]
    return np.sqrt(np.mean(samples ** 2)) * 1000


def callback(indata, frames, time_info, status):
    if status:
        print("Audio warning:", status)

    volume    = calculate_rms(indata)
    threshold = noise_tracker.get_threshold()

    if volume < threshold * 0.5:
        noise_tracker.update(volume)

    is_speech = vad_engine.detect_speech(indata, threshold)

    # pass frame result to confidence engine
    event = confidence_engine.process(is_speech)

    # if a meaningful event was produced, push it to the queue
    if event:
        event_queue.push(event)


def run():
    calibrator = Calibrator()

    while not calibrator.run(noise_tracker):
        input("Press Enter to try again...")

    print("Listening — speak and go silent, watch the events.\n")

    stream = sd.InputStream(
        samplerate=config.SAMPLE_RATE,
        blocksize=config.FRAME_SIZE,
        channels=1,
        dtype='float32',
        callback=callback
    )

    try:
        with stream:
            while True:
                # main thread reads events here
                event = event_queue.pop()

                if event:
                    # print with a timestamp so you can see the timing
                    print(f"  EVENT  →  {event}")

                time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nStopped.")