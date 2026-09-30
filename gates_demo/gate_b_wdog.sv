// ---- Gate B: watchdog timeout -> synchronized reset ----------------------
// Correct: async tout through a 2-flop synchronizer; SINGLE reset driver
// (the report's sketch drives rst_n from two always blocks — multi-driver,
// rejected here). Sync stages are debug outputs so formal stays top-level.
module gate_b_wdog(input wire clk, input wire rst,
                   input wire async_tout,
                   output wire sync0, output wire sync1,
                   output wire wdog_rst);
    reg [1:0] sync;
    always @(posedge clk) begin
        if (rst)
            sync <= 2'b00;
        else
            sync <= {sync[0], async_tout};
    end
    assign sync0 = sync[0];
    assign sync1 = sync[1];
    assign wdog_rst = sync[1];
endmodule
