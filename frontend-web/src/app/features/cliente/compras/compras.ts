import { CurrencyPipe, DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatIconModule } from '@angular/material/icon';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';

import {
  ComprasService,
  type ErrorCompras,
  type PaginaCompras,
} from '../../../core/services/compras.service';
import type { EstadoPedido, Pedido } from '../../../core/models/pedidos.models';
import { NavegacionCliente } from '../../../shared/navegacion-cliente/navegacion-cliente';

/** Los estados en los que la compra ya se cobró y tiene recibo. */
const CON_COMPROBANTE: EstadoPedido[] = ['PAGADA', 'ENTREGADA'];

/**
 * CU-29 · Consultar historial de compras — «boundary» PantallaMisCompras.
 *
 * Cierra el flujo del cliente. Hasta que existió, alguien compraba y **no tenía
 * dónde ver lo que compró**: sólo llegaba a su pedido si conservaba el código
 * que quedaba en la URL después de pagar.
 *
 * **Se muestran todas las compras**, incluidas las canceladas y las que esperan
 * pago. Un historial que sólo mostrara lo pagado dejaría al cliente sin forma de
 * encontrar el pedido que acaba de hacer —que es justo el que va a buscar— ni de
 * entender por qué un cobro que recuerda no aparece. El estado se muestra; la
 * fila no se esconde.
 */
@Component({
  selector: 'app-compras',
  imports: [
    NavegacionCliente,
    CurrencyPipe,
    DatePipe,
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatExpansionModule,
    MatIconModule,
    MatPaginatorModule,
    MatProgressBarModule,
    MatTooltipModule,
  ],
  templateUrl: './compras.html',
  styleUrl: './compras.scss',
})
export class Compras implements OnInit {
  private readonly api = inject(ComprasService);
  private readonly aviso = inject(MatSnackBar);

  protected readonly cargando = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly pagina = signal<PaginaCompras | null>(null);
  /** El código cuya descarga está en vuelo, para deshabilitar sólo ese botón. */
  protected readonly descargando = signal<string | null>(null);

  private indice = 0;
  private tamano = 10;

  protected readonly vacio = computed(() => this.pagina()?.total === 0);

  ngOnInit(): void {
    this.cargar();
  }

  private cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.api.listar(this.indice + 1, this.tamano).subscribe({
      next: (p) => {
        this.pagina.set(p);
        this.cargando.set(false);
      },
      error: (e: ErrorCompras) => {
        this.error.set(e.mensaje);
        this.cargando.set(false);
      },
    });
  }

  protected paginar(evento: PageEvent): void {
    this.indice = evento.pageIndex;
    this.tamano = evento.pageSize;
    this.cargar();
  }

  protected tieneComprobante(compra: Pedido): boolean {
    return CON_COMPROBANTE.includes(compra.estado);
  }

  /**
   * Descarga el recibo y lo guarda.
   *
   * Pasa por `HttpClient` y no por un `<a href>` porque el endpoint exige el
   * token, y un enlace del navegador no pasa por el interceptor que lo adjunta.
   * El `objectURL` se revoca enseguida: si no, el blob queda en memoria hasta
   * que se cierre la pestaña, y un cliente que descargue varios recibos los va
   * acumulando todos.
   */
  protected descargar(compra: Pedido): void {
    if (this.descargando() !== null) return;
    this.descargando.set(compra.codigo);

    this.api.comprobante(compra.codigo).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const enlace = document.createElement('a');
        enlace.href = url;
        enlace.download = `recibo-${compra.codigo}.pdf`;
        enlace.click();
        URL.revokeObjectURL(url);
        this.descargando.set(null);
      },
      error: (e: ErrorCompras) => {
        this.descargando.set(null);
        this.aviso.open(e.mensaje, 'Entendido', { duration: 6000 });
      },
    });
  }

  /** Cómo se llama cada estado para el cliente, que no habla en mayúsculas. */
  protected rotulo(estado: EstadoPedido): string {
    switch (estado) {
      case 'PAGADA':
        return 'Pagada';
      case 'ENTREGADA':
        return 'Entregada';
      case 'CANCELADA':
        return 'Cancelada';
      default:
        return 'Esperando pago';
    }
  }

  /**
   * El color del estado.
   *
   * `PENDIENTE_PAGO` NO va en rojo: no falló nada, sólo no terminó. En rojo el
   * cliente creería que perdió la compra.
   */
  protected tono(estado: EstadoPedido): 'bueno' | 'malo' | 'espera' {
    if (estado === 'PAGADA' || estado === 'ENTREGADA') return 'bueno';
    if (estado === 'CANCELADA') return 'malo';
    return 'espera';
  }
}
