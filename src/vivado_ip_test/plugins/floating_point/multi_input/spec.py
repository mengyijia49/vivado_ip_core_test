from dataclasses import dataclass

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import Port
from vivado_ip_test.plugins.floating_point.parameters import ALL_OPERATIONS


LAST_MODES = {'None': 'Null', 'A': 'Pass_A_TLAST', 'B': 'Pass_B_TLAST',
              'Operation': 'Pass_OPERATION_TLAST', 'Or': 'OR_all_TLASTs', 'And': 'AND_all_TLASTs'}
EXCEPTION_NAMES = ('UNDERFLOW', 'OVERFLOW', 'INVALID_OP', 'DIVIDE_BY_ZERO',
                   'ACCUM_OVERFLOW', 'ACCUM_INPUT_OVERFLOW')


@dataclass(frozen=True)
class OperandSpec:
    lanes: tuple[tuple[str, tuple[Port, ...]], ...]
    sink_payload: tuple[Port, ...]
    settings: dict
    model_parameters: dict
    clock = None
    capacity = 16
    output_period_ns = 10
    source_timing_pattern = 'floating_point_independent_operands:1.0'

    @property
    def transfer_interval_cycles(self):
        return self.model_parameters['C_RATE']

    @property
    def input_lane_count(self):
        return len(self.lanes)

    @property
    def payload(self):
        return tuple(Port(f'{lane}_{port.name}', port.width, port.scalar)
                     for lane, ports in self.lanes for port in ports)

    @property
    def generated_ports(self):
        return tuple(port for port in self.payload
                     if not port.name.endswith('_tlast') and port.name != 'operation_tdata')

    @property
    def inputs(self):
        return (Port('aclk', scalar=True), Port('aresetn', scalar=True),
                Port('m_axis_result_tready', scalar=True),
                *(Port(f's_axis_{lane}_tvalid', scalar=True) for lane, _ in self.lanes),
                *(Port(f's_axis_{port.name}', port.width, port.scalar) for port in self.payload))

    @property
    def outputs(self):
        return (*(Port(f's_axis_{lane}_tready', scalar=True) for lane, _ in self.lanes),
                Port('m_axis_result_tvalid', scalar=True),
                *(Port(f'm_axis_result_{port.name}', port.width, port.scalar) for port in self.sink_payload))

    @property
    def width(self):
        return sum(port.width for port in self.payload)


def build_spec(p, operations, programmable, result_width, result_fraction=0, *, settings=None, model=None, rate=1):
    if not programmable and (p['operation_user_width'] or p['has_operation_last']):
        raise PluginError('Fixed operation has no OPERATION channel')
    last_lanes = [lane for lane in ('a', 'b', 'operation') if p[f'has_{lane}_last']]
    mode = p['last_mode']
    if (not last_lanes) != (mode == 'None'):
        raise PluginError('TLAST mode must match the enabled input TLAST channels')
    if mode in ('A', 'B', 'Operation') and mode.lower() not in last_lanes:
        raise PluginError('Selected TLAST source is not enabled')
    e, precision = p['input_exponent'], p['input_fraction']
    wire_width, result_wire = ((e + precision + 7) // 8) * 8, ((result_width + 7) // 8) * 8
    lanes = []
    for lane in ('a', 'b', 'operation') if programmable else ('a', 'b'):
        ports = [Port('tdata', 8 if lane == 'operation' else wire_width)]
        if p[f'has_{lane}_last']:
            ports.append(Port('tlast', scalar=True))
        if p[f'{lane}_user_width']:
            ports.append(Port('tuser', p[f'{lane}_user_width']))
        lanes.append((lane, tuple(ports)))
    flags = {name: p.get('has_' + name.lower(), False) for name in EXCEPTION_NAMES}
    user_width = sum(p[f'{lane}_user_width'] for lane in ('a', 'b', 'operation')) + sum(flags.values())
    output = [Port('tdata', result_wire)]
    if last_lanes:
        output.append(Port('tlast', scalar=True))
    if user_width:
        output.append(Port('tuser', user_width))
    configuration = {'A_Precision_Type': 'Custom', 'C_A_Exponent_Width': e, 'C_A_Fraction_Width': precision,
        'C_Result_Exponent_Width': result_width - result_fraction, 'C_Result_Fraction_Width': result_fraction,
        'Flow_Control': 'Blocking', 'Axi_Optimize_Goal': p['optimization'], 'Has_RESULT_TREADY': True,
        'Maximum_Latency': True, 'C_Rate': rate, 'Has_ACLKEN': False, 'Has_ARESETn': True,
        'RESULT_TLAST_Behv': LAST_MODES[mode], **{f'C_Has_{name}': value for name, value in flags.items()},
        **(settings or {})}
    parameters = {**{f'C_HAS_{name}': int(name in operations) for name in ALL_OPERATIONS},
        'C_A_WIDTH': e + precision, 'C_A_FRACTION_WIDTH': precision,
        'C_B_WIDTH': e + precision, 'C_B_FRACTION_WIDTH': precision,
        'C_RESULT_WIDTH': result_width, 'C_RESULT_FRACTION_WIDTH': result_fraction,
        'C_HAS_B': 1, 'C_HAS_C': 0, 'C_HAS_OPERATION': int(programmable),
        'C_HAS_ACLKEN': 0, 'C_HAS_ARESETN': 1, 'C_RATE': rate, 'C_FIXED_DATA_UNSIGNED': 0,
        'C_THROTTLE_SCHEME': 1 if p['optimization'] == 'Resources' else 2,
        'C_HAS_RESULT_TLAST': int(bool(last_lanes)), 'C_HAS_RESULT_TUSER': int(bool(user_width)),
        'C_RESULT_TDATA_WIDTH': result_wire, 'C_RESULT_TUSER_WIDTH': user_width or 1,
        **{f'C_HAS_{name}': int(value) for name, value in flags.items()}, **(model or {})}
    for lane in ('a', 'b', 'c', 'operation'):
        width, last = p.get(f'{lane}_user_width', 0), p.get(f'has_{lane}_last', False)
        key = lane.upper()
        configuration.update({f'Has_{key}_TUSER': bool(width), f'Has_{key}_TLAST': last,
                              f'{key}_TUSER_Width': width or 1})
        parameters.update({f'C_HAS_{key}_TUSER': int(bool(width)), f'C_HAS_{key}_TLAST': int(last),
                           f'C_{key}_TUSER_WIDTH': width or 1})
    parameters.update(C_A_TDATA_WIDTH=wire_width, C_B_TDATA_WIDTH=wire_width, C_OPERATION_TDATA_WIDTH=8)
    return OperandSpec(tuple(lanes), tuple(output), configuration, parameters)
