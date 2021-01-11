from typing import Callable, Optional


class StepProgress:
    def __init__(self, step_mult: float, on_progress: Callable[[float], None]) -> None:
        self.step_no = 0
        self.step_mult = step_mult
        self.on_progress = on_progress

    def __call__(self, progress: float) -> None:
        try:
            self.on_progress((self.step_no + progress) * self.step_mult)
        except Exception as exc:
            # TODO warn limited number of times
            ...

    def advance(self) -> None:
        self.__call__(1.0)
        self.step_no += 1

    def backtrack(self) -> None:
        self.__call__(0.0)
        self.step_no -= 1


class RestoreProgress:
    def __init__(self, start_progress: float, on_progress: Callable[[float], None]) -> None:
        self.start_progress = start_progress
        self.on_progress = on_progress

    def __call__(self, progress: float) -> None:
        try:
            self.on_progress(self.start_progress * (1 - progress))
        except Exception as exc:
            # TODO warn limited number of times
            ...

    @staticmethod
    def step_progress(step_progress: StepProgress, on_progress: Callable[[float], None]) -> Callable[[float], None]:
        restore_progress: Optional[RestoreProgress] = None

        def on_restore_progress(p: float):
            nonlocal restore_progress
            if not restore_progress:
                restore_progress = RestoreProgress(
                    start_progress=step_progress.step_no * step_progress.step_mult, on_progress=on_progress)
            restore_progress(p)
        return on_restore_progress
