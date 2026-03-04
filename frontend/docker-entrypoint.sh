#!/bin/sh
set -e

# Genera nginx config da template.
# Se FRONTEND_API_KEY è vuota (AUTH_ENABLED=false), rimuove le righe X-API-Key
# per evitare "invalid number of arguments" in proxy_set_header.
if [ -n "$FRONTEND_API_KEY" ]; then
    envsubst '$FRONTEND_API_KEY' < /etc/nginx/nginx.conf.template > /etc/nginx/conf.d/default.conf
else
    grep -v 'X-API-Key' /etc/nginx/nginx.conf.template \
        | envsubst '$FRONTEND_API_KEY' > /etc/nginx/conf.d/default.conf
fi

exec nginx -g 'daemon off;'
