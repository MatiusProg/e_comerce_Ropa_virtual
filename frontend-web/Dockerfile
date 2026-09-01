# FashionStore - aplicacion web (Angular)
# Compila la SPA y la sirve con nginx. Es la imagen que despliega Railway.

# --- Etapa 1: compilacion -----------------------------------------------
FROM node:22-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build -- --configuration production

# --- Etapa 2: servidor ---------------------------------------------------
FROM nginx:alpine

# Angular 22 deja la compilacion en dist/<proyecto>/browser
COPY --from=build /app/dist/frontend-web/browser /usr/share/nginx/html
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Railway inyecta $PORT; la plantilla de nginx lo sustituye al arrancar.
ENV PORT=8080
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
