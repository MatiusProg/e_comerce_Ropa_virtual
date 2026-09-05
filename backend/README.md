# Violet Boutique — API REST (FastAPI)

Backend de la plataforma. Sirve al mismo tiempo a la aplicación web (Angular) y
a la aplicación móvil (Flutter): **un solo contrato, ninguna regla de negocio
duplicada en el cliente** (RNF07, RNF08).

## Arranque local

Requisitos: **Python 3.13** y Docker (solo para la base de datos).

```bash
# 1. La base de datos
docker compose up -d                     # desde la raíz del repositorio

# 2. El entorno virtual
cd backend
py -3.13 -m venv .venv                   # Windows
python3.13 -m venv .venv                 # macOS / Linux
.venv\Scripts\activate                   # Windows
source .venv/bin/activate                # macOS / Linux

pip install -r requirements.txt

# 3. La configuración
cp .env.example .env                     # y completar los valores

# 4. El esquema y los datos de prueba
alembic upgrade head
python -m app.db.seed

# 5. A correr
uvicorn app.main:app --reload
```

Verificación:

```bash
curl http://localhost:8000/health        # debe responder {"status":"ok",...}
```

Documentación interactiva de la API: <http://localhost:8000/docs>

## Organización del código

`app/modules/` contiene **un subpaquete por cada paquete de análisis** de
[`docs/04-analisis-arquitectura.md`](../docs/04-analisis-arquitectura.md), con
el mismo nombre. El diagrama de paquetes del documento y el árbol de carpetas
son la misma cosa; no hay que traducir entre uno y otro en la defensa.

```
app/
├── main.py               Monta un router por paquete. Los ciclos 2 y 3 están
│                         comentados: se descomentan al implementarlos.
├── core/
│   ├── config.py         Toda la configuración, por variables de entorno
│   ├── security.py       Hash bcrypt y emisión/validación de JWT
│   └── dependencies.py   Sesión de BD, usuario actual, exigencia de rol
├── db/
│   ├── base.py           Base declarativa + convención de nombres
│   ├── session.py        Motor y sesión (una por petición)
│   └── seed.py           Datos de prueba
├── modules/
│   ├── seguridad/          P1  · CU-01 a CU-04            · ciclo 1
│   ├── organizacion/       P2  · CU-05 a CU-07            · ciclo 1
│   ├── catalogo/           P3  · CU-08 a CU-12            · ciclos 1-3
│   ├── inventario/         P4  · CU-13 a CU-16            · ciclo 2
│   ├── catalogo_publico/   P5  · CU-17 a CU-20            · ciclos 2-3
│   ├── reservas/           P6  · CU-22 a CU-25            · ciclo 2
│   ├── ventas/             P7  · CU-26, 27, 29 a 32       · ciclo 3
│   ├── pagos/              P8  · CU-27, CU-28             · ciclo 3
│   ├── vestidor_virtual/   P9  · CU-21                    · ciclo 3
│   ├── ia/                 P10 · CU-33 a CU-35            · ciclo 3
│   └── reportes/           P11 · CU-36, CU-37             · ciclo 3
└── integrations/         Adaptadores de Stripe y de la API de IA
```

### Las cuatro capas — la regla que no se rompe

Dentro de cada módulo:

```
router.py       HTTP: valida la entrada, resuelve la autorización, delega
    ↓
service.py      Reglas de negocio y control de la transacción
    ↓
repository.py   Consultas. Nada más.
    ↓
models.py       SQLAlchemy
```

Ningún `router` toca `models` directamente, y ninguna regla de negocio vive en
un `router`. Esto no es formalismo: es lo que hace que los **diagramas de
secuencia** del flujo de Diseño se correspondan literalmente con el código, y
lo que permite que dos personas trabajen en paralelo sin pisarse.

## Migraciones (Alembic)

```bash
alembic revision --autogenerate -m "crear tablas de seguridad"
alembic upgrade head
alembic downgrade -1                     # deshacer la última
alembic history                          # ver el historial
```

> **La trampa más común:** si el modelo nuevo no está importado en
> `alembic/env.py`, Alembic no lo ve y genera una migración **vacía** sin
> avisar. Al agregar un módulo con tablas, descomentar su import ahí.

## Pruebas

```bash
pytest                                   # todas
pytest tests/test_health.py -v           # una
pytest --cov=app                         # con cobertura
```

## Reglas de negocio que no se negocian

Estas cuatro salen del análisis y sostienen la integridad del sistema. Están
justificadas en [`docs/04-analisis-arquitectura.md`](../docs/04-analisis-arquitectura.md) §4.2.1.

**1. La variante (SKU), no el producto, es la unidad de negocio.**
`Producto` describe la prenda; `VarianteProducto` es la combinación talla ×
color, y es la que tiene precio, existencia, reserva y venta. Inventario,
reservas y ventas referencian **variante**, nunca producto.

**2. Ninguna cantidad cambia sin generar un `MovimientoInventario`.**
Los movimientos son inmutables: una corrección es un movimiento nuevo de tipo
ajuste, jamás una edición. `Existencia` es el saldo de sus movimientos.

**3. La reserva no descuenta stock: lo traslada.**
`Existencia` lleva `cantidad_disponible` y `cantidad_reservada`. Reservar mueve
de disponible a reservado; vender descuenta de reservado (si vino de una
reserva) o de disponible; expirar devuelve a disponible. Toda la operación va
en **una transacción con `SELECT ... FOR UPDATE`** sobre la fila de existencia —
sin eso, dos clientes compran la misma última unidad.

**4. El estado del pago lo determina el webhook, nunca el navegador.**
La redirección de vuelta desde la pasarela solo sirve para mostrarle algo al
usuario. El pedido pasa a pagado al recibir el webhook **con la firma
verificada**, y ese procesamiento es **idempotente**: si la pasarela reenvía la
notificación, el inventario no se descuenta dos veces.
