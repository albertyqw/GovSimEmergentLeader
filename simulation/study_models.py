"""Study-only token override; the original wrapper defaults stay intact."""

from simulation.utils.models import ModelWandbWrapper


class StudyModelWrapper(ModelWandbWrapper):
    def gen(self, *args, **kwargs):
        cap = getattr(self, "study_generation_max_tokens", None)
        if cap is not None:
            kwargs["max_tokens"] = cap
        return super().gen(*args, **kwargs)

    def find(self, *args, **kwargs):
        cap = getattr(self, "study_generation_max_tokens", None)
        if cap is not None:
            kwargs["max_tokens"] = cap
        return super().find(*args, **kwargs)
