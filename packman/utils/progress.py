from math import floor
from typing import Callable, Optional


class StepProgress:
    def __init__(self, step_mult: float, on_progress: Callable[[float], None]) -> None:
        self.step_no = 0
        self.step_mult = step_mult
        self.on_progress = on_progress

    def __call__(self, progress: float) -> None:
        self.on_progress((self.step_no + progress) * self.step_mult)

    def advance(self) -> None:
        self.__call__(1.0)
        self.step_no += 1


class PercentString:
    def __init__(
        self,
        value: float = 0.0,
        left_side_percent: bool = False,
        number_padding: int = 0
    ) -> None:
        self.value = value
        self.left_side_percent = left_side_percent
        self.number_padding = number_padding

    def __str__(self) -> str:
        progress = floor(self.value * 100)
        if self.left_side_percent:
            progress_percent = f"%{str(progress).rjust(self.number_padding)}"
        else:
            progress_percent = f"{str(progress).ljust(self.number_padding)}%"
        return progress_percent


class ProgressBarString:
    def __init__(
        self,
        progress: float = 0.0,
        start: str = "|",
        part: str = "[]",
        end: str = "|",
        parts: int = 10,
        bar_padding: int = 21,
    ) -> None:
        self.progress = progress
        self.start = start
        self.part = part
        self.end = end
        self.parts = parts
        self.padding = bar_padding

    def __str__(self) -> str:
        parts = floor(self.progress * self.parts)
        bar = self.start + self.part * parts
        bar = bar.ljust(self.padding) + self.end
        return bar

    def __repr__(self) -> str:
        attrs = (f"{attr} = {value!r}" for attr,
                 value in self.__dict__.items())
        return f"{type(self).__name__}({', '.join(attrs)})"


class StepString:
    @property
    def progress(self) -> float:
        return self.progress_bar.value

    @progress.setter
    def progress(self, value: float) -> None:
        self.progress_bar.progress = value
        if self.percent:
            self.percent.value = value

    def __init__(self, name: str, progress_bar: ProgressBarString = ProgressBarString(), percent: Optional[PercentString] = PercentString(), percent_padding: int = 5, percent_on_right: bool = False) -> None:
        self.complete = False
        self.error = False
        self.name = name
        self.percent = percent
        self.progress_bar = progress_bar
        self.percent_padding = percent_padding
        self.percent_on_right = percent_on_right

    def __str__(self) -> str:
        if self.error:
            state = "✗"
        elif self.complete:
            state = "✓"
        else:
            state = " "

        if self.percent_on_right:
            percent_str = str(self.percent).rjust(self.percent_padding)
            progress_part = f"{self.progress_bar}{percent_str}"
        else:
            percent_str = str(self.percent).ljust(self.percent_padding)
            progress_part = f"{percent_str}{self.progress_bar}"

        return f"{self.name} - {progress_part} [{state}]"