// Gate E SEEDED BUG: off-by-one — strict > instead of >=, so speed==100
// does NOT flag. The boundary property must FAIL on this file.
module gate_e_speed(input wire clk, input wire rst,
                    input wire [7:0] speed,
                    output wire over_limit);
    reg over_r;
    always @(posedge clk) begin
        if (rst)
            over_r <= 1'b0;
        else
            over_r <= (speed > 8'd100);
    end
    assign over_limit = over_r;
endmodule
