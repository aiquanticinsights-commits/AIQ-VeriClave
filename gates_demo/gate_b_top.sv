// Formal top for Gate B. REQ-B-SYNC: two-cycle delay through the chain.
module gate_b_top(input wire clk, input wire async_tout);
    reg [1:0] rcnt = 2'd0;
    always @(posedge clk) begin
        if (rcnt != 2'd2) rcnt <= rcnt + 1'b1;
    end
    wire rst = (rcnt != 2'd2);
    wire sync0, sync1, wdog_rst;
    gate_b_wdog dut(.clk(clk), .rst(rst), .async_tout(async_tout),
                    .sync0(sync0), .sync1(sync1), .wdog_rst(wdog_rst));
    always @(posedge clk) begin
        if (!rst && $past(!rst)) begin
            B_SYNC0: assert(sync0 == $past(async_tout));
            B_SYNC1: assert(sync1 == $past(sync0));
            B_RST: assert(wdog_rst == sync1);
        end
    end
endmodule
