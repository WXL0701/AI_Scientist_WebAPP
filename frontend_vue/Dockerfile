FROM node:22-alpine as build
WORKDIR /app
ARG VITE_APP_BUILD_ID
ENV VITE_APP_BUILD_ID=${VITE_APP_BUILD_ID}
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:stable-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
