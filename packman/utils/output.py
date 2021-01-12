from math import floor
from typing import List, Optional, Tuple


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
        start: str = "▮",
        part: str = "■",
        background: str = " ",
        end: str = "▮",
        parts: int = 10,
        bar_padding: int = 11,
    ) -> None:
        self.progress = progress
        self.start = start
        self.part = part
        self.background = background
        self.end = end
        self.parts = parts
        self.padding = bar_padding

    def __str__(self) -> str:
        parts = floor(self.progress * self.parts)
        bar = self.start + self.part * parts
        bar = bar.ljust(self.padding, self.background) + self.end
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

    def __init__(self,
                 progress_bar: ProgressBarString = ProgressBarString(),
                 percent: Optional[PercentString] = PercentString(),
                 percent_padding: int = 5,
                 percent_on_right: bool = True,
                 separator: str = " ",
                 state_border: Tuple[str, str] = ("", " ")) -> None:
        self.complete: bool = False
        self.error: Optional[str] = None
        self.name = ""
        self.percent = percent
        self.progress_bar = progress_bar
        self.percent_padding = percent_padding
        self.percent_on_right = percent_on_right
        self.separator = separator
        self.state_border = state_border

    def __str__(self) -> str:
        if self.error:
            state = f"✗"
        elif self.complete:
            state = f"✓"
        else:
            state = "•"

        if self.percent_on_right:
            percent_str = str(self.percent).rjust(self.percent_padding)
            progress_part = f"{self.progress_bar}{percent_str}"
        else:
            percent_str = str(self.percent).ljust(self.percent_padding)
            progress_part = f"{percent_str}{self.progress_bar}"

        result = f"{self.state_border[0]}{state}{self.state_border[1]}{progress_part}{self.separator}{self.name}"

        if self.error:
            result += f" ({self.error})"

        return result


class ConsoleOutput:
    def __init__(self, step_string: StepString = StepString()) -> None:
        self._step_string = step_string

    def write(self, text: str, end: Optional[str] = None) -> None:
        print(str(text), end=end)

    def _finish_step(self, more_steps: bool = False) -> None:
        if not self._step_string.name:
            return
        self.write(self._step_string, "\n")
        self._step_string.name = ""
        self._step_string.error = None
        self._step_string.progress = 0.0
        self._step_string.complete = False

    def write_step_progress(self, name: str, progress: float) -> None:
        if self._step_string.name != name:
            self._finish_step(True)
            self._step_string.name = name

        self._step_string.progress = progress
        self.write(self._step_string, end="\r")

    def write_step_complete(self, name: str) -> None:
        if self._step_string.name != name:
            self._finish_step(True)
            self._step_string.name = name

        self._step_string.complete = True
        self.write(self._step_string, end="\r")

    def write_step_error(self, name: str, error: str) -> None:
        if self._step_string.name != name:
            self._finish_step(True)
            self._step_string.name = name

        self._step_string.error = error
        self.write(self._step_string, end="\r")

    def write_table(self, rows: List[List[str]]) -> None:
        ...  # TODO use for list

    def end(self) -> None:
        self._finish_step()
