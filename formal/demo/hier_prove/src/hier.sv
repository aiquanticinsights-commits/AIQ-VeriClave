// Minimal hier-ref test: inner is provably 1 after reset; if the tool
// resolves dut.inner, the assert passes. If it dangles, it fails.
module tiny_dut(input wire clk, input wire rst, output wire o);
    reg inner;
    always @(posedge clk) begin
        if (rst) inner <= 1'b1;
    end
    assign o = inner;
endmodule
module tiny_top(input wire clk, input wire rst);
    wire o;
    tiny_dut dut(.clk(clk), .rst(rst), .o(o));
    reg [1:0] rcnt = 2'd0;
    always @(posedge clk) if (rcnt != 2'd2) rcnt <= rcnt + 1'b1;
    wire r2 = (rcnt != 2'd2);
    always @(posedge clk) begin
        if (!r2 && $past(!r2)) begin
            A_HIER: assert(dut.inner == 1'b1);
        end
    end
endmodule
