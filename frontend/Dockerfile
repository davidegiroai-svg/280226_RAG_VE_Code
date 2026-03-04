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
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 80

# Lo script gestisce sia FRONTEND_API_KEY valorizzata che vuota
CMD ["/docker-entrypoint.sh"]
