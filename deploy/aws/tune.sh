#!/usr/bin/env bash
# Size the scanner's nuclei settings to this server's RAM and save them in
# .env (between the AUTO-TUNE markers). Run automatically by setup.sh and
# update.sh, so after changing the EC2 instance type, just run update.sh.
# To pin your own values instead, put them in .env OUTSIDE the markers and
# set TUNE=off in .env.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
[ -f .env ] || { echo "tune.sh: no .env yet" >&2; exit 1; }

if grep -q "^TUNE='\{0,1\}off'\{0,1\}$" .env; then
  echo "auto-tune disabled (TUNE=off in .env)"; exit 0
fi

mem_kb="${TUNE_MEM_KB:-$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)}"
mem_mb=$(( mem_kb / 1024 ))

if   [ "$mem_mb" -lt 1500 ]; then   # ~1 GB  (t3.micro)
  profile="small (1 GB)";  tags="cve,misconfig,exposure,xss,sqli,lfi,rce,ssrf,redirect,takeover,default-login"
  args="-c 5 -bs 5 -rl 50";     timeout=600;  gomem="300MiB"
elif [ "$mem_mb" -lt 3000 ]; then   # ~2 GB  (t3.small)
  profile="medium (2 GB)"; tags="cve,misconfig,exposure,xss,sqli,lfi,rce,ssrf,redirect,takeover,default-login"
  args="-c 15 -bs 15 -rl 100";  timeout=900;  gomem="1200MiB"
else                                # 4 GB+  (c7i-flex.large, m7i-flex.large)
  profile="large (4 GB+)"; tags=""  # full template set
  args="-c 25 -bs 25 -rl 150";  timeout=1200; gomem="$(( mem_mb * 6 / 10 ))MiB"
fi

tmp="$(mktemp)"
sed '/^# >>> AUTO-TUNE/,/^# <<< AUTO-TUNE/d' .env > "$tmp"
cat >> "$tmp" <<EOT
# >>> AUTO-TUNE (written by tune.sh for ${mem_mb} MB RAM, do not edit inside)
NUCLEI_TAGS='${tags}'
NUCLEI_EXTRA_ARGS='${args}'
NUCLEI_TIMEOUT='${timeout}'
GOMEMLIMIT='${gomem}'
# <<< AUTO-TUNE
EOT
cat "$tmp" > .env && rm -f "$tmp"
echo "nuclei tuned for this server: ${profile}, ${mem_mb} MB RAM -> ${args}, timeout ${timeout}s, templates: ${tags:-all}"
