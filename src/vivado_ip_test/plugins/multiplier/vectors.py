import random
from dataclasses import dataclass

from vivado_ip_test.domain import VerificationProfile
from vivado_ip_test.plugins.multiplier.reference import (
    encode_fixed_width,
    multiply,
)
from vivado_ip_test.strategies import CaseSpace, GenerationResult, StrategyRegistry
from vivado_ip_test.strategies.boundaries import boundary_values


@dataclass(frozen=True)
class MultiplierVector:
    a: int
    b: int
    product: int
    packed_output: int


def _limits(width: int, operand_type: str) -> tuple[int, int]:
    if operand_type == "Signed":
        return -(1 << (width - 1)), (1 << (width - 1)) - 1
    if operand_type == "Unsigned":
        return 0, (1 << width) - 1
    raise ValueError(f"不支持的乘数类型：{operand_type}")


def _directed_pairs(
    a_width: int,
    b_width: int,
    a_type: str,
    b_type: str,
) -> list[tuple[int, int]]:
    a_min, a_max = _limits(a_width, a_type)
    b_min, b_max = _limits(b_width, b_type)
    candidates = [
        (0, 0),
        (0, 1),
        (1, 0),
        (1, 1),
        (a_min, b_min),
        (a_min, b_max),
        (a_max, b_min),
        (a_max, b_max),
        (a_min, 1),
        (a_max, 1),
        (1, b_min),
        (1, b_max),
    ]
    if a_min < 0:
        candidates.extend([(-1, b_min), (-1, b_max)])
    if b_min < 0:
        candidates.extend([(a_min, -1), (a_max, -1)])
    return list(dict.fromkeys(candidates))


def generate_vectors(
    *,
    a_width: int,
    b_width: int,
    a_type: str,
    b_type: str,
    output_width: int,
    profile: VerificationProfile,
    strategy_registry: StrategyRegistry,
) -> tuple[list[MultiplierVector], GenerationResult]:
    a_min, a_max = _limits(a_width, a_type)
    b_min, b_max = _limits(b_width, b_type)
    available_pairs = (a_max - a_min + 1) * (b_max - b_min + 1)
    a_edges = boundary_values(a_width, a_type == "Signed")
    b_edges = boundary_values(b_width, b_type == "Signed")
    edge_sets = {"a": set(a_edges), "b": set(b_edges)}
    directed = _directed_pairs(a_width, b_width, a_type, b_type)
    if profile.boundary_mode == "systematic":
        directed.extend((a, b) for a in a_edges for b in b_edges)

    def random_pair(generator: random.Random) -> tuple[int, int]:
        return generator.randint(a_min, a_max), generator.randint(b_min, b_max)

    def exhaustive_pairs():
        for a in range(a_min, a_max + 1):
            for b in range(b_min, b_max + 1):
                yield a, b

    def coverage_features(pair: tuple[int, int]) -> frozenset[str]:
        a, b = pair
        upper = encode_fixed_width(multiply(a, b), output_width) >> max(a_width, b_width)
        features = {
            f"sign:{'-' if a < 0 else '+'}{'-' if b < 0 else '+'}",
            f"product_upper:{'nonzero' if upper else 'zero'}",
        }
        for name, value, low, high in (
            ("a", a, a_min, a_max), ("b", b, b_min, b_max),
        ):
            if value == low:
                features.add(f"boundary:{name}:min")
            if value == high:
                features.add(f"boundary:{name}:max")
            features.add(f"magnitude:{name}:{abs(value).bit_length()}")
            if "systematic_values" in profile.coverage_targets and value in edge_sets[name]:
                features.add(f"systematic:{name}:{value}")
        return frozenset(features)

    a_signs = ("+", "-") if a_min < 0 else ("+",)
    b_signs = ("+", "-") if b_min < 0 else ("+",)

    generation = strategy_registry.generate(
        CaseSpace(
            directed_cases=tuple(directed),
            random_case=random_pair,
            exhaustive_cases=exhaustive_pairs,
            total_case_count=available_pairs,
            coverage_features=coverage_features,
            target_bins={
                "boundary_values": frozenset(
                    f"boundary:{name}:{edge}" for name in ("a", "b") for edge in ("min", "max")
                ),
                "sign_combinations": frozenset(f"sign:{a}{b}" for a in a_signs for b in b_signs),
                "full_precision": frozenset({"product_upper:zero", "product_upper:nonzero"}),
                "operand_magnitude": frozenset(
                    [f"magnitude:a:{bits}" for bits in range(max(abs(a_min), a_max).bit_length() + 1)]
                    + [f"magnitude:b:{bits}" for bits in range(max(abs(b_min), b_max).bit_length() + 1)]
                ),
                "systematic_values": frozenset(
                    f"systematic:{name}:{value}" for name, values in edge_sets.items() for value in values
                ),
            },
        ),
        profile,
    )

    vectors = []
    for a, b in generation.cases:
        product = multiply(a, b)
        vectors.append(
            MultiplierVector(
                a=a,
                b=b,
                product=product,
                packed_output=encode_fixed_width(product, output_width),
            )
        )
    return vectors, generation
