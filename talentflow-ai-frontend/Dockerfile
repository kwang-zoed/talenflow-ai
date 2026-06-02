# 默认 DaoCloud，避免国内直连 auth.docker.io；海外构建可传 --build-arg 覆盖
ARG NODE_BASE=docker.m.daocloud.io/library/node:18-alpine
ARG NGINX_BASE=docker.m.daocloud.io/library/nginx:stable-alpine

FROM ${NODE_BASE} AS build-stage

WORKDIR /app
COPY package*.json ./
RUN npm config set registry https://registry.npmmirror.com \
    && npm install

COPY . .
RUN npm run build

FROM ${NGINX_BASE} AS production-stage

RUN rm /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d

COPY --from=build-stage /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
