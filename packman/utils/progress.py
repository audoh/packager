from typing import Callable


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
