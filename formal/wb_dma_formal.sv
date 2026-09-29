// wb_dma formal wrapper — requirement-linked properties (frozen item 1).
//
// Deterministic 2-cycle reset; all DUT stimulus inputs are top-level free
// inputs (any value, every cycle). Properties must hold universally:
//
//   REQ-DMA-ACK (T1): (s_wb_cyc && s_wb_stb) |-> ##1 s_wb_ack
//       RTL: s_wb_ack <= (s_wb_cyc && s_wb_stb) ? 1 : 0  (registered)
//   REQ-DMA-IRQ (T2): irq |-> irq_en
//       RTL: assign irq = irq_flag & irq_en  (structural)
//   REQ-DMA-CYC (T7): m_wb_stb |-> m_wb_cyc
//       RTL: cyc = (state != IDLE), stb = (state == READ/WRITE)  (structural)
//
// The two structural properties should prove trivially; ACK exercises BMC.
module wb_dma_formal (
    input wire        clk,
    input wire        s_wb_cyc,
    input wire        s_wb_stb,
    input wire        s_wb_we,
    input wire [31:0] s_wb_adr,
    input wire [31:0] s_wb_dat_w,
    input wire [ 3:0] s_wb_sel,
    input wire [31:0] m_wb_dat_r,
    input wire        m_wb_ack
);
    reg [1:0] reset_cnt = 2'd0;
    always @(posedge clk) begin
        if (reset_cnt != 2'd2)
            reset_cnt <= reset_cnt + 1'b1;
    end
    wire rst = (reset_cnt != 2'd2);

    wire [31:0] s_wb_dat_r;
    wire        s_wb_ack;
    wire        m_wb_cyc;
    wire        m_wb_stb;
    wire        m_wb_we;
    wire [31:0] m_wb_adr;
    wire [31:0] m_wb_dat_w;
    wire [ 3:0] m_wb_sel;
    wire        irq;

    wb_dma dut (
        .clk(clk), .rst(rst),
        .s_wb_cyc(s_wb_cyc), .s_wb_stb(s_wb_stb), .s_wb_we(s_wb_we),
        .s_wb_adr(s_wb_adr), .s_wb_dat_w(s_wb_dat_w), .s_wb_sel(s_wb_sel),
        .s_wb_dat_r(s_wb_dat_r), .s_wb_ack(s_wb_ack),
        .m_wb_cyc(m_wb_cyc), .m_wb_stb(m_wb_stb), .m_wb_we(m_wb_we),
        .m_wb_adr(m_wb_adr), .m_wb_dat_w(m_wb_dat_w), .m_wb_sel(m_wb_sel),
        .m_wb_dat_r(m_wb_dat_r), .m_wb_ack(m_wb_ack),
        .irq(irq)
    );

    // Immediate-assert style with $past: this Yosys parses no concurrent
    // |-> / ## / @(posedge)-in-property syntax (measured). The ACK property
    // is exact-cycle (ack == past(cyc&&stb)) — faithful to the RTL, which
    // registers ack in exactly one cycle, and stronger than "within 2".
    // $past(!rst) guard keeps the reset-exit cycle out of the proof.
    //
    // A_IRQ (irq |-> irq_en) is DELIBERATELY absent: irq_en is DUT-internal
    // and this toolchain does not resolve hierarchical references
    // (proven by formal/demo/hier.sby — even dut.inner==1 fails). It stays
    // NOT_EXECUTED-via-formal with that reason; T2 remains lint-checked
    // until sim/FRM exercises irq behavior (item 2).
    always @(posedge clk) begin
        if (!rst && $past(!rst)) begin
            A_ACK: assert(s_wb_ack == $past(s_wb_cyc && s_wb_stb));
            A_CYC: assert(!m_wb_stb || m_wb_cyc);
        end
    end
endmodule
