from datetime import datetime, timedelta


class ClockStub:
    def __init__(self, time: datetime) -> None:
        self.time = time

    def advance_time(self, delta: timedelta = timedelta(days=1)) -> datetime:
        self.time += delta
        return self.time

    def __call__(self) -> datetime:
        return self.time
