FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
COPY uis/website/package.json uis/website/package.json
COPY uis/web/package.json uis/web/package.json

RUN npm ci -w uis/website -w uis/web

COPY uis/website uis/website
COPY uis/web uis/web
COPY uis/start.sh uis/start.sh

RUN chmod +x uis/start.sh && sed -i 's/\r$//' uis/start.sh

EXPOSE 3000 3001

CMD ["./uis/start.sh"]
