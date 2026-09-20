import { Routes } from '@angular/router';

import { rolGuard, sesionGuard } from './core/guards/auth.guard';

/**
 * Mapa de rutas de la aplicación web.
 *
 * Sigue el diagrama de navegación de
 * `docs/entregas/ciclo-1/cap-2-3-analisis-y-diseno.md` §3.2. Las áreas se van
 * llenando a medida que avanzan los casos de uso; en el Ciclo 1 cada una es una
 * pantalla de bienvenida, suficiente para mostrar que la guarda por rol opera.
 *
 * Regla de navegación (§3.2): toda ruta distinta de inicio de sesión y registro
 * exige token vigente. Lo impone `sesionGuard`; el ámbito por rol, `rolGuard`.
 */
const inicio = () => import('./features/inicio/inicio').then((m) => m.Inicio);

export const routes: Routes = [
  // --- Público (sin sesión) ---------------------------------------------
  {
    path: 'login',
    title: 'Iniciar sesión · Violet Boutique',
    loadComponent: () => import('./features/auth/login/login').then((m) => m.Login),
  },
  {
    path: 'registro',
    title: 'Crear cuenta · Violet Boutique',
    loadComponent: () => import('./features/auth/registro/registro').then((m) => m.Registro),
  },

  // CU-41 · Recuperar contraseña. Las dos son públicas por definición: el actor
  // es alguien que justamente no puede iniciar sesión.
  {
    path: 'olvide-contrasena',
    title: 'Recuperar contraseña · Violet Boutique',
    loadComponent: () => import('./features/auth/olvide/olvide').then((m) => m.Olvide),
  },
  {
    // El camino lo arma el backend al mandar el correo:
    // `${WEB_BASE_URL}/recuperar/{token}`. Si cambia acá, cambia allá.
    path: 'recuperar/:token',
    title: 'Contraseña nueva · Violet Boutique',
    loadComponent: () =>
      import('./features/auth/restablecer/restablecer').then((m) => m.Restablecer),
  },

  // --- Ciclo 2 · Karen · La vitrina, también sin sesión ------------------
  // CU-17 y CU-18 son públicos a propósito: el flujo principal no tiene
  // precondición de sesión y el RF07 pide que el cliente consulte el catálogo
  // desde la web y el móvil. Exigir token obligaría a registrarse para mirar
  // una prenda. Lo que se ofrece ya está acotado en el servidor —solo producto
  // activo con variantes activas— y los esquemas públicos no exponen proveedor
  // ni precio base.
  {
    path: 'tienda',
    title: 'Catálogo · Violet Boutique',
    loadComponent: () =>
      import('./features/tienda/catalogo/catalogo').then((m) => m.Catalogo),
  },
  {
    path: 'tienda/producto/:id',
    title: 'Prenda · Violet Boutique',
    loadComponent: () => import('./features/tienda/ficha/ficha').then((m) => m.Ficha),
  },
  {
    // CU-26. Como los favoritos, exige sesión de Cliente: un carrito es de
    // alguien. El código es de P7 aunque la ruta viva bajo /tienda, que es
    // donde el cliente la usa.
    path: 'tienda/carrito',
    title: 'Mi carrito · Violet Boutique',
    canActivate: [sesionGuard, rolGuard('CLIENTE')],
    loadComponent: () =>
      import('./features/tienda/carrito/carrito').then((m) => m.CarritoPantalla),
  },
  {
    // CU-20. A diferencia del resto de la tienda, ésta **sí** exige sesión de
    // Cliente: un favorito es de alguien, y sin sesión no hay de quién.
    path: 'tienda/favoritos',
    title: 'Mis favoritos · Violet Boutique',
    canActivate: [sesionGuard, rolGuard('CLIENTE')],
    loadComponent: () =>
      import('./features/tienda/favoritos/favoritos').then((m) => m.Favoritos),
  },

  // --- Ciclo 3 · CU-33 Recibir recomendaciones de prendas (RF25) ---------
  {
    path: 'tienda/para-vos',
    title: 'Para vos · Violet Boutique',
    canActivate: [sesionGuard, rolGuard('CLIENTE')],
    loadComponent: () => import('./features/tienda/para-vos/para-vos').then((m) => m.ParaVos),
  },

  // --- Ciclo 3 · CU-29 Consultar historial de compras --------------------
  // Vive bajo /mi-cuenta y no bajo /tienda: la tienda es donde se compra, y
  // esto es lo que quedó de haber comprado. Es la misma distinción que hay
  // entre «pedidos» y «compras» en la API.
  {
    path: 'mi-cuenta/compras',
    title: 'Mis compras · Violet Boutique',
    canActivate: [sesionGuard, rolGuard('CLIENTE')],
    loadComponent: () =>
      import('./features/cliente/compras/compras').then((m) => m.Compras),
  },

  // --- Ciclo 3 · CU-27 Realizar pedido y pagar en línea ------------------
  {
    path: 'tienda/checkout',
    title: 'Confirmar el pedido · Violet Boutique',
    canActivate: [sesionGuard, rolGuard('CLIENTE')],
    loadComponent: () =>
      import('./features/tienda/checkout/checkout').then((m) => m.Checkout),
  },
  // Las dos salidas de la pasarela. Los caminos NO son libres: los fija el
  // backend con `PAGO_URL_EXITO` y `PAGO_URL_CANCELADO`, que por omisión
  // apuntan acá. Cambiar uno sin cambiar el otro deja al cliente en un 404
  // justo después de pagar.
  //
  // `data.salida` llega al componente como entrada gracias a
  // `withComponentInputBinding()` (ver app.config.ts): es la misma pantalla
  // con dos encabezados, porque las dos hacen lo mismo —preguntarle a la base
  // en qué estado quedó el pedido—.
  {
    path: 'pago/exito',
    title: 'Resultado del pago · Violet Boutique',
    canActivate: [sesionGuard, rolGuard('CLIENTE')],
    data: { salida: 'exito' },
    loadComponent: () =>
      import('./features/tienda/pago/pago-retorno').then((m) => m.PagoRetorno),
  },
  {
    path: 'pago/cancelado',
    title: 'Pago cancelado · Violet Boutique',
    canActivate: [sesionGuard, rolGuard('CLIENTE')],
    data: { salida: 'cancelado' },
    loadComponent: () =>
      import('./features/tienda/pago/pago-retorno').then((m) => m.PagoRetorno),
  },

  // --- Con sesión, una por rol ------------------------------------------
  {
    path: 'admin',
    canActivate: [sesionGuard, rolGuard('ADMINISTRADOR')],
    loadComponent: () =>
      import('./features/admin/admin-layout/admin-layout').then((m) => m.AdminLayout),
    children: [
      {
        path: '',
        pathMatch: 'full',
        title: 'Administración · Violet Boutique',
        loadComponent: () =>
          import('./shared/bienvenida/bienvenida').then((m) => m.Bienvenida),
      },
      {
        path: 'usuarios',
        title: 'Usuarios · Violet Boutique',
        loadComponent: () =>
          import('./features/admin/usuarios/usuarios').then((m) => m.Usuarios),
      },
      {
        path: 'sucursales',
        title: 'Sucursales · Violet Boutique',
        loadComponent: () =>
          import('./features/admin/sucursales/sucursales').then((m) => m.Sucursales),
      },
      {
        path: 'ciudades',
        title: 'Ciudades · Violet Boutique',
        loadComponent: () =>
          import('./features/admin/ciudades/ciudades').then((m) => m.Ciudades),
      },
      {
        path: 'empleados',
        title: 'Empleados · Violet Boutique',
        loadComponent: () =>
          import('./features/admin/empleados/empleados').then((m) => m.Empleados),
      },
      {
        path: 'proveedores',
        title: 'Proveedores · Violet Boutique',
        loadComponent: () =>
          import('./features/admin/proveedores/proveedores').then((m) => m.Proveedores),
      },
      {
        path: 'maestros',
        title: 'Maestros del catálogo · Violet Boutique',
        loadComponent: () =>
          import('./features/admin/maestros/maestros').then((m) => m.Maestros),
      },
      {
        path: 'temporadas',
        title: 'Temporadas · Violet Boutique',
        loadComponent: () =>
          import('./features/admin/temporadas/temporadas').then((m) => m.Temporadas),
      },
      {
        path: 'promociones',
        title: 'Promociones · Violet Boutique',
        loadComponent: () =>
          import('./features/admin/promociones/promociones').then((m) => m.Promociones),
      },
      // --- Ciclo 2 · Karen -------------------------------------------------
      // Se agrega al final del bloque y sin reordenar lo anterior, que es el
      // protocolo de archivos compartidos del ciclo (§5 del acuerdo).
      {
        path: 'productos',
        title: 'Productos · Violet Boutique',
        loadComponent: () =>
          import('./features/admin/productos/productos').then((m) => m.Productos),
      },
      {
        // CU-14. Ruta aparte de `inventario`, que es de CU-13 y CU-15: aquélla
        // sirve para operar sobre una tienda y ésta para mirar la red entera.
        path: 'consolidado',
        title: 'Inventario consolidado · Violet Boutique',
        loadComponent: () =>
          import('./features/admin/consolidado/consolidado').then((m) => m.Consolidado),
      },
      // --- Ciclo 2 · P4 Inventario (CU-13, CU-15) ---
      {
        path: 'inventario',
        title: 'Inventario · Violet Boutique',
        loadComponent: () =>
          import('./features/admin/inventario/inventario').then((m) => m.Inventario),
      },
      // --- Ciclo 2 · P6 Reservas (CU-24, CU-25) ---
      // Misma pantalla que la del Encargado: el alcance lo decide el servidor
      // con el ambito del token, y el disparador de la expiracion (CU-25) solo
      // aparece para el Administrador.
      {
        path: 'reservas',
        title: 'Reservas · Violet Boutique',
        loadComponent: () =>
          import('./features/sucursal/reservas/reservas-sucursal').then(
            (m) => m.ReservasSucursal,
          ),
      },
      // --- Ciclo 3 · P11 Reportes y Tablero (CU-36) ---
      // Dentro de 'admin' y no en una cáscara propia: el tablero es del
      // Administrador y la guarda del padre ya resuelve el rol. La exportación
      // (CU-37) cuelga de acá cuando exista.
      {
        path: 'tablero',
        title: 'Tablero de indicadores · Violet Boutique',
        // Chart.js se provee dentro del propio componente, no acá: este
        // archivo viaja en el bundle inicial, así que importar `ng2-charts`
        // para ponerlo en `providers` metería la librería en el arranque de
        // todas las pantallas —medido: 678 kB a 890 kB—. Ver la nota de
        // `tablero.ts`.
        loadComponent: () =>
          import('./features/reportes/tablero/tablero').then((m) => m.Tablero),
      },
      // CU-37 · la exportacion, que el comentario de arriba ya preveia.
      {
        path: 'reportes',
        title: 'Reportes de gestión · Violet Boutique',
        loadComponent: () =>
          import('./features/reportes/exportar/exportar').then((m) => m.Exportar),
      },
    ],
  },
  // --- Ciclo 2 · P6 Reservas del Cliente (CU-22, CU-23) ---
  //
  // ANTES de 'mi-cuenta' a proposito: esa ruta no declara hijos, asi que si
  // quedara primero consumiria el prefijo y esta no se resolveria nunca. Mismo
  // caso que 'sucursal/...' mas abajo.
  {
    path: 'mi-cuenta/reservas',
    title: 'Mis reservas · Violet Boutique',
    canActivate: [sesionGuard, rolGuard('CLIENTE')],
    loadComponent: () =>
      import('./features/cliente/reservas/reservas').then((m) => m.Reservas),
  },
  {
    path: 'mi-cuenta',
    title: 'Mi perfil · Violet Boutique',
    canActivate: [sesionGuard, rolGuard('CLIENTE')],
    loadComponent: () =>
      import('./features/cliente/perfil/perfil').then((m) => m.Perfil),
  },
  // --- Ciclo 2 · P4 para el Encargado (CU-13 y CU-16) ---
  //
  // Van ANTES de 'sucursal' a propósito: esa ruta no declara hijos, así que si
  // quedara primero consumiría el prefijo y estas no se resolverían nunca.
  //
  // `disponibilidad` es CU-16 y tiene pantalla propia: está organizada
  // alrededor del saldo de un local —alertas arriba, listado abajo—, mientras
  // que la del Administrador lo está alrededor del movimiento. Comparten los
  // diálogos y el servicio, que es donde vive lo que de verdad se repite.
  //
  // `inventario` reusa la pantalla del Administrador para que el Encargado
  // registre sus ingresos (CU-13) y lea su historial. El alcance no lo decide
  // la ruta sino el servidor: el ámbito viaja en el token.
  // CU-24: el panel de reservas del local. El Administrador entra por
  // /admin/reservas con alcance a toda la red.
  // El area del Encargado cuelga de su propia cascara, igual que la del
  // Administrador. ANTES LAS TRES RUTAS ERAN HERMANAS Y `sucursal` caia en la
  // pantalla generica de bienvenida: las pantallas funcionaban pero no habia
  // como llegar a ellas salvo escribiendo la URL. Ver `SucursalLayout`.
  //
  // El guard va en el padre y lo heredan las hijas; repetirlo en cada una
  // seria pedirle lo mismo cuatro veces al mismo token.
  {
    path: 'sucursal',
    canActivate: [sesionGuard, rolGuard('ENCARGADO')],
    loadComponent: () =>
      import('./features/sucursal/sucursal-layout/sucursal-layout').then(
        (m) => m.SucursalLayout,
      ),
    children: [
      {
        path: '',
        title: 'Sucursal · Violet Boutique',
        loadComponent: () =>
          import('./shared/bienvenida/bienvenida').then((m) => m.Bienvenida),
      },
      {
        path: 'reservas',
        title: 'Reservas de la sucursal · Violet Boutique',
        loadComponent: () =>
          import('./features/sucursal/reservas/reservas-sucursal').then(
            (m) => m.ReservasSucursal,
          ),
      },
      {
        path: 'disponibilidad',
        title: 'Disponibilidad · Violet Boutique',
        loadComponent: () =>
          import('./features/sucursal/disponibilidad/disponibilidad').then(
            (m) => m.Disponibilidad,
          ),
      },
      {
        // Reusa la pantalla del Administrador: el alcance no lo decide la ruta
        // sino el ambito que viaja en el token.
        path: 'inventario',
        title: 'Inventario de la sucursal · Violet Boutique',
        loadComponent: () =>
          import('./features/admin/inventario/inventario').then((m) => m.Inventario),
      },
    ],
  },
  // --- Ciclo 3 · CU-30 · El area de Caja --------------------------------
  //
  // Cuelga de su propia cascara, igual que las del Administrador, el Encargado
  // y el Proveedor. ERA UNA RUTA SUELTA que caia en la pantalla generica de
  // bienvenida desde el Ciclo 1: el Cajero entraba y no habia nada.
  //
  // Es la CUARTA vez que aparece el mismo hueco ---y la ultima que faltaba---.
  // La leccion ya costo tres: una pantalla montada no esta entregada si no hay
  // como llegar a ella.
  {
    path: 'caja',
    canActivate: [sesionGuard, rolGuard('CAJERO')],
    loadComponent: () =>
      import('./features/caja/caja-layout/caja-layout').then((m) => m.CajaLayout),
    children: [
      {
        path: '',
        pathMatch: 'full',
        title: 'Mi turno · Violet Boutique',
        loadComponent: () => import('./features/caja/turno/turno').then((m) => m.Turno),
      },
      {
        path: 'vender',
        title: 'Vender · Violet Boutique',
        loadComponent: () => import('./features/caja/venta/venta').then((m) => m.Venta),
      },
      {
        path: 'devoluciones',
        title: 'Devoluciones · Violet Boutique',
        loadComponent: () =>
          import('./features/caja/devolucion/devolucion').then((m) => m.Devolucion),
      },
    ],
  },
  // --- Ciclo 3 · CU-38 · El area del Proveedor --------------------------
  //
  // Cuelga de su propia cascara, igual que las del Administrador y el
  // Encargado. ANTES ERA UNA RUTA SUELTA que caia en la pantalla generica de
  // bienvenida: el Proveedor entraba y no habia nada, porque era un actor
  // principal que no iniciaba ningun caso de uso. Es la misma leccion que dejo
  // CU-16 al cierre del Ciclo 2 --- una pantalla montada no esta entregada si
  // no hay como llegar a ella ---, aplicada antes de que vuelva a pasar.
  //
  // El guard va en el padre y lo heredan las hijas.
  {
    path: 'proveedor',
    canActivate: [sesionGuard, rolGuard('PROVEEDOR')],
    loadComponent: () =>
      import('./features/proveedor/proveedor-layout/proveedor-layout').then(
        (m) => m.ProveedorLayout,
      ),
    children: [
      {
        path: '',
        title: 'Proveedor · Violet Boutique',
        loadComponent: () =>
          import('./shared/bienvenida/bienvenida').then((m) => m.Bienvenida),
      },
      {
        path: 'productos',
        title: 'Mis productos · Violet Boutique',
        loadComponent: () =>
          import('./features/proveedor/mis-productos/mis-productos').then(
            (m) => m.MisProductos,
          ),
      },
      // CU-39 · informar disponibilidad y plazo (RF38).
      {
        path: 'abastecimiento',
        title: 'Qué puedo abastecer · Violet Boutique',
        loadComponent: () =>
          import('./features/proveedor/abastecimiento/abastecimiento').then(
            (m) => m.Abastecimiento,
          ),
      },
    ],
  },

  { path: '', pathMatch: 'full', redirectTo: 'login' },
  { path: '**', redirectTo: 'login' },
];
