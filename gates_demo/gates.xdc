# Demo timing constraints (verification-only): 100 MHz clock only.
# Deliberately NO input/output delays: these blocks have no board context,
# and invented IO numbers previously produced pad-path violations that said
# nothing about the designs. What IS measured: internal register-to-register
# timing at 100 MHz. Not a sign-off — a board-real XDC is still required
# for any tapeout/bring-up claim.
create_clock -period 10.000 -name clk [get_ports clk]
set_false_path -from [all_inputs]
set_false_path -to [all_outputs]
