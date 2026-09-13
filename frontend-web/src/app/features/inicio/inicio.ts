import { Component, computed, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatToolbarModule } from '@angular/material/toolbar';

import { Bienvenida } from '../../shared/bienvenida/bienvenida';
import { AuthService } from '../../core/services/auth.service';

/**
 * Pantalla de inicio de los roles que todavía no tienen área propia:
 * Cliente, Cajero y Proveedor.
 *
 * Ni el Administrador ni el Encargado pasan por acá: sus áreas tienen su
 * propia cáscara con navegación —`AdminLayout` y `SucursalLayout`— y
 * reutilizan la misma tarjeta de bienvenida.
 *
 * El Encargado SÍ pasaba, y ese era el problema: sus tres pantallas estaban
 * terminadas y montadas, pero esta pantalla no tiene navegación, así que no
 * había forma de llegar a ellas sin escribir la URL.
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
