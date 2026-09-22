from itertools import product
from math import prod

from vivado_ip_test.infrastructure.json_values import with_hex_large_integers
from vivado_ip_test.plugins.common.cycle import CycleSpec
from vivado_ip_test.strategies.base import CaseSpace
from vivado_ip_test.strategies.boundaries import boundary_values


def cycle_space(spec: CycleSpec, systematic: bool) -> CaseSpace:
    return port_space(spec.inputs, systematic, spec.frame(), spec.combine_scalar_controls)


def port_space(ports, systematic: bool, neutral=None, combine_scalar_controls=True) -> CaseSpace:
    active = {port.name: (neutral or {}).get(port.name, 0) for port in ports}
    boundaries = [tuple(sorted({value for value in
                  (boundary_values(port.width, False) if systematic else
                   (0, 1, port.limit // 2, port.limit - 1, port.limit))
                  if 0 <= value <= port.limit})) for port in ports]
    directed = []
    active_high = {**active, **{port.name: port.limit for port in ports if not port.scalar}}
    bases = (tuple(active[port.name] for port in ports),
             tuple(active_high[port.name] for port in ports),
             tuple(0 for _ in ports), tuple(port.limit for port in ports))
    for base in dict.fromkeys(bases):
        directed.append(base)
        for index, values in enumerate(boundaries):
            for value in values:
                row = list(base)
                row[index] = value
                directed.append(tuple(row))
    if combine_scalar_controls:
        control_indices = [index for index, port in enumerate(ports) if port.scalar]
        for controls in product((0, 1), repeat=len(control_indices)):
            row = [port.limit for port in ports]
            for index, value in zip(control_indices, controls):
                row[index] = value
            directed.append(tuple(row))
    bins = frozenset(f"{port.name}:{with_hex_large_integers(value)}" for port, values in zip(ports, boundaries)
                     for value in values)
    return CaseSpace(
        directed_cases=tuple(dict.fromkeys(directed)),
        random_case=lambda rng: tuple(rng.randrange(port.limit + 1) for port in ports),
        exhaustive_cases=lambda: product(*(range(port.limit + 1) for port in ports)),
        total_case_count=prod(port.limit + 1 for port in ports),
        coverage_features=lambda row: frozenset(f"{port.name}:{with_hex_large_integers(value)}"
                                               for port, value in zip(ports, row)),
        target_bins={"port_boundaries": bins},
    )
