`timescale 1ns/1ps

module tb_i2s_transmitter;
  localparam int C_SAMPLE_WIDTH = @@sample_width@@;
  localparam int C_SLOT_WIDTH = @@slot_width@@;
  localparam int C_LANES = @@lanes@@;
  localparam int C_INPUT_COUNT = @@input_count@@;
  localparam int C_EXPECTED_COUNT = @@expected_count@@;
  localparam logic [C_SAMPLE_WIDTH-1:0] C_SYNC_SAMPLE = @@sync_sample@@;

  logic clk = 0;
  logic aud_clk = 0;
  logic resetn = 0;
  logic aud_mrst = 1;
  logic [7:0] awaddr = 0, araddr = 0;
  logic awvalid = 0, wvalid = 0, bready = 0, arvalid = 0, rready = 0;
  wire awready, wready, bvalid, arready, rvalid;
  logic [31:0] wdata = 0;
  wire [31:0] rdata;
  wire [1:0] bresp, rresp;
  logic [31:0] axis_tdata = 0;
  logic [2:0] axis_tid = 0;
  logic axis_tvalid = 0;
  wire axis_tready, irq, lrclk, sclk;
@@lane_signals@@

  always #5 clk = ~clk;
  always #13.572 aud_clk = ~aud_clk;

  dut_0 dut (
    .s_axi_ctrl_aclk(clk), .s_axi_ctrl_aresetn(resetn),
    .aud_mclk(aud_clk), .aud_mrst(aud_mrst),
    .s_axis_aud_aclk(clk), .s_axis_aud_aresetn(resetn),
    .s_axi_ctrl_awaddr(awaddr), .s_axi_ctrl_awvalid(awvalid),
    .s_axi_ctrl_awready(awready), .s_axi_ctrl_wdata(wdata),
    .s_axi_ctrl_wvalid(wvalid), .s_axi_ctrl_wready(wready),
    .s_axi_ctrl_bresp(bresp), .s_axi_ctrl_bvalid(bvalid), .s_axi_ctrl_bready(bready),
    .s_axi_ctrl_araddr(araddr), .s_axi_ctrl_arvalid(arvalid),
    .s_axi_ctrl_arready(arready), .s_axi_ctrl_rdata(rdata),
    .s_axi_ctrl_rresp(rresp), .s_axi_ctrl_rvalid(rvalid), .s_axi_ctrl_rready(rready),
    .s_axis_aud_tdata(axis_tdata), .s_axis_aud_tid(axis_tid),
    .s_axis_aud_tvalid(axis_tvalid), .s_axis_aud_tready(axis_tready),
    .irq(irq), .lrclk_out(lrclk), .sclk_out(sclk)@@lane_mapping@@
  );

  task automatic axi_write(input logic [7:0] address, input logic [31:0] data);
    @(negedge clk); awaddr = address; awvalid = 1;
    while (!awready) @(posedge clk);
    @(negedge clk); awvalid = 0; wdata = data; wvalid = 1;
    while (!wready) @(posedge clk);
    @(negedge clk); wvalid = 0; bready = 1;
    while (!bvalid) @(posedge clk);
    if (bresp !== 2'b00) $fatal(1, "I2S_TRANSMITTER_STATUS: FAIL AXI response");
    @(negedge clk); bready = 0;
  endtask

  integer input_file;
  integer scan_status;
  logic [34:0] input_word;
  initial begin
    repeat (20) @(posedge clk);
    @(negedge clk); resetn = 1; aud_mrst = 0;
    repeat (12) @(posedge clk);
    axi_write(8'h20, @@sclk_divider@@);
    axi_write(8'h08, 1);
    #10000;
    input_file = $fopen("@@input_path@@", "r");
    if (!input_file) $fatal(1, "I2S_TRANSMITTER_STATUS: FAIL input open");
    for (int item = 0; item < C_INPUT_COUNT; item++) begin
      scan_status = $fscanf(input_file, "%b\n", input_word);
      if (scan_status != 1) $fatal(1, "I2S_TRANSMITTER_STATUS: FAIL input vector");
      @(negedge clk); axis_tid = input_word[34:32]; axis_tdata = input_word[31:0]; axis_tvalid = 1;
      do @(posedge clk); while (!axis_tready);
    end
    @(negedge clk); axis_tvalid = 0;
    $fclose(input_file);
  end

  integer actual_file;
  logic [C_SAMPLE_WIDTH-1:0] captured [0:C_LANES-1];
  logic previous_lr;
  bit have_lr = 0, collecting = 0, output_started = 0;
  int bit_index = 0, output_count = 0;
  initial actual_file = $fopen("@@actual_path@@", "w");

  task automatic emit_captured(input logic side);
    if (!output_started && !side && captured[0] == C_SYNC_SAMPLE) output_started = 1;
    if (output_started) begin
      for (int lane = 0; lane < C_LANES; lane++) begin
        $fdisplay(actual_file, "%b", captured[lane]);
        $fflush(actual_file); output_count++;
      end
      if (output_count == C_EXPECTED_COUNT) begin
        $display("I2S_TRANSMITTER_STATUS: PASS");
        $finish;
      end
    end
  endtask

  always @(posedge sclk) begin
    #0.001;
    if (!have_lr) begin
      previous_lr = lrclk; have_lr = 1;
    end else if (lrclk != previous_lr) begin
      if (collecting && C_SLOT_WIDTH == C_SAMPLE_WIDTH) begin
        bit_index = C_SAMPLE_WIDTH - 1;
@@lane_capture@@
        emit_captured(previous_lr);
      end
      previous_lr = lrclk; collecting = 1; bit_index = 0;
      for (int lane = 0; lane < C_LANES; lane++) captured[lane] = '0;
    end else if (collecting) begin
@@lane_capture@@
      if (bit_index == C_SAMPLE_WIDTH - 1) begin
        emit_captured(previous_lr);
        collecting = 0;
      end else bit_index++;
    end
  end

  initial begin
    #@@timeout_ns@@;
    $fatal(1, "I2S_TRANSMITTER_STATUS: FAIL watchdog timeout");
  end
endmodule
