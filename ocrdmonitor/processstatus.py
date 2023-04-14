from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import Enum


class ProcessState(Enum):
    # see ps(1)#PROCESS_STATE_CODES
    RUNNING = "R"
    SLEEPING = "S"
    SLEEPIO = "D"
    STOPPED = "T"
    TRACING = "t"
    ZOMBIE = "Z"
    UNKNOWN = "?"

    def __str__(self) -> str:
        return str(self.name)


@dataclass(frozen=True)
class ProcessStatus:
    pid: int
    state: ProcessState
    percent_cpu: float
    memory: int
    cpu_time: timedelta

    @classmethod
    def shell_command(cls, pid: int) -> str:
        return f"ps -s {pid} -o pid,state,%cpu,rss,cputime --no-headers"

    @classmethod
    def from_shell_output(cls, ps_output: str) -> list["ProcessStatus"]:
        def is_error(lines: list[str]) -> bool:
            return lines[0].startswith("error:")

        def parse_line(line: str) -> "ProcessStatus":
            pid, state, percent_cpu, memory, cpu_time, *_ = line.split()
            return cls(
                pid=int(pid),
                state=ProcessState(state[0]),
                percent_cpu=float(percent_cpu),
                memory=int(memory),
                cpu_time=timedelta(seconds=_cpu_time_to_seconds(cpu_time)),
            )

        lines = ps_output.strip().splitlines()
        if not lines or is_error(lines):
            return []

        return [parse_line(line) for line in lines]


def _cpu_time_to_seconds(cpu_time: str) -> int:
    hours, minutes, seconds, *_ = cpu_time.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds)
