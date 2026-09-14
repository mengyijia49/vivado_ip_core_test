import random
from dataclasses import dataclass

from vivado_ip_test.domain import VerificationProfile
from vivado_ip_test.plugins.divider.reference import (
    pack_remainder_output,
    truncating_division,
)
from vivado_ip_test.strategies import CaseSpace, GenerationResult, StrategyRegistry
from vivado_ip_test.strategies.boundaries import boundary_values


@dataclass(frozen=True)
class DividerVector:
    dividend: int
    divisor: int
    quotient: int
    remainder: int
    packed_output: int


def _limits(width: int, signed: bool) -> tuple[int, int]:
    if signed:
        return -(1 << (width - 1)), (1 << (width - 1)) - 1
    return 0, (1 << width) - 1


def _directed_pairs(
    dividend_width: int,
    divisor_width: int,
    signed: bool,
) -> list[tuple[int, int]]:
    dividend_min, dividend_max = _limits(dividend_width, signed)
    divisor_min, divisor_max = _limits(divisor_width, signed)

    if signed:
        candidates = [
            (0, 1),
            (1, 1),
            (-1, 1),
            (1, -1),
            (-1, -1),
            (dividend_max, 1),
            (dividend_min, 1),
            (dividend_max, -1),
            (dividend_min, 2),
            (dividend_min, divisor_min),
            (dividend_max, divisor_max),
            (dividend_max, 2),
            (dividend_min + 1, -2),
            (dividend_max // 2, divisor_max),
            (-(dividend_max // 2), divisor_max),
            (dividend_max // 3, -max(1, divisor_max // 2)),
        ]
    else:
        candidates = [
            (0, 1),
            (1, 1),
            (dividend_max, 1),
            (dividend_max, divisor_max),
            (dividend_max, 2),
            (dividend_max // 2, divisor_max),
            (dividend_max // 2, 3),
            (1 << (dividend_width - 1), 1),
            (1 << (dividend_width - 1), divisor_max),
            (max(0, divisor_max - 1), divisor_max),
            (divisor_max, divisor_max),
            (divisor_max + 1, divisor_max),
        ]

    return [
        (dividend, divisor)
        for dividend, divisor in candidates
        if dividend_min <= dividend <= dividend_max
        and divisor_min <= divisor <= divisor_max
        and divisor != 0
        and not (signed and dividend == dividend_min and divisor == -1)
    ]


def generate_vectors(
    *,
    dividend_width: int,
    divisor_width: int,
    operand_sign: str,
    profile: VerificationProfile,
    strategy_registry: StrategyRegistry,
) -> tuple[list[DividerVector], GenerationResult]:
    if dividend_width <= 0 or divisor_width <= 0:
        raise ValueError("Divider 位宽必须是正整数")
    if operand_sign not in {"Unsigned", "Signed"}:
        raise ValueError(f"不支持的 Divider 符号类型：{operand_sign}")

    signed = operand_sign == "Signed"
    dividend_min, dividend_max = _limits(dividend_width, signed)
    divisor_min, divisor_max = _limits(divisor_width, signed)
    dividend_values = dividend_max - dividend_min + 1
    nonzero_divisors = divisor_max - divisor_min
    available_pairs = dividend_values * nonzero_divisors
    if signed and divisor_min <= -1 <= divisor_max:
        available_pairs -= 1

    dividend_edges = boundary_values(dividend_width, signed)
    divisor_edges = tuple(value for value in boundary_values(divisor_width, signed) if value)
    edge_sets = {"dividend": set(dividend_edges), "divisor": set(divisor_edges)}

    def legal(pair):
        a, b = pair
        return (dividend_min <= a <= dividend_max and divisor_min <= b <= divisor_max
                and b != 0 and not (signed and a == dividend_min and b == -1))

    directed = _directed_pairs(dividend_width, divisor_width, signed)
    if profile.boundary_mode == "systematic":
        directed.extend((a, b) for a in dividend_edges for b in divisor_edges if legal((a, b)))
        quotients = {0, 1, 2, 3, *(1 << bit for bit in range(dividend_width))}
        if signed:
            quotients |= {-value for value in quotients}
        for b in divisor_edges:
            for q in sorted(quotients):
                for delta in (-abs(b) + 1, -1, 0, 1, abs(b) - 1):
                    pair = (q * b + delta, b)
                    if legal(pair):
                        directed.append(pair)

    def random_pair(generator: random.Random) -> tuple[int, int]:
        while True:
            dividend = generator.randint(dividend_min, dividend_max)
            divisor = generator.randint(divisor_min, divisor_max)
            if divisor == 0:
                continue
            if signed and dividend == dividend_min and divisor == -1:
                continue
            return dividend, divisor

    def exhaustive_pairs():
        for dividend in range(dividend_min, dividend_max + 1):
            for divisor in range(divisor_min, divisor_max + 1):
                if divisor == 0:
                    continue
                if signed and dividend == dividend_min and divisor == -1:
                    continue
                yield dividend, divisor

    def coverage_features(pair: tuple[int, int]) -> frozenset[str]:
        dividend, divisor = pair
        features = {
            f"divisor:{'-' if divisor < 0 else '+'}",
            f"sign:{'-' if dividend < 0 else '+'}{'-' if divisor < 0 else '+'}",
        }
        for name, value, low, high in (
            ("dividend", dividend, dividend_min, dividend_max),
            ("divisor", divisor, divisor_min, divisor_max),
        ):
            if value == low:
                features.add(f"boundary:{name}:min")
            if value == high:
                features.add(f"boundary:{name}:max")
            if "systematic_values" in profile.coverage_targets and value in edge_sets[name]:
                features.add(f"systematic:{name}:{value}")
        if "division_relations" in profile.coverage_targets:
            remainder = abs(dividend) % abs(divisor)
            if remainder == 0:
                features.add("division:exact")
            if remainder == 1:
                features.add("division:remainder_one")
            if abs(divisor) > 1 and remainder == abs(divisor) - 1:
                features.add("division:remainder_last")
            features.add(f"division:{'small' if abs(dividend) < abs(divisor) else 'large'}")
        return frozenset(features)

    boundary_bins = {"boundary:dividend:min", "boundary:dividend:max", "boundary:divisor:max"}
    if divisor_min != 0:
        boundary_bins.add("boundary:divisor:min")
    signs = ("+", "-") if signed else ("+",)

    generation = strategy_registry.generate(
        CaseSpace(
            directed_cases=tuple(directed),
            random_case=random_pair,
            exhaustive_cases=exhaustive_pairs,
            total_case_count=available_pairs,
            coverage_features=coverage_features,
            target_bins={
                "boundary_values": frozenset(boundary_bins),
                "sign_combinations": frozenset(f"sign:{a}{b}" for a in signs for b in signs),
                "nonzero_divisor": frozenset(f"divisor:{sign}" for sign in signs),
                "systematic_values": frozenset(
                    f"systematic:{name}:{value}" for name, values in edge_sets.items() for value in values
                ),
                "division_relations": frozenset({
                    "division:exact", "division:remainder_one", "division:remainder_last",
                    "division:small", "division:large",
                }),
            },
        ),
        profile,
    )

    vectors = []
    for dividend, divisor in generation.cases:
        result = truncating_division(dividend, divisor)
        vectors.append(
            DividerVector(
                dividend=dividend,
                divisor=divisor,
                quotient=result.quotient,
                remainder=result.remainder,
                packed_output=pack_remainder_output(
                    result,
                    quotient_width=dividend_width,
                    remainder_width=divisor_width,
                ),
            )
        )
    return vectors, generation
