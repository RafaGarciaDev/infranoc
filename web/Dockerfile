FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

EXPOSE 3000

# WATCHPACK_POLLING resolve bind mount + Windows
ENV WATCHPACK_POLLING=true
ENV CHOKIDAR_USEPOLLING=true

CMD ["npm", "run", "dev", "--", "--webpack", "--hostname", "0.0.0.0"]