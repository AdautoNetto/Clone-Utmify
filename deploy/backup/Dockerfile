# Mesmo Postgres do banco: pg_dump precisa ser da mesma versão (ou mais nova)
FROM postgres:16-alpine

# Fuso de Brasília para o horário agendado (garante mesmo se a imagem base mudar)
RUN apk add --no-cache tzdata

COPY backup.sh /usr/local/bin/backup.sh
RUN chmod +x /usr/local/bin/backup.sh

# "unhealthy" se o último backup bom tiver mais de 26 horas
HEALTHCHECK --interval=1h --timeout=10s --start-period=10m \
  CMD find /backups/ULTIMO-BACKUP-OK -mmin -1560 | grep -q . || exit 1

ENTRYPOINT ["/usr/local/bin/backup.sh"]
CMD ["loop"]
