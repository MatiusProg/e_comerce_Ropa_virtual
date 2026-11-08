# Organizaciones de demostración (multitenant)

Además de **Violet Boutique**, la plataforma tiene cuatro boutiques de
demostración. Sirven para mostrar en la defensa que cada empresa tiene su plan,
sus sucursales, su catálogo, su personal y sus clientes, y que no ve nada de las
demás. Las carga `backend/scripts/organizaciones_demo.py`.

## Cómo entrar

| Campo | Valor |
|---|---|
| Empresa (slug) | el de la tabla de abajo, por ejemplo `alpaca` |
| Correo | rol + número + `@<slug>.test`, por ejemplo `cajero2@alpaca.test` |
| Contraseña | `si2ex22026` (la de todas las cuentas) |

## Organizaciones

| Slug | Empresa | Plan | Sucursales | Para mostrar |
|---|---|---|---|---|
| `alpaca` | Alpaca Real (tejidos de alpaca) | Empresarial | La Paz, Cochabamba, Santa Cruz | todo, con analítica ML e IA |
| `chiquitana` | Chiquitana Moda (ropa tropical) | Empresarial | Santa Cruz, Cochabamba, La Paz | todo, con analítica ML e IA |
| `illimani` | Illimani Urbano (urbana y outdoor) | Profesional | La Paz, Santa Cruz, Cochabamba | IA sí, analítica ML **no** (403) |
| `awayu` | Awayu Boutique (textiles andinos) | Básico | Cochabamba, La Paz | **sin** IA ni analítica, máx. 2 sucursales |

Las sucursales salen de las ciudades que existen en la base y nunca pasan el
`max_sucursales` ni el `max_empleados` del plan.

## Cuentas por empresa

| Rol | Correos | alpaca | chiquitana | illimani | awayu |
|---|---|---|---|---|---|
| Administrador | `admin@<slug>.test` | 1 | 1 | 1 | 1 |
| Encargado (uno por sucursal) | `encargado1@…` a `encargadoN@…` | 3 | 3 | 3 | 2 |
| Cajero | `cajero1@…` a `cajeroN@…` | 6 (2 por sucursal) | 6 | 3 (1 por sucursal) | 2 |
| Proveedor | `proveedor1@<slug>.test` | 1 | 1 | 1 | 1 |
| Cliente | `cliente1@…` a `cliente20@<slug>.test` | 20 | 20 | 20 | 20 |

Los cajeros van en orden de sucursal: con 2 por sucursal, `cajero1` y `cajero2`
son de la primera, `cajero3` y `cajero4` de la segunda, y así.

## Qué tiene cada una

- Suscripción vigente (30 días desde la carga) con su pago simulado de alta.
- Cajas (2 por sucursal en las Empresariales, 1 en las demás).
- Catálogo propio: 16 a 22 productos con variantes de talla y color, categorías,
  colores, una temporada y una colección propias, y un proveedor con cuenta.
  Los productos no tienen foto (se ve el marcador de la tienda).
- Existencias en todas las sucursales, con su historial de movimientos
  (ingreso, ventas, devoluciones, reservas); algunas quedan en stock bajo.
- Turnos de caja cerrados con ventas: 54 en cada Empresarial (6 semanas, alcanza
  para la analítica y las anomalías), 18 en `illimani` y 12 en `awayu` (3 semanas).
- Devoluciones: 18 en cada Empresarial, 6 y 5 en las otras.
- Reservas por sucursal: 2 pendientes (mañana y pasado), 2 atendidas con su venta,
  1 cancelada y 1 expirada.

## Ejemplos para la defensa

1. **El mismo correo de cliente en dos tiendas (RN-13):** `cliente1@alpaca.test`
   entra con el slug `alpaca` y también con `violet-boutique`: es una sola
   cuenta de la plataforma, y la segunda tienda empieza a verlo recién al entrar.
2. **El personal no cruza de empresa:** `admin@awayu.test` con el slug `alpaca`
   responde «correo o contraseña incorrectos».
3. **Aislamiento:** el administrador de `alpaca` ve solo los productos `ALP-..`, y
   el de `awayu` solo los `AWY-..`.
4. **Límites del plan:** en `awayu` (Básico) Analítica responde «El plan Básico no
   incluye la analítica con ML», y no deja crear una tercera sucursal. En `illimani`
   (Profesional) la IA anda pero la analítica no.
5. **Analítica:** en `alpaca` o `chiquitana`, Analítica → Entrenar y Anomalías →
   Buscar. Hay un turno con un faltante de Bs 180 que aparece marcado.

## Tips

- Las cuentas `.test` necesitan el backend con el arreglo de este PR
  (`email-validator` rechazaba el dominio `.test` y el login respondía 422).
- Los inicios de sesión quedan en la bitácora; `--borrar` también los quita.
- Si se cambia la clave con `DEMO_ORGANIZACIONES_CLAVE` al cargar, esa es la de
  todas las cuentas.

## Cargar y borrar (desde `backend/`, en PowerShell)

```powershell
$env:APP_DB_ROLE = "violet_app"
python -m scripts.organizaciones_demo --dry-run   # simulacro: no guarda nada
python -m scripts.organizaciones_demo             # pide escribir CARGAR
python -m scripts.organizaciones_demo --borrar    # pide escribir BORRAR
python -m scripts.organizaciones_demo --empresa awayu   # solo una
```

El script se niega a correr si alguna de las cuatro ya existe, exige
`APP_DB_ROLE` y hace todo en una sola transacción. `--borrar` quita las empresas
enteras (todo lo que tenga su `empresa_id`, incluso lo hecho después en la
defensa), su personal, las cuentas de sus clientes y sus logins en la bitácora;
solo toca una empresa si tiene la cuenta `admin@<slug>.test`, la marca de que la
creó el script.
