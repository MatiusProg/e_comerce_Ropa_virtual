import { Component, computed, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { MatBadgeModule } from '@angular/material/badge';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

import { AuthService } from '../../core/services/auth.service';
import { CarritoService } from '../../core/services/carrito.service';

/**
 * La barra de navegación del Cliente, compartida por todas sus pantallas.
 *
 * POR QUÉ ES UN COMPONENTE Y NO UN LAYOUT
 * ----------------------------------------
 * Admin, Proveedor y Encargado resuelven su navegación con un `*-layout` que
 * envuelve sus rutas hijas. **Para el Cliente eso no sirve**: la mitad de sus
 * pantallas —el catálogo y la ficha— son **públicas**, y envolverlas en un
 * layout con sesión rompería la vitrina para quien todavía no tiene cuenta,
 * que es justamente a quien se le quiere mostrar el catálogo.
 *
 * Por eso la barra viaja como componente y se la incluye en cada pantalla. En
 * las públicas **no se dibuja sola**: sólo aparece cuando quien mira es un
 * Cliente con sesión. Un visitante anónimo ve la vitrina como siempre.
 *
 * LA BURBUJA SALE DE LA SEÑAL COMPARTIDA DEL SERVICIO
 * ----------------------------------------------------
 * No de un contador propio. Es lo que hace que el número de acá, el de la
 * pantalla del carrito y el de cualquier otra pantalla digan **siempre lo
 * mismo**: con contadores separados se desincronizarían en cuanto el cliente
 * agregara algo desde una ficha.
 */
@Component({
  selector: 'app-navegacion-cliente',
  imports: [
    RouterLink,
    RouterLinkActive,
    MatBadgeModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
  ],
  templateUrl: './navegacion-cliente.html',
  styleUrl: './navegacion-cliente.scss',
})
export class NavegacionCliente {
  private readonly auth = inject(AuthService);
  private readonly carrito = inject(CarritoService);

  /** Sólo el Cliente la ve. El resto de los roles tiene su propio layout. */
  protected readonly visible = computed(() => this.auth.rol() === 'CLIENTE');

  protected readonly itemsEnCarrito = this.carrito.items;

  /**
   * Cerrar sesión vive ACÁ y no en cada pantalla.
   *
   * Hasta el 19/09 el botón estaba en el encabezado propio de «Mi perfil»,
   * «Mis reservas» e «Inicio», y en ninguna otra. O sea que **aparecía y
   * desaparecía al cambiar de pestaña**: desde el catálogo, el carrito o los
   * favoritos no había forma de salir sin volver antes a una de las tres.
   *
   * La barra es lo único que está en todas las pantallas del Cliente, así que
   * es el único lugar donde el botón puede ser consistente. Que cada pantalla
   * tuviera su propio encabezado es lo que hizo que se olvidara en seis.
   */
  protected salir(): void {
    // `cerrarSesion` ya navega a /login, gane o falle la llamada al servidor.
    this.auth.cerrarSesion();
  }
}
