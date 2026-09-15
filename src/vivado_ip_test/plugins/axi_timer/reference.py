from collections import Counter

from vivado_ip_test.plugins.common.axilite.spec import Action
from vivado_ip_test.plugins.common.cycle import DefinedBits


MDT, UDT, GENT, CAPT, ARHT, LOAD, ENIT, ENT, TINT, PWM, ENALL, CASC = (
    1 << bit for bit in range(12))


class TimerModel:
    """总线操作间暂停计数；窗口结束后允许已发起的重装载完成。"""

    def __init__(self, parameters):
        self.p = dict(parameters)
        self.mask = (1 << self.p['count_width'])-1
        self.event_counts = Counter()
        self.pulses = [0, 0]
        self.reset()

    def reset(self):
        self.control = [0, 0]
        self.load = [0, 0]
        self.count = [0, 0]
        self.stopped = [False, False]
        self.reload_pending = [False, False]
        self.capture_armed = [False, False]
        self.trigger = [1-int(self.p[f'trigger{i}_high']) for i in range(2)]

    def write(self, address, value):
        channel, offset = divmod(address, 16)
        if channel >= self.p['channels'] or offset not in (0, 4):
            return
        if offset == 4:
            self.load[channel] = value & self.mask
            if self.control[channel] & LOAD:
                self.count[channel] = self.load[channel]
            return
        if value & (PWM | CASC):
            raise ValueError('PWM and cascade need their own Timer sequence models')
        flag = self.control[channel] & TINT if not value & TINT else 0
        self.control[channel] = (value & 0x4FF) | flag
        for i in range(self.p['channels']):
            self.control[i] = (self.control[i] & ~ENALL) | (value & ENALL)
            if value & ENALL:
                self.control[i] |= ENT
        if value & LOAD:
            self.count[channel] = self.load[channel]
            self.stopped[channel] = self.reload_pending[channel] = False
            self.event_counts['explicit_load'] += 1

    def read(self, address):
        channel, offset = divmod(address, 16)
        if channel >= self.p['channels'] or offset == 12:
            return 0
        if offset == 0:
            return DefinedBits(self.control[channel], 0xFFF if channel == 0 else 0x7FF,
                               'reserved_control_bits')
        if offset == 4:
            self.capture_armed[channel] = True
            return self.load[channel]
        return self.count[channel]

    def drive(self, command):
        for i in range(self.p['channels']):
            trigger = command[f'capturetrig{i}']
            active_edge = trigger != self.trigger[i] and trigger == int(self.p[f'trigger{i}_high'])
            self.trigger[i] = trigger
            control = self.control[i]
            if active_edge and control & MDT and control & CAPT and control & ENT:
                if self.capture_armed[i] or control & ARHT:
                    self.load[i] = self.count[i]
                    self.capture_armed[i] = False
                    self.control[i] |= TINT
                    self.event_counts[f'capture{i}'] += 1
                else:
                    self.event_counts[f'capture{i}_held'] += 1

    def advance(self, cycles):
        for _ in range(cycles):
            for i in range(self.p['channels']):
                control = self.control[i]
                if control & LOAD or self.reload_pending[i]:
                    self.count[i] = self.load[i]
                    self.reload_pending[i] = False
                elif control & ENT and not self.stopped[i]:
                    direction = -1 if control & UDT else 1
                    previous = self.count[i]
                    self.count[i] = (previous + direction) & self.mask
                    overflow = previous == (0 if direction < 0 else self.mask)
                    if overflow and control & GENT:
                        self.pulses[i] += 1
                    if overflow and not control & MDT:
                        self.control[i] |= TINT
                        self.event_counts[f'rollover{i}'] += 1
                        if control & ARHT:
                            self.reload_pending[i] = True
                        else:
                            self.stopped[i] = True
        # freeze stops counting, not a reload already requested by rollover.
        for i in range(self.p['channels']):
            if self.reload_pending[i]:
                self.count[i] = self.load[i]
                self.reload_pending[i] = False

    def step(self, command):
        action = Action(command['action'])
        if action == Action.RESET:
            self.reset()
        self.drive(command)
        if action == Action.WRITE:
            self.write(command['address'], command['data'])
        elif action == Action.WINDOW:
            self.advance(command['run_cycles'])
        result = {'response': 0 if action in (Action.WRITE, Action.READ) else
                  DefinedBits(0, 0, 'no_bus_response'),
                  'read_data': self.read(command['address']) if action == Action.READ else
                  DefinedBits(0, 0, 'no_read_transfer'),
                  'pwm0': 0, 'interrupt': int(any(c & TINT and c & ENIT for c in self.control))}
        for i in range(2):
            result[f'generateout{i}'] = 1-int(self.p[f'generate{i}_high'])
            result[f'generateout{i}_pulses'] = self.pulses[i]
        self.event_counts[action.name.lower()] += 1
        return result
