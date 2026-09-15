from vivado_ip_test.plugins.registry import PluginRegistry
from vivado_ip_test.plugins.divider import DividerPlugin
from vivado_ip_test.plugins.multiplier import MultiplierPlugin
from vivado_ip_test.plugins.adder_subtractor.plugin import AdderSubtractorPlugin
from vivado_ip_test.plugins.accumulator.plugin import AccumulatorPlugin
from vivado_ip_test.plugins.counter.plugin import CounterPlugin
from vivado_ip_test.plugins.shift_register.plugin import ShiftRegisterPlugin
from vivado_ip_test.plugins.distributed_memory.plugin import DistributedMemoryPlugin
from vivado_ip_test.plugins.vector_logic.plugin import VectorLogicPlugin
from vivado_ip_test.plugins.reduced_logic.plugin import ReducedLogicPlugin
from vivado_ip_test.plugins.axis_register_slice.plugin import AxisRegisterSlicePlugin
from vivado_ip_test.plugins.axis_data_fifo.plugin import AxisDataFifoPlugin
from vivado_ip_test.plugins.axis_clock_converter.plugin import AxisClockConverterPlugin
from vivado_ip_test.plugins.block_memory.plugin import BlockMemoryPlugin
from vivado_ip_test.plugins.fifo_generator.plugin import FifoGeneratorPlugin
from vivado_ip_test.plugins.multiply_adder.plugin import MultiplyAdderPlugin
from vivado_ip_test.plugins.complex_multiplier.plugin import ComplexMultiplierPlugin
from vivado_ip_test.plugins.tmr_voter.plugin import TmrVoterPlugin
from vivado_ip_test.plugins.tmr_comparator.plugin import TmrComparatorPlugin
from vivado_ip_test.plugins.axis_dwidth_converter.plugin import AxisDwidthConverterPlugin
from vivado_ip_test.plugins.axis_subset_converter.plugin import AxisSubsetConverterPlugin
from vivado_ip_test.plugins.axis_broadcaster.plugin import AxisBroadcasterPlugin
from vivado_ip_test.plugins.axis_combiner.plugin import AxisCombinerPlugin
from vivado_ip_test.plugins.axis_switch.plugin import AxisSwitchPlugin
from vivado_ip_test.plugins.axi_gpio.plugin import AxiGpioPlugin
from vivado_ip_test.plugins.axi_timer.plugin import AxiTimerPlugin
from vivado_ip_test.plugins.axi_intc.plugin import AxiIntcPlugin
from vivado_ip_test.plugins.xlconcat.plugin import XlConcatPlugin
from vivado_ip_test.plugins.xlslice.plugin import XlSlicePlugin
from vivado_ip_test.plugins.xlconstant.plugin import XlConstantPlugin
from vivado_ip_test.plugins.ilconcat.plugin import IlConcatPlugin
from vivado_ip_test.plugins.ilslice.plugin import IlSlicePlugin
from vivado_ip_test.plugins.ilconstant.plugin import IlConstantPlugin
from vivado_ip_test.plugins.ilvector_logic.plugin import IlVectorLogicPlugin
from vivado_ip_test.plugins.ilreduced_logic.plugin import IlReducedLogicPlugin
from vivado_ip_test.plugins.cordic.plugin import CordicPlugin
from vivado_ip_test.plugins.floating_point.plugin import FloatingPointPlugin


PLUGIN_TYPES = (DividerPlugin, MultiplierPlugin, AdderSubtractorPlugin, AccumulatorPlugin,
                CounterPlugin, ShiftRegisterPlugin, DistributedMemoryPlugin,
                VectorLogicPlugin, ReducedLogicPlugin, AxisRegisterSlicePlugin,
                AxisDataFifoPlugin, AxisClockConverterPlugin, BlockMemoryPlugin, FifoGeneratorPlugin,
                MultiplyAdderPlugin, ComplexMultiplierPlugin, TmrVoterPlugin, TmrComparatorPlugin,
                AxisDwidthConverterPlugin, AxisSubsetConverterPlugin, AxisBroadcasterPlugin, AxisCombinerPlugin,
                AxisSwitchPlugin, AxiGpioPlugin, XlConcatPlugin, XlSlicePlugin, XlConstantPlugin,
                IlConcatPlugin, IlSlicePlugin, IlConstantPlugin, IlVectorLogicPlugin, IlReducedLogicPlugin,
                CordicPlugin, FloatingPointPlugin, AxiTimerPlugin, AxiIntcPlugin)


def create_plugin_registry(layout, strategies):
    registry = PluginRegistry()
    for plugin_type in PLUGIN_TYPES:
        registry.register(plugin_type(layout, strategies))
    return registry
