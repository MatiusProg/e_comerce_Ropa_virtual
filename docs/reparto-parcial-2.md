# Reparto de casos de uso — 2do parcial

*23/10/2026. Es una guía para no pisarnos, no una frontera: si uno se atrasa, el otro hace lo que falte.*

**Cómo se reparte.** Como en el 1er parcial, quien toma un caso de uso lo hace **completo**: la migración, el
backend, la web, el móvil y sus diagramas (robustez con sus mensajes, secuencia, diseño de clases y la prueba).
Cada uno se lleva bloques que dependen entre sí, para no esperar al otro. Lo que toca el probador o el
teléfono de pruebas lo hace Luis, que tiene el celular.

Los números son los del Word (`SI2 Ex2 Grupo 15.docx`, sección 2.5).

## Presentación 1 — dom 25/10 (CU-01 a CU-12)

| Luis: el núcleo multitenant | Karen: la empresa por dentro |
|---|---|
| CU-01 Gestionar empresas | CU-04 Consultar plan y consumo |
| CU-02 Gestionar planes | CU-07 Registrar cliente con cuenta única |
| CU-03 Gestionar suscripciones | CU-08 Gestionar usuarios de la empresa |
| CU-05 Verificar límites y funciones del plan | CU-09 Gestionar sucursales de la empresa |
| CU-06 Iniciar sesión en una empresa | CU-10 Gestionar empleados de la empresa |
| CU-11 Contratar un plan desde la web | CU-12 Personalizar la tienda de la empresa |

**Primero va el CU-05 y el CU-06** (la empresa en el token y el control del plan), porque los de Karen los usan.
Mientras tanto, Karen puede adelantar las pantallas y los diagramas.

## Presentación 2 — dom 01/11 (CU-13 a CU-26)

| Luis: offline y sincronización | Karen: caja, inventario y devoluciones |
|---|---|
| CU-13 Preparar el dispositivo para trabajar offline | CU-20 Abrir y cerrar caja con ventas offline |
| CU-14 Registrar venta offline | CU-21 Gestionar el inventario de la sucursal |
| CU-15 Registrar reserva offline | CU-22 Registrar cambio o devolución en caja |
| CU-16 Registrar pago sin conexión | CU-23 Configurar la ventana de devolución |
| CU-17 Sincronizar operaciones pendientes | CU-24 Solicitar cambio o devolución por la web |
| CU-18 Consultar operaciones pendientes | CU-25 Atender solicitud de devolución |
| CU-19 Atender operaciones rechazadas y devolver el dinero | CU-26 Notificar eventos por correo según el plan |

El contrato de sincronización (CU-17) es la pieza común: el CU-20 y el CU-21 lo usan para lo que se hizo sin
conexión.

## Presentación 3 — dom 08/11 (CU-27 a CU-39)

| Luis: IA, analítica y probador | Karen: ofertas, traspasos y datos |
|---|---|
| CU-27 Generar reporte con IA por texto o voz | CU-28 Generar reportes de gestión con devoluciones |
| CU-29 Entrenar los modelos de analítica | CU-31 Gestionar ofertas y precios mayoristas |
| CU-30 Consultar el dashboard analítico | CU-32 Aplicar ofertas de fuera de temporada |
| CU-36 Preparar prenda para el probador | CU-33 Solicitar traspaso entre sucursales |
| CU-37 Probarse una prenda con su talla real | CU-34 Atender traspaso |
| CU-38 Generar foto realista de la prueba | CU-35 Consultar traspasos sugeridos |
| | CU-39 Exportar los datos de la empresa |

## Total

| | P1 | P2 | P3 | Total |
|---|---|---|---|---|
| Luis | 6 | 7 | 6 | 19 |
| Karen | 6 | 7 | 7 | 20 |

**Lo que no es de un caso de uso** (capítulos I y II, arquitectura, despliegue, base de datos, el Word) lo
hacemos entre los dos según quién tenga tiempo.

## Diagramas de la presentación 1

Los 12 diagramas de robustez ya están en EA (`PARCIAL 2 - ICONIX > 3.2 Diagramas de Robustez`), solo con los
enlaces. Cada uno carga los **mensajes** de sus casos de uso siguiendo
`docs/diagramas/2do Parcial/3.2-robustez-mensajes.md`. El `.eapx` no se fusiona: **avisar en el grupo antes de
abrirlo y subirlo apenas se termina**.
