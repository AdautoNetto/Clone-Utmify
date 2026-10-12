#!/bin/sh
# Prepara uma VM Ubuntu da Oracle Cloud (Always Free) para o Vale Tec / Log Pose.
# Rode UMA vez, como root:  sudo sh deploy/oracle-preparar.sh
# Pode rodar de novo sem problema (cada passo confere antes de fazer).
set -eu

# 1) Memória extra em disco (swap): a micro gratuita tem só 1 GB de RAM
if ! swapon --show | grep -q /swapfile; then
  echo "== Criando 3 GB de swap"
  fallocate -l 3G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile >/dev/null
  swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi
sysctl -q -w vm.swappiness=20
grep -q '^vm.swappiness' /etc/sysctl.conf || echo 'vm.swappiness=20' >> /etc/sysctl.conf

# 2) Firewall interno: as imagens Ubuntu da Oracle bloqueiam tudo menos o SSH (22).
#    Libera 80 (certificado/redirect) e 443 (site), antes da regra de REJECT.
for PORTA in 80 443; do
  if ! iptables -C INPUT -p tcp --dport "$PORTA" -m state --state NEW -j ACCEPT 2>/dev/null; then
    echo "== Liberando porta $PORTA no firewall interno"
    LINHA=$(iptables -L INPUT --line-numbers -n | awk '/REJECT/ {print $1; exit}')
    if [ -n "${LINHA:-}" ]; then
      iptables -I INPUT "$LINHA" -p tcp --dport "$PORTA" -m state --state NEW -j ACCEPT
    else
      iptables -A INPUT -p tcp --dport "$PORTA" -m state --state NEW -j ACCEPT
    fi
  fi
done
if command -v netfilter-persistent >/dev/null 2>&1; then
  netfilter-persistent save >/dev/null 2>&1 || true
else
  mkdir -p /etc/iptables && iptables-save > /etc/iptables/rules.v4
fi

echo "OK: swap ativo e portas 80/443 liberadas no servidor."
echo "Lembrete: no painel da Oracle, a 'Lista de Segurança' da sub-rede também precisa liberar 80 e 443."
