// Gate B SEEDED BUG: single-flop "synchronizer" — async tout reaches the
// reset output after ONE cycle instead of two. The 2-cycle delay property
// must FAIL on this file (in silicon: metastability exposure).
module gate_b_wdog(input wire clk, input wire rst,
                   input wire async_tout,
                   output wire sync0, output wire sync1,
                   output wire wdog_rst);
    reg s0;
    always @(posedge clk) begin
        if (rst)
            s0 <= 1'b0;
        else
            s0 <= async_tout;
    end
    assign sync0 = s0;
    assign sync1 = s0;
    assign wdog_rst = s0;
endmodule
