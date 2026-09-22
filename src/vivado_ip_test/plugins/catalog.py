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
from vivado_ip_test.plugins.fir_compiler.plugin import FirCompilerPlugin
from vivado_ip_test.plugins.dds_compiler.plugin import DdsCompilerPlugin
from vivado_ip_test.plugins.processor_system_reset.plugin import ProcessorSystemResetPlugin
from vivado_ip_test.plugins.clocking_wizard.plugin import ClockingWizardPlugin
from vivado_ip_test.plugins.cic_compiler.plugin import CicCompilerPlugin
from vivado_ip_test.plugins.axi_uartlite.plugin import AxiUartLitePlugin
from vivado_ip_test.plugins.convolution.plugin import ConvolutionPlugin
from vivado_ip_test.plugins.xfft.plugin import XfftPlugin
from vivado_ip_test.plugins.axi_bram_controller.plugin import AxiBramControllerPlugin
from vivado_ip_test.plugins.lmb_bram_controller.plugin import LmbBramControllerPlugin
from vivado_ip_test.plugins.axi_timebase_wdt.plugin import AxiTimebaseWdtPlugin
from vivado_ip_test.plugins.fit_timer.plugin import FitTimerPlugin
from vivado_ip_test.plugins.mutex.plugin import MutexPlugin
from vivado_ip_test.plugins.mailbox.plugin import MailboxPlugin
from vivado_ip_test.plugins.util_ff.plugin import UtilFfPlugin
from vivado_ip_test.plugins.axi_apb_bridge.plugin import AxiApbBridgePlugin
from vivado_ip_test.plugins.axi_fifo_mm_s.plugin import AxiFifoMmSPlugin
from vivado_ip_test.plugins.tmr_inject.plugin import TmrInjectPlugin
from vivado_ip_test.plugins.axi_sideband_util.plugin import AxiSidebandUtilPlugin
from vivado_ip_test.plugins.axi_register_slice.plugin import AxiRegisterSlicePlugin
from vivado_ip_test.plugins.axi_lmb_bridge.plugin import AxiLmbBridgePlugin
from vivado_ip_test.plugins.axi_clock_converter.plugin import AxiClockConverterPlugin
from vivado_ip_test.plugins.axi_protocol_converter.plugin import AxiProtocolConverterPlugin
from vivado_ip_test.plugins.axi_protocol_checker.plugin import AxiProtocolCheckerPlugin
from vivado_ip_test.plugins.axi_memory_init.plugin import AxiMemoryInitPlugin
from vivado_ip_test.plugins.ahblite_axi_bridge.plugin import AhbLiteAxiBridgePlugin
from vivado_ip_test.plugins.axis_protocol_checker.plugin import AxisProtocolCheckerPlugin
from vivado_ip_test.plugins.i2s_transmitter.plugin import I2sTransmitterPlugin


PLUGIN_TYPES = (DividerPlugin, MultiplierPlugin, AdderSubtractorPlugin, AccumulatorPlugin,
                CounterPlugin, ShiftRegisterPlugin, DistributedMemoryPlugin,
                VectorLogicPlugin, ReducedLogicPlugin, AxisRegisterSlicePlugin,
                AxisDataFifoPlugin, AxisClockConverterPlugin, BlockMemoryPlugin, FifoGeneratorPlugin,
                MultiplyAdderPlugin, ComplexMultiplierPlugin, TmrVoterPlugin, TmrComparatorPlugin,
                AxisDwidthConverterPlugin, AxisSubsetConverterPlugin, AxisBroadcasterPlugin, AxisCombinerPlugin,
                AxisSwitchPlugin, AxiGpioPlugin, XlConcatPlugin, XlSlicePlugin, XlConstantPlugin,
                IlConcatPlugin, IlSlicePlugin, IlConstantPlugin, IlVectorLogicPlugin, IlReducedLogicPlugin,
                CordicPlugin, FloatingPointPlugin, FirCompilerPlugin, DdsCompilerPlugin,
                ProcessorSystemResetPlugin, ClockingWizardPlugin, CicCompilerPlugin,
                AxiTimerPlugin, AxiIntcPlugin, AxiUartLitePlugin, ConvolutionPlugin, XfftPlugin,
                AxiBramControllerPlugin, LmbBramControllerPlugin, AxiTimebaseWdtPlugin,
                FitTimerPlugin, MutexPlugin, MailboxPlugin, UtilFfPlugin, AxiApbBridgePlugin,
                AxiFifoMmSPlugin, TmrInjectPlugin, AxiSidebandUtilPlugin,
                AxiRegisterSlicePlugin, AxiLmbBridgePlugin, AxiClockConverterPlugin,
                AxiProtocolConverterPlugin, AxiProtocolCheckerPlugin, AxiMemoryInitPlugin,
                AhbLiteAxiBridgePlugin, AxisProtocolCheckerPlugin, I2sTransmitterPlugin)


def create_plugin_registry(layout, strategies):
    registry = PluginRegistry()
    for plugin_type in PLUGIN_TYPES:
        registry.register(plugin_type(layout, strategies))
    return registry
