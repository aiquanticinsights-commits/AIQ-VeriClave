// Formal top for Gate D. REQ-D-SYNC: interlock follows the SYNCED input
// with 2-cycle delay; never the raw asynchronous input.
module gate_d_top(input wire clk, input wire brake_i, input wire enable);
    reg [1:0] rcnt = 2'd0;
    always @(posedge clk) begin
        if (rcnt != 2'd2) rcnt <= rcnt + 1'b1;
    end
    wire rst = (rcnt != 2'd2);
    wire sync0, sync1, brake_lock;
    gate_d_brake dut(.clk(clk), .rst(rst), .brake_i(brake_i), .enable(enable),
                     .sync0(sync0), .sync1(sync1), .brake_lock(brake_lock));
    always @(posedge clk) begin
        if (!rst && $past(!rst)) begin
            D_SYNC1: assert(sync1 == $past(sync0));
            D_LOCK: assert(brake_lock == (sync1 & enable));
        end
    end
endmodule
