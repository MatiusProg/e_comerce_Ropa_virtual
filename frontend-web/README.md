# Violet Boutique — aplicación web (Angular)

Angular **22** con componentes *standalone*. Una sola aplicación que sirve a
cuatro roles, cada uno con su área y sus guardas de ruta.

## Arranque local

Requisitos: Node 20+ y el backend corriendo en `http://localhost:8000`.

```bash
cd frontend-web
npm install
npm start                 # http://localhost:4200
```

Otros comandos:

```bash
npm run build             # compilación de producción → dist/frontend-web/browser
npm test                  # pruebas unitarias
```

## Áreas de la aplicación

| Carpeta en `src/app/features/` | Rol | Contenido | Ciclo |
|---|---|---|---|
| `auth/` | — | Registro e inicio de sesión | 1 |
| `admin/` | Administrador | Organización, catálogo, inventario, promociones | 1 – 3 |
| `tienda/` | Cliente | Catálogo público, ficha, carrito, pedidos | 2 – 3 |
| `sucursal/` | Encargado | Reservas e inventario de **su** sucursal | 2 |
| `caja/` | Cajero | Punto de venta, cobro, comprobantes | 3 |
| `reportes/` | Administrador | Tablero de KPIs y exportación PDF/Excel | 3 |
| `asistente/` | Cliente / Admin | Chat con IA y comando de voz | 3 |

`core/` guarda lo transversal: el interceptor que adjunta el JWT, las guardas
por rol, los servicios de API y los modelos del contrato. `shared/` guarda lo
reutilizable entre áreas.

## Configuración de la URL de la API

`src/environments/environment.ts` (desarrollo) y `environment.prod.ts`
(producción). El reemplazo en la compilación de producción ya está declarado en
`angular.json` con `fileReplacements`. **Al desplegar en Railway hay que poner
la URL pública del servicio `api` en `environment.prod.ts`** — si queda el
valor de ejemplo, la web compila bien y no funciona nada.

## Comando de voz (CU-35)

Se usa la **Web Speech API** del navegador (`SpeechRecognition`), sin
biblioteca externa ni servicio de transcripción adicional. Solo funciona en
navegadores basados en Chromium y **exige HTTPS** — en Railway se cumple, en
`localhost` también, pero no en una IP de red local por HTTP.

## Despliegue

`Dockerfile` de dos etapas: compila con Node y sirve la SPA con nginx.
`nginx.conf` incluye el `try_files ... /index.html` que necesita el enrutado del
lado del cliente; sin él, recargar la página en `/admin/productos` da 404.
