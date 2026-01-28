FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000

RUN npm run build

CMD ["npm", "run", "start", "--", "-p", "3000"]

