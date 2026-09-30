// Gate D SEEDED BUG: brake_i used DIRECTLY (no synchronizer). The interlock
// answers in 0 cycles instead of 2 — the delay property must FAIL here
// (in silicon: metastability/glitch exposure on brake_lock).
module gate_d_brake(input wire clk, input wire rst,
                    input wire brake_i, input wire enable,
                    output wire sync0, output wire sync1,
                    output wire brake_lock);
    assign sync0 = brake_i;
    assign sync1 = brake_i;
    assign brake_lock = brake_i & enable;
endmodule
