// wb_dma C++ driver — mirrors WbDmaFrm::run_stim cycle order EXACTLY.
// Any divergence between this file's protocol and the FRM is a harness bug:
// present slave inputs -> settle master stub combinationally -> clock.
// Stimulus: argv[1] DSL file. Trace: stdout (same line format as the FRM).
#include <cstdio>
#include <cstdint>
#include <string>
#include <vector>
#include "Vwb_dma.h"
#include "verilated.h"

static Vwb_dma *dut;
static uint64_t xfers = 0;

static void tick_clock() {
    dut->clk = 0; dut->eval();
    dut->clk = 1; dut->eval();
}

// One harness cycle. Returns post-cycle {ack, dat_r, irq}.
struct Out { bool ack; uint32_t dat_r; bool irq; };
static Out cycle(bool rst = false, bool cyc = false, bool stb = false,
                 bool we = false, uint32_t adr = 0, uint32_t dat_w = 0,
                 uint32_t sel = 0) {
    dut->rst = rst ? 1 : 0;
    dut->s_wb_cyc = cyc ? 1 : 0;
    dut->s_wb_stb = stb ? 1 : 0;
    dut->s_wb_we = we ? 1 : 0;
    dut->s_wb_adr = adr;
    dut->s_wb_dat_w = dat_w;
    dut->s_wb_sel = sel;
    dut->eval();  // settle: sample master request
    bool mstb = dut->m_wb_stb;
    bool mwe = dut->m_wb_we;
    if (mstb) {
        dut->m_wb_ack = 1;
        dut->m_wb_dat_r = 0xA5000000u + (uint32_t)xfers;
        dut->eval();  // settle stub response
    } else {
        dut->m_wb_ack = 0;
    }
    bool was_read = mstb && !mwe;
    tick_clock();
    if (was_read && dut->m_wb_ack) xfers++;
    dut->m_wb_ack = 0;
    Out o{(bool)dut->s_wb_ack, dut->s_wb_dat_r,
          (bool)(dut->irq)};
    return o;
}

int main(int argc, char **argv) {
    Verilated::commandArgs(argc, argv);
    dut = new Vwb_dma;
    dut->clk = 0; dut->rst = 1;
    dut->s_wb_cyc = dut->s_wb_stb = dut->s_wb_we = 0;
    dut->s_wb_adr = dut->s_wb_dat_w = dut->s_wb_sel = 0;
    dut->m_wb_ack = 0; dut->m_wb_dat_r = 0;
    dut->eval();

    FILE *f = fopen(argv[1], "r");
    if (!f) { fprintf(stderr, "no stim file\n"); return 2; }
    char line[256];
    bool last_irq = dut->irq;
    auto emit_irq = [&]() {
        bool q = dut->irq;
        if (q != last_irq) {
            last_irq = q;
            printf("IRQ %d\n", (int)q);
        }
    };
    while (fgets(line, sizeof line, f)) {
        std::string s(line);
        while (!s.empty() && (s.back() == '\n' || s.back() == '\r'))
            s.pop_back();
        if (s.empty()) continue;
        if (s == "rst") {
            cycle(true); cycle(true); emit_irq();
        } else if (s.rfind("tick ", 0) == 0) {
            int n = std::stoi(s.substr(5));
            for (int i = 0; i < n; i++) cycle();
            emit_irq();
        } else if (s.rfind("w ", 0) == 0) {
            uint32_t a, d;
            sscanf(s.c_str() + 2, "%x %x", &a, &d);
            cycle(false, true, true, true, a, d, 0xF);   // present
            Out o = cycle(false, true, true, true, a, d, 0xF);  // sample held
            printf("W %08x %08x ack=%d\n", a, d, (int)o.ack);
            cycle();  // deassert / idle
            emit_irq();
        } else if (s.rfind("r ", 0) == 0) {
            uint32_t a;
            sscanf(s.c_str() + 2, "%x", &a);
            cycle(false, true, true, false, a, 0, 0);    // present
            Out o = cycle(false, true, true, false, a, 0, 0);  // sample held
            printf("R %08x %08x\n", a, o.dat_r);
            cycle();  // deassert / idle
            emit_irq();
        } else {
            fprintf(stderr, "bad stim line: %s\n", s.c_str());
            return 2;
        }
    }
    fclose(f);
    dut->final();
    return 0;
}
