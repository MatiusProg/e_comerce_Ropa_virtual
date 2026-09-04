import { Component, computed, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatToolbarModule } from '@angular/material/toolbar';

import { Bienvenida } from '../../shared/bienvenida/bienvenida';
import { AuthService } from '../../core/services/auth.service';

/**
 * Pantalla de inicio de los roles que todavía no tienen área propia:
 * Cliente, Encargado de Sucursal y Cajero.
 *
 * El Administrador no pasa por acá: su área tiene su propia cáscara con
 * navegación (`AdminLayout`), y reutiliza la misma tarjeta de bienvenida.
 */
@Component({
  selector: 'app-inicio',
  imports: [Bienvenida, MatButtonModule, MatIconModule, MatToolbarModule],
  templateUrl: './inicio.html',
  styleUrl: './inicio.scss',
})
export class Inicio {
  private readonly auth = inject(AuthService);

  protected readonly usuario = this.auth.usuario;

  protected readonly iniciales = computed(() => {
    const u = this.usuario();
    if (!u) return '';
    return `${u.nombres.charAt(0)}${u.apellidos.charAt(0)}`.toUpperCase();
  });

  protected salir(): void {
    this.auth.cerrarSesion();
  }
}
