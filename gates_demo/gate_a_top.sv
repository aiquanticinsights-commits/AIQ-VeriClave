// Formal top for Gate A (correct + buggy share it; only the DUT file swaps).
// Requirement REQ-A-STOP: stop == 1 exactly one cycle after cnt_zero.
module gate_a_top(input wire clk);
    reg [1:0] rcnt = 2'd0;
    always @(posedge clk) begin
        if (rcnt != 2'd2) rcnt <= rcnt + 1'b1;
    end
    wire rst = (rcnt != 2'd2);
    wire stop, cnt_zero;
    gate_a_stop dut(.clk(clk), .rst(rst), .stop(stop), .cnt_zero(cnt_zero));
    always @(posedge clk) begin
        if (!rst && $past(!rst)) begin
            A_STOP_EXACT: assert(stop == $past(cnt_zero));
        end
    end
endmodule
