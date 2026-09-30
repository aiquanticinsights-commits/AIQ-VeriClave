// ---- Gate D: brake interlock with input synchronizer ---------------------
// Correct: async brake_i through 2 flops; lock = synced & enable.
module gate_d_brake(input wire clk, input wire rst,
                    input wire brake_i, input wire enable,
                    output wire sync0, output wire sync1,
                    output wire brake_lock);
    reg [1:0] sync;
    always @(posedge clk) begin
        if (rst)
            sync <= 2'b00;
        else
            sync <= {sync[0], brake_i};
    end
    assign sync0 = sync[0];
    assign sync1 = sync[1];
    assign brake_lock = sync[1] & enable;
endmodule
