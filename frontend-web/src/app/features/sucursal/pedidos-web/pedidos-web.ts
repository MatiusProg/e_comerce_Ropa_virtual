import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTabsModule } from '@angular/material/tabs';

import { environment } from '../../../../environments/environment';
import {
  ROTULO_SOLICITUD,
  type EstadoSolicitud,
  type PedidoDeSucursal,
  type Solicitud,
} from '../../../core/models/devoluciones-web.models';
import { BsPipe } from '../../../shared/bs.pipe';

/**
 * Pedidos web de la sucursal — «boundary» PantallaPedidosWeb (encargado).
 *
 * - **Por entregar:** los pedidos pagados. Al entregarlos se guarda la hora, y
 *   desde ahí corre la ventana de devolución (precondición de CU-24).
 * - **Cambios y devoluciones:** lo que pidieron los clientes (CU-24). Atenderlas
 *   es el CU-25.
 */
@Component({
  selector: 'app-pedidos-web',
  imports: [DatePipe, MatButtonModule, MatCardModule, MatIconModule, MatTabsModule, BsPipe],
  template: `
    <header class="encabezado">
      <h1 class="vb-titulo">Pedidos web</h1>
      <p class="bajada">Entregá los pedidos pagados y mirá los cambios y devoluciones que piden los clientes.</p>
    </header>
    <mat-card class="vb-filete-superior" appearance="outlined">
      <mat-tab-group animationDuration="0ms">
        <mat-tab label="Por entregar ({{ porEntregar().length }})">
          <div class="panel">
            @for (p of porEntregar(); track p.codigo) {
              <div class="fila">
                <div>
                  <strong>{{ p.codigo }}</strong> · {{ p.cliente || 'Cliente' }}
                  <span class="detalle">
                    {{ p.unidades }} prendas · {{ p.total | bs }} ·
                    {{ p.modalidad_entrega === 'ENVIO' ? 'Envío' : 'Retiro en tienda' }} ·
                    pedido el {{ p.creado_en | date: 'dd/MM HH:mm' }}
                  </span>
                </div>
                <button matButton="filled" class="vb-boton-marca" type="button"
                        [disabled]="entregando() === p.codigo" (click)="entregar(p)">
                  <mat-icon>inventory</mat-icon> Entregar
                </button>
              </div>
            } @empty {
              <p class="vacio">No hay pedidos pagados esperando entrega.</p>
            }
          </div>
        </mat-tab>
        <mat-tab label="Cambios y devoluciones ({{ pendientes() }})">
          <div class="panel">
            @for (s of solicitudes(); track s.id) {
              <div class="fila">
                <div>
                  <strong>{{ s.tipo === 'CAMBIO' ? 'Cambio' : 'Devolución' }} · {{ s.venta_codigo }}</strong>
                  · {{ s.cliente }}
                  <span class="detalle">
                    @for (l of s.lineas; track l.variante_id; let ultimo = $last) {
                      {{ l.cantidad }}× {{ l.producto }} {{ l.talla }} {{ l.color }}
                      @if (l.talla_nueva) { → {{ l.talla_nueva }} {{ l.color_nueva }} }{{ ultimo ? '' : ',' }}
                    }
                  </span>
                  <span class="detalle">«{{ s.motivo }}» · {{ s.creado_en | date: 'dd/MM HH:mm' }}</span>
                </div>
                <span class="estado" [class]="'estado-' + s.estado">{{ rotulo(s.estado) }}</span>
              </div>
            } @empty {
              <p class="vacio">Todavía no hay solicitudes.</p>
            }
          </div>
        </mat-tab>
      </mat-tab-group>
      @if (error(); as e) {
        <p class="error" role="alert">{{ e }}</p>
      }
    </mat-card>
  `,
  styles: `
    :host { display: block; max-width: 64rem; margin: 0 auto; }
    .encabezado { margin-bottom: 16px; }
    .bajada { color: var(--mat-sys-on-surface-variant); margin: 0; }
    .panel { padding: 8px 16px 16px; }
    .fila { display: flex; justify-content: space-between; align-items: center; gap: 12px;
            padding: 10px 0; border-bottom: 1px solid var(--mat-sys-outline-variant); }
    .detalle { display: block; font-size: 0.875rem; color: var(--mat-sys-on-surface-variant); }
    .vacio { color: var(--mat-sys-on-surface-variant); }
    .error { color: var(--mat-sys-error); padding: 0 16px 16px; }
    .estado { padding: 1px 8px; border-radius: 12px; font-size: 0.8rem; white-space: nowrap;
              background: var(--mat-sys-surface-container); }
    .estado-RECHAZADA { background: var(--mat-sys-error-container); }
    .estado-APROBADA, .estado-COMPLETADA { background: var(--mat-sys-primary-container); }
  `,
})
export class PedidosWeb implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly aviso = inject(MatSnackBar);
  private readonly base = `${environment.apiUrl}/sucursal`;

  protected readonly porEntregar = signal<PedidoDeSucursal[]>([]);
  protected readonly solicitudes = signal<Solicitud[]>([]);
  protected readonly entregando = signal<string | null>(null);
  protected readonly error = signal<string | null>(null);

  protected pendientes(): number {
    return this.solicitudes().filter((s) => s.estado === 'PENDIENTE').length;
  }

  ngOnInit(): void {
    this.cargar();
  }

  private cargar(): void {
    this.http.get<PedidoDeSucursal[]>(`${this.base}/pedidos`, { params: { estado: 'PAGADA' } }).subscribe({
      next: (p) => this.porEntregar.set(p),
      error: (e: HttpErrorResponse) => this.error.set(this.mensaje(e)),
    });
    this.http.get<Solicitud[]>(`${this.base}/solicitudes-devolucion`).subscribe({
      next: (s) => this.solicitudes.set(s),
      error: (e: HttpErrorResponse) => this.error.set(this.mensaje(e)),
    });
  }

  protected entregar(p: PedidoDeSucursal): void {
    this.entregando.set(p.codigo);
    this.http.post<PedidoDeSucursal>(`${this.base}/pedidos/${p.codigo}/entregar`, {}).subscribe({
      next: () => {
        this.entregando.set(null);
        this.aviso.open(`Pedido ${p.codigo} entregado. Desde ahora corre la ventana de devolución.`, 'Cerrar', {
          duration: 5000,
        });
        this.cargar();
      },
      error: (e: HttpErrorResponse) => {
        this.entregando.set(null);
        this.error.set(this.mensaje(e));
      },
    });
  }

  protected rotulo(estado: EstadoSolicitud): string {
    return ROTULO_SOLICITUD[estado];
  }

  private mensaje(e: HttpErrorResponse): string {
    return typeof e.error?.detail === 'string' ? e.error.detail : 'No se pudo cargar.';
  }
}
