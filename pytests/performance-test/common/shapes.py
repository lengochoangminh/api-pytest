"""
Reusable Locust LoadTestShape classes.

Import the shape you need into your scenario file — do NOT pass this file
directly with -f, as Locust will error when it finds multiple LoadTestShape
subclasses in the same loaded set.

Usage in a scenario file
------------------------
    # Default: staged ramp
    from common.shapes import StagesShape

    # Long soak run (pass --run-time on CLI)
    from common.shapes import SoakShape

    # Spike validation
    from common.shapes import SpikeShape

Locust discovers the imported class via the scenario module's namespace.
"""

from locust import LoadTestShape


class StagesShape(LoadTestShape):
    """
    5-stage progressive ramp — total 8 minutes.

    Stage 1  :   0 –  60 s |  5 users | spawn  1/s  – warm-up
    Stage 2  :  60 – 180 s | 20 users | spawn  2/s  – baseline
    Stage 3  : 180 – 300 s | 50 users | spawn  5/s  – stress ramp
    Stage 4  : 300 – 420 s | 50 users | spawn  5/s  – sustained peak
    Stage 5  : 420 – 480 s |  0 users | spawn 10/s  – ramp-down / stop
    """

    stages = [
        {"duration": 60,  "users": 5,  "spawn_rate": 1},
        {"duration": 180, "users": 20, "spawn_rate": 2},
        {"duration": 300, "users": 50, "spawn_rate": 5},
        {"duration": 420, "users": 50, "spawn_rate": 5},
        {"duration": 480, "users": 0,  "spawn_rate": 10},
    ]

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return stage["users"], stage["spawn_rate"]
        return None


class SoakShape(LoadTestShape):
    """
    Flat sustained load — duration controlled entirely by --run-time on CLI.

    Never self-terminates; Locust stops when --run-time elapses.

    Example:
        locust -f <scenario>.py --headless --run-time 2h
        (swap the StagesShape import for SoakShape in the scenario file)
    """

    users = 20
    spawn_rate = 2

    def tick(self):
        return self.users, self.spawn_rate


class SpikeShape(LoadTestShape):
    """
    Sudden traffic spike — total 4 minutes.

    Stage 1  :   0 –  30 s |  10 users | spawn  5/s – pre-spike baseline
    Stage 2  :  30 –  90 s | 200 users | spawn 50/s – spike
    Stage 3  :  90 – 150 s | 200 users | spawn 50/s – hold peak
    Stage 4  : 150 – 210 s |  10 users | spawn 50/s – recovery
    Stage 5  : 210 – 240 s |  10 users | spawn  5/s – post-spike baseline
    """

    stages = [
        {"duration": 30,  "users": 10,  "spawn_rate": 5},
        {"duration": 90,  "users": 200, "spawn_rate": 50},
        {"duration": 150, "users": 200, "spawn_rate": 50},
        {"duration": 210, "users": 10,  "spawn_rate": 50},
        {"duration": 240, "users": 10,  "spawn_rate": 5},
    ]

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return stage["users"], stage["spawn_rate"]
        return None
