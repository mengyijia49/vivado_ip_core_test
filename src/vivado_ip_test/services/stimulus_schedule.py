"""确定性时序调度；无使能接口的保持周期仍是需要检查的真实事务。"""

import random
from dataclasses import dataclass

from vivado_ip_test.domain import VerificationProfile


@dataclass(frozen=True)
class StimulusSchedule:
    gaps: tuple[int, ...]
    transaction_indices: tuple[int, ...]
    input_cycles: int

    def metrics(self) -> dict[str, object]:
        return {
            "schedule_version": "1.0",
            "input_cycles": self.input_cycles,
            "checked_transaction_count": len(self.transaction_indices),
            "gap_cycles": sum(self.gaps),
            "max_observed_gap": max(self.gaps, default=0),
        }


def build_schedule(count: int, profile: VerificationProfile, *, can_idle: bool) -> StimulusSchedule:
    if count <= 0:
        raise ValueError("schedule requires at least one vector")
    if profile.timing_mode not in {"continuous", "random_gaps", "bursts"}:
        raise ValueError("unsupported timing mode")
    if profile.max_gap_cycles < 1 or profile.burst_length < 1:
        raise ValueError("invalid timing limits")
    # 独立随机流保证改变时序不会改变数值向量。
    generator = random.Random(f"timing:1.0:{profile.random_seed}")
    order = list(range(count))
    if profile.input_order == "shuffled":
        random.Random(f"order:1.0:{profile.random_seed}").shuffle(order)
    elif profile.input_order != "generated":
        raise ValueError("unsupported input order")
    gaps = []
    indices = []
    for index in range(count):
        gap = 0
        if index and profile.timing_mode == "random_gaps":
            gap = generator.randint(0, profile.max_gap_cycles)
        elif index and profile.timing_mode == "bursts" and index % profile.burst_length == 0:
            gap = profile.max_gap_cycles
        gaps.append(gap)
        if not can_idle:
            indices.extend([order[index - 1]] * gap)
        indices.append(order[index])
    return StimulusSchedule(tuple(gaps), tuple(indices), count + sum(gaps))
