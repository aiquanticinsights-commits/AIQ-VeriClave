// Smoke DUT: 4-bit counter with enable. Deliberately tiny (BMC depth 10
// proves in seconds). Self-contained: no external RTL, no sibling tree.
// NOTE: rst is a free input here — the TOP (counter_top.sv) drives a
// deterministic reset so $past chains stay X-free (measured: free rst
// lets the solver exploit X through $past and refutes spuriously).
module counter_smoke(input wire clk, input wire rst, input wire en,
                     output wire [3:0] count);
    reg [3:0] count_r = 4'd0;
    always @(posedge clk) begin
        if (rst)
            count_r <= 4'd0;
        else if (en)
            count_r <= count_r + 4'd1;
    end
    assign count = count_r;
    always @(posedge clk) begin
        if (!rst && $past(!rst)) begin
            SMOKE_COUNT: assert(count_r == $past(count_r) + $past(en));
        end
    end
endmodule
