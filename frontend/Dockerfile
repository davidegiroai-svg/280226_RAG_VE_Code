# Stage 1: Build React app
FROM node:20-alpine AS builder

WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Serve with nginx + API key proxy injection
FROM nginx:alpine

# gettext fornisce envsubst per sostituire variabili d'ambiente nel template
RUN apk add --no-cache gettext

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/nginx.conf.template

EXPOSE 80

# envsubst sostituisce solo ${FRONTEND_API_KEY}, lasciando le variabili nginx ($uri, $host, ecc.) intatte
CMD ["/bin/sh", "-c", \
  "envsubst '$FRONTEND_API_KEY' < /etc/nginx/nginx.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
