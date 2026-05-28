class NoiseTracker:

    def __init__(self):
        self.noise_floor = 10.0
        self.threshold_multiplier = 3
        self.minimum_noise_floor = 5.0
        self.maximum_noise_floor = None   # set after calibration

    def set_multiplier(self, multiplier):
        self.threshold_multiplier = multiplier
        print(f"Threshold multiplier set to: {multiplier:.2f}")

    def update(self, volume):
        if volume > self.noise_floor:
            attack = 0.90
            self.noise_floor = (
                (attack * self.noise_floor) + ((1 - attack) * volume)
            )
        else:
            release = 0.995
            self.noise_floor = (
                (release * self.noise_floor) + ((1 - release) * volume)
            )

        # enforce minimum
        if self.noise_floor < self.minimum_noise_floor:
            self.noise_floor = self.minimum_noise_floor

        # enforce maximum — don't let floor chase loud rooms past calibration
        if self.maximum_noise_floor and self.noise_floor > self.maximum_noise_floor:
            self.noise_floor = self.maximum_noise_floor

    def get_threshold(self):
        return self.noise_floor * self.threshold_multiplier