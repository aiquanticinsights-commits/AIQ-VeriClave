// Hermetic CI-safe formal demo: 2-bit counter, overflow flag property.
// No external RTL — runs anywhere sby exists; skipped otherwise.
module cnt_formal(input wire clk);
    reg rst = 1'b1;
    reg [1:0] cnt = 2'd0;
    always @(posedge clk) begin
        rst <= 1'b0;
        cnt <= cnt + 1'b1;
    end
    wire ovf = (cnt == 2'd3);
    always @(posedge clk) begin
        if (!rst) begin
            A_OVF_ONEHOT: assert property ($onehot0({cnt == 2'd0, cnt == 2'd1,
                                                     cnt == 2'd2, cnt == 2'd3}));
            A_OVF_IMPLIES_MAX: assert property (ovf |-> (cnt == 2'd3));
        end
    end
endmodule
