import { Component, computed, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatToolbarModule } from '@angular/material/toolbar';

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
      'Acá se atienden las reservas y se controla el inventario de la sucursal. Sus funciones propias llegan con el Ciclo 2.',
    icono: 'storefront',
  },
  CAJERO: {
    titulo: 'Punto de venta',
    detalle:
      'Acá se abre y cierra la caja y se registran las ventas presenciales. Sus funciones propias llegan con el Ciclo 3.',
    icono: 'point_of_sale',
  },
};

/**
 * Pantalla de bienvenida por rol.
 *
 * En el Ciclo 1 su valor es mostrar que la guarda por rol ya opera: cada quien
 * cae en su área y no puede entrar a la de otro. El contenido real de cada área
 * llega con los casos de uso de CU-03 en adelante.
 */
@Component({
  selector: 'app-inicio',
  imports: [MatButtonModule, MatCardModule, MatIconModule, MatToolbarModule],
  templateUrl: './inicio.html',
  styleUrl: './inicio.scss',
})
export class Inicio {
  private readonly auth = inject(AuthService);

  protected readonly usuario = this.auth.usuario;

  protected readonly area = computed(() => {
    const rol = this.usuario()?.rol;
    return rol ? AREA[rol] : null;
  });

  protected readonly iniciales = computed(() => {
    const u = this.usuario();
    if (!u) return '';
    return `${u.nombres.charAt(0)}${u.apellidos.charAt(0)}`.toUpperCase();
  });

  protected salir(): void {
    this.auth.cerrarSesion();
  }
}
