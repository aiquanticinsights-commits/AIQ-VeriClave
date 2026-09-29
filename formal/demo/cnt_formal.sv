// Hermetic CI-safe formal demo: 2-bit counter, overflow flag property.
// No external RTL — runs anywhere sby exists; skipped otherwise.
// Immediate-assert style only: this Yosys parses no concurrent |->/##.
module cnt_formal(input wire clk);
    reg rst = 1'b1;
    reg [1:0] cnt = 2'd0;
    always @(posedge clk) begin
        rst <= 1'b0;
        cnt <= cnt + 1'b1;
    end
    wire ovf = (cnt == 2'd3);
    always @(posedge clk) begin
        if (!rst && $past(!rst)) begin
            // Unlabeled: Yosys 0.33 (docker image) predates labeled asserts.
            assert($onehot0({cnt == 2'd0, cnt == 2'd1,
                             cnt == 2'd2, cnt == 2'd3}));
            assert(!ovf || (cnt == 2'd3));
        end
    end
endmodule
