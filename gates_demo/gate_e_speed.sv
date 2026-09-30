// ---- Gate E: speed-limit comparator --------------------------------------
// Correct: over_limit at speed >= LIMIT (LIMIT=100).
module gate_e_speed(input wire clk, input wire rst,
                    input wire [7:0] speed,
                    output wire over_limit);
    reg over_r;
    always @(posedge clk) begin
        if (rst)
            over_r <= 1'b0;
        else
            over_r <= (speed >= 8'd100);
    end
    assign over_limit = over_r;
endmodule
