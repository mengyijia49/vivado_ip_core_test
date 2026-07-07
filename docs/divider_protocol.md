# Divider Generator Protocol Analysis

Scope: this document analyzes the generated `divider_u16_u8` Divider Generator IP files:

- `runs/divider_u16_u8/proj/divider_ip_test.gen/sources_1/ip/div_gen_0/demo_tb/tb_div_gen_0.vhd`
- `runs/divider_u16_u8/proj/divider_ip_test.gen/sources_1/ip/div_gen_0/sim/div_gen_0.vhd`
- `runs/divider_u16_u8/proj/divider_ip_test.srcs/sources_1/ip/div_gen_0/div_gen_0.xci`

No generated Vivado files were modified.

## `div_gen_0` Ports

The generated simulation wrapper entity exposes these top-level ports:

| Port | Direction | Width | Notes |
| --- | --- | --- | --- |
| `aclk` | input | 1 | Master clock. |
| `s_axis_divisor_tvalid` | input | 1 | Divisor input valid. |
| `s_axis_divisor_tdata` | input | 8 | Divisor input payload. |
| `s_axis_dividend_tvalid` | input | 1 | Dividend input valid. |
| `s_axis_dividend_tdata` | input | 16 | Dividend input payload. |
| `m_axis_dout_tvalid` | output | 1 | Result output valid. |
| `m_axis_dout_tdata` | output | 24 | Result output payload. |

The clock port is `aclk`.

There is no reset port on the exposed `div_gen_0` wrapper. The internal core has an `aresetn` connection, but this generated wrapper ties it to `'1'`, and the XCI/model parameters show `ARESETN = false` / `C_HAS_ARESETN = 0`.

## Input Channels

Dividend input ports:

- `s_axis_dividend_tvalid`
- `s_axis_dividend_tdata(15 downto 0)`

Divisor input ports:

- `s_axis_divisor_tvalid`
- `s_axis_divisor_tdata(7 downto 0)`

The XCI and wrapper describe these as AXI-Stream style slave interfaces named `S_AXIS_DIVIDEND` and `S_AXIS_DIVISOR`, but for the current `NonBlocking` configuration they only expose `TVALID` and `TDATA`. There is no exposed `TREADY`, `TLAST`, `TUSER`, `TKEEP`, or `TSTRB`.

## Output Channel

DOUT output ports:

- `m_axis_dout_tvalid`
- `m_axis_dout_tdata(23 downto 0)`

The XCI and wrapper describe this as an AXI-Stream style master interface named `M_AXIS_DOUT`, but it only exposes `TVALID` and `TDATA`. There is no exposed `TREADY`, `TLAST`, `TUSER`, `TKEEP`, or `TSTRB`. The internal `m_axis_dout_tready` is tied to `'0'` because `OutTready` / `HAS_TREADY` is disabled for this interface.

For the current `divider_u16_u8` unsigned remainder configuration, the demo testbench breaks `m_axis_dout_tdata` into:

- `remainder <= m_axis_dout_tdata(7 downto 0)`
- `quotient  <= m_axis_dout_tdata(23 downto 8)`

So `dout_tdata` packs the 8-bit remainder in the low bits and the 16-bit quotient above it.

## Current Data Widths

Current `divider_u16_u8` widths:

| Signal | Width |
| --- | ---: |
| `s_axis_dividend_tdata` | 16 bits |
| `s_axis_divisor_tdata` | 8 bits |
| `m_axis_dout_tdata` | 24 bits |

The XCI confirms:

- `dividend_and_quotient_width = 16`
- `divisor_width = 8`
- `remainder_type = Remainder`
- `operand_sign = Unsigned`
- `C_M_AXIS_DOUT_TDATA_WIDTH = 24`

## Demo Testbench Behavior

The official demo testbench instantiates `work.div_gen_0` and drives `aclk` with a 100 ns period.

Input generation:

- It creates a dividend table of walking-one 16-bit values.
- It creates a divisor table of 8-bit values with bit 0 set, avoiding zero divisors in the generated pattern.
- It drives signals after each rising edge of `aclk`, delayed by `T_HOLD`.
- Phase 1 drives both dividend and divisor `tvalid` high every cycle.
- Phase 2 keeps divisor valid, but periodically deasserts dividend valid.
- Phase 3 periodically deasserts both channels at different rates.
- When a channel's `tvalid` is low, the corresponding `tdata` is driven to the `INVALID` constant, which is `'0'`.
- The input data index for each channel increments only when that channel's `tvalid` is high.

Output handling:

- The testbench samples output after each rising edge of `aclk`, delayed by `T_STROBE`.
- It does not check numeric quotient/remainder correctness.
- It only checks protocol validity: when `m_axis_dout_tvalid = '1'`, `m_axis_dout_tdata` must not contain unknown (`X`) values.
- If the output payload contains `X` while valid is high, it reports an error and terminates with failure.
- Otherwise the test ends after `TEST_CYCLES` by reporting "Test completed successfully".

## Implications for `input.bin -> testbench -> actual_output.bin`

For a file-driven testbench, keep these handshake rules:

- Drive `aclk`; there is no external reset to sequence.
- Present dividend data on `s_axis_dividend_tdata` only when `s_axis_dividend_tvalid = '1'`.
- Present divisor data on `s_axis_divisor_tdata` only when `s_axis_divisor_tvalid = '1'`.
- Because no `tready` ports are exposed, the testbench cannot wait for ready. It should treat a cycle with `tvalid = '1'` as an offered/accepted beat for that channel, matching the generated demo style.
- For paired division test vectors, assert both `s_axis_dividend_tvalid` and `s_axis_divisor_tvalid` together for each input record unless deliberately testing missing-channel behavior.
- Keep each valid input payload stable for the clock cycle in which its `tvalid` is asserted.
- Capture output only on cycles where `m_axis_dout_tvalid = '1'`.
- Decode `m_axis_dout_tdata(7 downto 0)` as remainder and `m_axis_dout_tdata(23 downto 8)` as quotient for this `u16/u8` configuration.
- Since there is no output `tready`, the sink cannot apply backpressure. The testbench must always be ready to record every cycle where `m_axis_dout_tvalid = '1'`.
- The testbench needs an expected output count or an end-of-input plus drain timeout, because the IP has pipeline latency (`C_LATENCY = 18`) and output appears later than input.
