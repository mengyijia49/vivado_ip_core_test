from vivado_ip_test.plugins.common.cycle import DefinedBits


class ProcessorResetModel:
    """PG164 reset filtering and ordered-release reference model."""

    RELEASE_BUS = 31
    RELEASE_PERIPHERAL = RELEASE_BUS + 16
    RELEASE_MB = RELEASE_PERIPHERAL + 16
    TRANSITION_MARGIN = 2

    def __init__(self, parameters):
        self.p = parameters
        self.ext_latched = False
        self.aux_latched = False
        self.ext_active_streak = self.ext_inactive_streak = 0
        self.aux_active_streak = self.aux_inactive_streak = 0
        self.release_count = -16  # PG164 specifies a 16-cycle power-on reset.
        self.entry_uncertain = 0
        self.was_requested = False
        self.event_counts = {"qualified_ext_resets": 0, "qualified_aux_resets": 0,
                             "dcm_unlock_cycles": 0, "masked_transition_cycles": 0,
                             "released_cycles": 0}

    @staticmethod
    def _active(value, active_high):
        return bool(value) == active_high

    @staticmethod
    def _update_filter(active, width, latched, active_streak, inactive_streak):
        active_streak = active_streak + 1 if active else 0
        inactive_streak = 0 if active else inactive_streak + 1
        became_active = not latched and active_streak >= width
        became_inactive = latched and inactive_streak >= width
        if became_active:
            latched = True
        elif became_inactive:
            latched = False
        return latched, active_streak, inactive_streak, became_active

    def _values(self, bus_active, peripheral_active, mb_active):
        ones = lambda width: (1 << width) - 1
        return {
            "mb_reset": int(mb_active),
            "bus_struct_reset": ones(self.p["bus_reset_count"]) if bus_active else 0,
            "peripheral_reset": ones(self.p["peripheral_reset_count"]) if peripheral_active else 0,
            "interconnect_aresetn": 0 if bus_active else ones(self.p["interconnect_aresetn_count"]),
            "peripheral_aresetn": 0 if peripheral_active else ones(self.p["peripheral_aresetn_count"]),
        }

    def _masked(self, values, reason):
        self.event_counts["masked_transition_cycles"] += 1
        return {name: DefinedBits(value, 0, reason) for name, value in values.items()}

    def step(self, inputs):
        ext_active = (self._active(inputs["ext_reset_in"], self.p["ext_active_high"])
                      or bool(inputs["mb_debug_sys_rst"]))
        aux_active = self._active(inputs["aux_reset_in"], self.p["aux_active_high"])
        old_ext, old_aux = self.ext_latched, self.aux_latched
        (self.ext_latched, self.ext_active_streak, self.ext_inactive_streak,
         ext_started) = self._update_filter(
            ext_active, self.p["ext_reset_width"], self.ext_latched,
            self.ext_active_streak, self.ext_inactive_streak)
        (self.aux_latched, self.aux_active_streak, self.aux_inactive_streak,
         aux_started) = self._update_filter(
            aux_active, self.p["aux_reset_width"], self.aux_latched,
            self.aux_active_streak, self.aux_inactive_streak)
        if ext_started:
            self.event_counts["qualified_ext_resets"] += 1
        if aux_started:
            self.event_counts["qualified_aux_resets"] += 1

        unlocked = not inputs["dcm_locked"]
        if unlocked:
            self.event_counts["dcm_unlock_cycles"] += 1
        requested = self.ext_latched or self.aux_latched or unlocked
        if requested:
            self.release_count = 0
            if not self.was_requested:
                self.entry_uncertain = 2 if unlocked and not (ext_started or aux_started) else 7
            self.was_requested = True
        else:
            if self.was_requested:
                # Input synchronization precedes the configured filter. Keep its
                # latency outside the documented 16-cycle output sequencing;
                # dcm_locked does not use this input filter.
                self.release_count = -5 if old_ext or old_aux else 0
            self.was_requested = False
            self.release_count += 1

        if requested or self.release_count < self.RELEASE_BUS:
            values = self._values(True, True, True)
        elif self.release_count < self.RELEASE_PERIPHERAL:
            values = self._values(False, True, True)
        elif self.release_count < self.RELEASE_MB:
            values = self._values(False, False, True)
        else:
            values = self._values(False, False, False)
            self.event_counts["released_cycles"] += 1

        if self.entry_uncertain:
            self.entry_uncertain -= 1
            return self._masked(values, "异步输入同步和复位进入允许少量周期差异")
        transitions = (self.RELEASE_BUS, self.RELEASE_PERIPHERAL, self.RELEASE_MB)
        if any(abs(self.release_count - edge) <= self.TRANSITION_MARGIN for edge in transitions):
            return self._masked(values, "PG164 允许输入同步器产生一至两个周期的不确定延迟")
        return values
