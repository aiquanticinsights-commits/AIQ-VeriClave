# SBY smoke image — MINIMAL formal toolchain, not the 745MB suite.
#
# What goes in (measured subset trial, 2026-09-30):
#   yosys binary + sby launcher + share/yosys/python3 + boolector (static)
#   + system python3 (sby imports stdlib only — no bundled python needed).
# Deliberately EXCLUDED: full-suite GUI libs, tcl/tk, ghdl, nextpnr,
#   extra solvers, docs (~700MB rejected with reasons in SBY_SMOKE.json).
# Pinned: oss-cad-suite 2026-09-29 (sha256 below) + ubuntu:24.04.
FROM ubuntu:24.04

ARG OSS_URL=https://github.com/YosysHQ/oss-cad-suite-build/releases/download/2026-09-29/oss-cad-suite-linux-x64-20260929.tgz
ARG OSS_SHA256=eba89154b46ca9829e90d4238ed28e85b25d6ce9b8eb331076a32f10c81d0aff

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-click ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp/oss
# Suite yosys needs a NEWER glibc than ubuntu:24.04 ships, so it must run
# under the suite's own loader+libc (same mechanism as the suite's own
# bin/ wrappers). Only the C/C++/tcl/readline runtime set is extracted —
# no GUI, ghdl, python bundle, docs, or extra solvers.
RUN curl -sfL -o suite.tgz "$OSS_URL" \
 && echo "$OSS_SHA256  suite.tgz" | sha256sum -c - \
 && mkdir -p /opt/formal && cd /opt/formal \
 && tar xzf /tmp/oss/suite.tgz --wildcards \
      "*/libexec/sby" "*/libexec/yosys" "*/libexec/yosys-smtbmc" \
      "*/bin/boolector" "*/share/yosys/python3/*" \
      "*/lib/ld-linux*" "*/lib/libc.so*" "*/lib/libm.so*" \
      "*/lib/libstdc++.so*" "*/lib/libgcc_s*" "*/lib/libtcl8.6*" \
      "*/lib/libreadline*" "*/lib/libz.so*" "*/lib/libffi*" \
      "*/lib/libtinfo*" "*/lib/libncurses*" \
 && mv oss-cad-suite smk && rm -rf /tmp/oss \
 && mkdir -p /opt/formal/smk/bin \
 && printf '#!/bin/sh\nHERE="$(dirname "$(readlink -f "$0")")"\nexec "$HERE/../lib/ld-linux-x86-64.so.2" --library-path "$HERE/../lib" "$HERE/../libexec/yosys" "$@"\n' \
      > /opt/formal/smk/bin/yosys \
 && printf '#!/bin/sh\nHERE="$(dirname "$(readlink -f "$0")")"\nexport PYTHONPATH="$HERE/../share/yosys/python3${PYTHONPATH:+:$PYTHONPATH}"\nexec python3 "$HERE/../libexec/sby" "$@"\n' \
      > /opt/formal/smk/bin/sby \
 && printf '#!/bin/sh\nHERE="$(dirname "$(readlink -f "$0")")"\nexec python3 "$HERE/../libexec/yosys-smtbmc" "$@"\n' \
      > /opt/formal/smk/bin/yosys-smtbmc \
 && chmod +x /opt/formal/smk/bin/* \
 && /opt/formal/smk/bin/yosys -V \
 && /opt/formal/smk/bin/boolector --version
ENV PATH="/opt/formal/smk/bin:${PATH}" \
    PYTHONPATH="/opt/formal/smk/share/yosys/python3"

WORKDIR /smoke
COPY smoke/ /smoke/
COPY run_smoke.sh /smoke/run_smoke.sh
RUN chmod +x /smoke/run_smoke.sh
ENTRYPOINT ["/smoke/run_smoke.sh"]
