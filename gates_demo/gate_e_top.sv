// Formal top for Gate E. REQ-E-LIMIT: over_limit == 1 exactly when the
// previous cycle's speed was >= 100 (registered comparator).
module gate_e_top(input wire clk, input wire [7:0] speed);
    reg [1:0] rcnt = 2'd0;
    always @(posedge clk) begin
        if (rcnt != 2'd2) rcnt <= rcnt + 1'b1;
    end
    wire rst = (rcnt != 2'd2);
    wire over_limit;
    gate_e_speed dut(.clk(clk), .rst(rst), .speed(speed),
                     .over_limit(over_limit));
    always @(posedge clk) begin
        if (!rst && $past(!rst)) begin
            E_LIMIT: assert(over_limit == $past(speed >= 8'd100));
        end
    end
endmodule
