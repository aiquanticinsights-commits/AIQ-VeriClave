// Formal top for REAL wb_watchdog: programmed end-to-end proof.
// The wrapper programs the DUT over its own slave bus (compare=3,
// enabled=1), then checks: ack timing + single-cycle timeout pulse.
// REQ-WDT-ACK/REQ-WDT-PULSE. No hierarchy, no assumptions beyond reset.
module wb_watchdog_formal(input wire clk);
    reg [1:0] rcnt = 2'd0;
    always @(posedge clk) begin
        if (rcnt != 2'd2) rcnt <= rcnt + 1'b1;
    end
    wire rst = (rcnt != 2'd2);

    // Program sequencer: W reg0 dat=1 (enable) | W reg1 dat=3 (compare) |
    // wait | observe. Each bus op: present, sample(held), idle.
    reg [4:0] step = 5'd0;
    reg s_cyc, s_stb, s_we;
    reg [31:0] s_adr, s_dat;
    reg [3:0]  s_sel;
    always @(posedge clk) begin
        if (rst) begin
            step <= 5'd0;
            s_cyc <= 0; s_stb <= 0; s_we <= 0;
            s_adr <= 0; s_dat <= 0; s_sel <= 0;
        end else begin
            step <= step + 5'd1;
            s_cyc <= 0; s_stb <= 0; s_we <= 0;
            case (step)
                // W reg0 (adr 0) dat 1: enable
                5'd0, 5'd1: begin s_cyc <= 1; s_stb <= 1; s_we <= 1;
                    s_adr <= 0; s_dat <= 1; s_sel <= 4'hf; end
                // W reg1 (adr 4) dat 3: compare
                5'd3, 5'd4: begin s_cyc <= 1; s_stb <= 1; s_we <= 1;
                    s_adr <= 4; s_dat <= 3; s_sel <= 4'hf; end
                default: begin end
            endcase
        end
    end

    wire [31:0] s_wb_dat_r;
    wire        s_wb_ack;
    wire        wdt_timeout, wdt_reset, irq;
    wb_watchdog dut (
        .clk(clk), .rst(rst),
        .s_wb_cyc(s_cyc), .s_wb_stb(s_stb), .s_wb_we(s_we),
        .s_wb_adr(s_adr), .s_wb_dat_w(s_dat), .s_wb_sel(s_sel),
        .s_wb_dat_r(s_wb_dat_r), .s_wb_ack(s_wb_ack),
        .wdt_timeout(wdt_timeout), .wdt_reset(wdt_reset), .irq(irq)
    );

    always @(posedge clk) begin
        if (!rst && $past(!rst)) begin
            W_ACK: assert(s_wb_ack == $past(s_cyc && s_stb));
            W_PULSE: assert(!(wdt_timeout && $past(wdt_timeout)));
        end
    end
endmodule
