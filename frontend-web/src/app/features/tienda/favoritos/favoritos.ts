import { Component, OnInit, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Router, RouterLink } from '@angular/router';

import { TiendaService, type ErrorTienda } from '../../../core/services/tienda.service';
import type { PaginaFavoritos, ProductoVitrina } from '../../../core/models/tienda.models';

/**
 * CU-20 · Gestionar favoritos — «boundary» PantallaFavoritos.
 *
 * La lista del Cliente, con lo último marcado primero. Las tarjetas son las
 * mismas que las del catálogo: la pantalla muestra exactamente lo mismo, y un
 * componente propio de tarjeta haría que la misma prenda se pudiera ver
 * distinta en cada lugar.
 *
 * **Solo lista lo que sigue ofreciéndose.** Si una prenda marcada se desactiva,
 * desaparece de acá pero la fila no se borra: es historial de preferencia y lo
 * consume el recomendador del CU-33 (RF31). Mostrarla sería ofrecer algo que no
 * se puede comprar.
 *
 * A diferencia del resto de la tienda, esta ruta **exige sesión de Cliente**:
 * un favorito es de alguien.
 */
@Component({
  selector: 'app-favoritos',
  imports: [
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatPaginatorModule,
    MatProgressBarModule,
    MatTooltipModule,
  ],
  templateUrl: './favoritos.html',
  styleUrl: './favoritos.scss',
})
export class Favoritos implements OnInit {
  private readonly api = inject(TiendaService);
  private readonly router = inject(Router);

  protected readonly cargando = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly pagina = signal<PaginaFavoritos | null>(null);

  private indice = 0;
  private tamano = 12;

  ngOnInit(): void {
    this.consultar();
  }

  protected paginar(evento: PageEvent): void {
    this.indice = evento.pageIndex;
    this.tamano = evento.pageSize;
    this.consultar();
  }

  protected abrir(producto: ProductoVitrina): void {
    this.router.navigate(['/tienda/producto', producto.id]);
  }

  protected foto(producto: ProductoVitrina): string | null {
    return this.api.urlDeImagen(producto.imagen_url);
  }

  protected precio(producto: ProductoVitrina): string {
    if (!producto.precio_desde) return 'Sin precio';
    if (producto.precio_hasta && producto.precio_hasta !== producto.precio_desde) {
      return `desde Bs ${producto.precio_desde}`;
    }
    return `Bs ${producto.precio_desde}`;
  }

  /**
   * Quita la prenda de la lista.
   *
   * Se saca de la pantalla antes de que responda el servidor, por lo mismo que
   * el corazón del catálogo: esperar hace que parezca que no funcionó. Si el
   * servidor falla, se vuelve a consultar —y no se «devuelve» la tarjeta a
   * mano— porque el total y la paginación también cambiaron.
   */
  protected quitar(producto: ProductoVitrina, evento: Event): void {
    evento.stopPropagation();

    const actual = this.pagina();
    if (actual) {
      this.pagina.set({
        ...actual,
        total: actual.total - 1,
        items: actual.items.filter((p) => p.id !== producto.id),
      });
    }

    this.api.desmarcarFavorito(producto.id).subscribe({
      error: () => {
        this.error.set('No se pudo quitar la prenda de tus favoritos.');
        this.consultar();
      },
    });
  }

  private consultar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.api.listarFavoritos(this.indice + 1, this.tamano).subscribe({
      next: (pagina) => {
        this.pagina.set(pagina);
        this.cargando.set(false);
      },
      error: (fallo: ErrorTienda) => {
        this.error.set(fallo.mensaje);
        this.pagina.set(null);
        this.cargando.set(false);
      },
    });
  }
}
