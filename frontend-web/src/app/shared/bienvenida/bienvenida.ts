import { Component, computed, inject } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';

import { AuthService } from '../../core/services/auth.service';
import type { Rol } from '../../core/models/auth.models';

/** Qué ve cada rol al entrar, según el diagrama de navegación §3.2. */
const AREA: Record<Rol, { titulo: string; detalle: string; icono: string }> = {
  ADMINISTRADOR: {
    titulo: 'Panel de administración',
    detalle:
      'Desde acá se gestionan los usuarios, la organización —ciudades, sucursales, empleados y proveedores— y los maestros del catálogo.',
    icono: 'admin_panel_settings',
  },
  CLIENTE: {
    titulo: 'Mi cuenta',
    detalle:
      'Acá vas a ver tu perfil, tus tallas habituales, tus direcciones y —desde el Ciclo 2— tus reservas y tus compras.',
    icono: 'person',
  },
  ENCARGADO: {
    titulo: 'Panel de sucursal',
    detalle:
      'Desde la barra de arriba se atienden las reservas del local, se controla la disponibilidad de las prendas y se registran los ingresos e inventario de la sucursal. Todo acotado a tu tienda.',
    icono: 'storefront',
  },
  CAJERO: {
    titulo: 'Punto de venta',
    detalle:
      'Acá se abre y cierra la caja y se registran las ventas presenciales. Sus funciones propias llegan con el Ciclo 3.',
    icono: 'point_of_sale',
  },
  PROVEEDOR: {
    titulo: 'Portal del proveedor',
    detalle:
      'Desde la barra de arriba se registran las prendas que abastecés y las tallas y colores en que las traés. Lo que registres queda a la espera de que la tienda lo publique en su catálogo.',
    icono: 'local_shipping',
  },
};

/**
 * Tarjeta de bienvenida por rol, sin barra superior.
 *
 * Se usa suelta dentro de las áreas que ya traen su propia barra —la de
 * administración, la de sucursal y, desde CU-38, la del proveedor— y envuelta
 * por `Inicio` para los roles que todavía no tienen área propia: Cliente y
 * Cajero. Existe separada justamente para no duplicar el texto de cada rol en
 * dos lugares.
 */
@Component({
  selector: 'app-bienvenida',
  imports: [MatCardModule, MatIconModule],
  templateUrl: './bienvenida.html',
  styleUrl: './bienvenida.scss',
})
export class Bienvenida {
  private readonly auth = inject(AuthService);

  protected readonly usuario = this.auth.usuario;

  protected readonly area = computed(() => {
    const rol = this.usuario()?.rol;
    return rol ? AREA[rol] : null;
  });
}
