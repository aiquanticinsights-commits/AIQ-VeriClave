// Formal top for REAL wb_safety: reset-value properties only.
// The wdt-timeout entry path (50M-cycle threshold) is UNPROVABLE-AT-BUDGET
// per formal_policy.recommend (depth wall) — recorded, never attempted.
module wb_safety_formal(input wire clk);
    reg [1:0] rcnt = 2'd0;
    always @(posedge clk) begin
        if (rcnt != 2'd2) rcnt <= rcnt + 1'b1;
    end
    wire rst = (rcnt != 2'd2);

    wire [31:0] s_wb_dat_r;
    wire        s_wb_ack;
    wire        safe_state, fatal_alert;
    wire [15:0] fault_vector;
    wire [ 3:0] err_inject;
    wb_safety dut (
        .clk(clk), .rst(rst),
        .s_wb_cyc(1'b0), .s_wb_stb(1'b0), .s_wb_we(1'b0),
        .s_wb_adr(32'h0), .s_wb_dat_w(32'h0), .s_wb_sel(4'h0),
        .s_wb_dat_r(s_wb_dat_r), .s_wb_ack(s_wb_ack),
        .safe_state(safe_state), .fatal_alert(fatal_alert),
        .fault_vector(fault_vector), .err_inject(err_inject)
    );

    always @(posedge clk) begin
        if (!rst && $past(!rst)) begin
            S_SAFE_RST: assert(safe_state == 1'b0);
            S_FATAL_RST: assert(fatal_alert == 1'b0);
            S_FAULT_RST: assert(fault_vector == 16'h0);
            S_ACK_IDLE: assert(s_wb_ack == 1'b0);
        end
    end
endmodule
