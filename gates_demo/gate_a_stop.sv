// gates_demo — synthetic reference blocks for the Failure-Fixes report.
// NOT real RideProtect IP: minimal, single-clock DUTs shaped exactly like
// the report's Gates A/B/D/E so every claim in the report is executable.
// Each block ships CORRECT plus a SEEDED-BUG variant (_buggy). The gate
// passes iff: correct version PROVES + buggy version FAILS (negative
// control — proves the check detects) + fixed version PROVES (closure).

// ---- Gate A: stop flag timing ------------------------------------------
// Correct: stop registered exactly when the counter hits 0.
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
            stop_r <= (counter == 4'd0);
        end
    end
    assign stop = stop_r;
    // Debug tap for formal (verification-only output, documented).
    assign cnt_zero = (counter == 4'd0);
endmodule
