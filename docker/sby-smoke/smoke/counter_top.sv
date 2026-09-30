// Smoke top: deterministic 2-cycle reset (X-free past chain) + DUT.
module counter_top(input wire clk, input wire en);
    reg [1:0] rcnt = 2'd0;
    always @(posedge clk) begin
        if (rcnt != 2'd2) rcnt <= rcnt + 1'b1;
    end
    wire rst = (rcnt != 2'd2);
    wire [3:0] count;
    counter_smoke dut(.clk(clk), .rst(rst), .en(en), .count(count));
endmodule
