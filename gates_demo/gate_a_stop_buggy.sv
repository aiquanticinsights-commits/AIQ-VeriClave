// Gate A SEEDED BUG: off-by-one — stop fires while counter still reads 1,
// i.e. one cycle early. The A_STOP_EXACT property must FAIL on this file.
module gate_a_stop(input wire clk, input wire rst, output wire stop,
                 output wire cnt_zero);
    reg [3:0] counter;
    reg       stop_r;
    always @(posedge clk) begin
        if (rst) begin
            counter <= 4'd10;
            stop_r  <= 1'b0;
        end else begin
            if (counter != 4'd0)
                counter <= counter - 1'b1;
            stop_r <= (counter == 4'd1);
        end
    end
    assign stop = stop_r;
    // Debug tap for formal (verification-only output, documented).
    assign cnt_zero = (counter == 4'd0);
endmodule
