# analytics.py
from collections import deque
import time


class AnalyticsEngine:
    """
    Maintains CPU/RAM history and generates alerts based on simple rules.
    """
    def __init__(self, max_history=60):
        self.cpu_history = deque(maxlen=max_history)
        self.memory_history = deque(maxlen=max_history)
        self.time_history = deque(maxlen=max_history)

    def update_history(self, system_stats: dict):
        """
        Add a new point to history.
        """
        now = time.strftime("%H:%M:%S")
        self.time_history.append(now)
        self.cpu_history.append(system_stats["cpu_percent"])
        self.memory_history.append(system_stats["memory_percent"])

    def check_alerts(self, system_stats: dict):
        """
        Generate alerts based on thresholds.
        Returns list of alert dicts: {level, message, time}
        """
        alerts = []
        cpu = system_stats["cpu_percent"]
        mem = system_stats["memory_percent"]
        now = time.strftime("%H:%M:%S")

        # CPU alerts
        if cpu > 90:
            alerts.append({
                "level": "CRITICAL",
                "message": f"CPU usage is {cpu:.1f}%",
                "time": now
            })
        elif cpu > 80:
            alerts.append({
                "level": "WARNING",
                "message": f"CPU usage is high: {cpu:.1f}%",
                "time": now
            })

        # Memory alerts
        if mem > 90:
            alerts.append({
                "level": "CRITICAL",
                "message": f"Memory usage is {mem:.1f}%",
                "time": now
            })
        elif mem > 80:
            alerts.append({
                "level": "WARNING",
                "message": f"Memory usage is high: {mem:.1f}%",
                "time": now
            })

        return alerts
