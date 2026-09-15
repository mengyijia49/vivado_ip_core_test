from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.axilite.plugin import AxiLiteIpPlugin
from vivado_ip_test.plugins.common.axilite.spec import AxiLiteSpec, ClockWindow, PulseObservation
from vivado_ip_test.plugins.common.cycle import Port, validate_parameters
from vivado_ip_test.plugins.axi_timer.reference import TimerModel
from vivado_ip_test.plugins.axi_timer.vectors import prepare_operations


class AxiTimerPlugin(AxiLiteIpPlugin):
    ip_type = ip_name = 'axi_timer'
    version = '2.0'

    def describe(self, p):
        validate_parameters(p, {'count_width': range(8, 33, 8), 'channels': range(1, 3),
            **{f'{name}{i}_high': bool for name in ('trigger', 'generate') for i in range(2)}})
        if p['count_width'] not in (8, 16, 32):
            raise PluginError('AXI Timer count_width must be 8, 16 or 32')
        if p['channels'] == 1 and not (p['trigger1_high'] and p['generate1_high']):
            raise PluginError('Disabled timer 1 must keep its default polarities')
        settings = {'COUNT_WIDTH': p['count_width'], 'enable_timer2': p['channels']-1, 'mode_64bit': 0}
        model = {'C_COUNT_WIDTH': p['count_width'], 'C_ONE_TIMER_ONLY': 2-p['channels'],
                 'C_S_AXI_DATA_WIDTH': 32, 'C_S_AXI_ADDR_WIDTH': 5}
        for prefix, field in (('TRIG', 'trigger'), ('GEN', 'generate')):
            for i in range(2):
                high = p[f'{field}{i}_high']
                settings[f'{prefix}{i}_ASSERT'] = 'Active_High' if high else 'Active_Low'
                model[f'C_{prefix}{i}_ASSERT'] = int(high)
        parameters = dict(p)
        return AxiLiteSpec(5,
            tuple(Port(name, scalar=True) for name in ('capturetrig0', 'capturetrig1', 'freeze')),
            tuple(Port(name, scalar=True) for name in ('generateout0', 'generateout1', 'pwm0', 'interrupt')),
            (Port('load', 32), Port('cycles', 8), Port('control', 8), Port('strobe', 4)),
            settings, model, lambda: TimerModel(parameters),
            lambda samples: prepare_operations(samples, parameters), settle_cycles=64,
            window=ClockWindow('freeze'),
            pulses=tuple(PulseObservation(f'generateout{i}', int(p[f'generate{i}_high'])) for i in range(2)))
