import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';

import { environment } from '../../../../environments/environment';
import {
  ROTULO_SOLICITUD,
  type EstadoSolicitud,
  type Solicitud,
} from '../../../core/models/devoluciones-web.models';
import { BsPipe } from '../../../shared/bs.pipe';

/**
 * CU-24 · Mis solicitudes de cambio o devolución — «boundary» ListaMisSolicitudes.
 *
 * Lo que el cliente pidió por la web y en qué quedó, con la respuesta de la
 * tienda cuando la rechazó (RF-36).
 */
@Component({
  selector: 'app-mis-solicitudes',
  imports: [DatePipe, MatCardModule, MatIconModule, BsPipe],
  template: `
    @if (solicitudes().length) {
      <mat-card class="solicitudes vb-filete-superior" appearance="outlined">
        <mat-card-content>
          <h2><mat-icon>assignment_return</mat-icon> Mis cambios y devoluciones</h2>
          @for (s of solicitudes(); track s.id) {
            <div class="solicitud">
              <div class="cabecera">
                <strong>{{ s.tipo === 'CAMBIO' ? 'Cambio' : 'Devolución' }} · pedido {{ s.venta_codigo }}</strong>
                <span class="estado" [class]="'estado-' + s.estado">{{ rotulo(s.estado) }}</span>
              </div>
              <span class="detalle">
                {{ s.creado_en | date: 'dd/MM/yyyy HH:mm' }} · {{ s.sucursal }} ·
                @for (l of s.lineas; track l.variante_id; let ultimo = $last) {
                  {{ l.cantidad }}× {{ l.producto }} {{ l.talla }}
                  @if (l.talla_nueva) { → {{ l.talla_nueva }} {{ l.color_nueva }} }{{ ultimo ? '' : ',' }}
                }
              </span>
              @if (s.diferencia !== null && s.diferencia !== '0.00') {
                <span class="detalle">Diferencia a saldar al retirar: {{ s.diferencia | bs }}</span>
              }
              @if (s.respuesta) {
                <span class="respuesta">Respuesta de la tienda: {{ s.respuesta }}</span>
              }
            </div>
          }
        </mat-card-content>
      </mat-card>
    }
  `,
  styles: `
    .solicitudes { margin-top: 24px; }
    h2 { display: flex; gap: 8px; align-items: center; font-size: 1.1rem; margin: 0 0 8px; }
    .solicitud { padding: 8px 0; border-bottom: 1px solid var(--mat-sys-outline-variant); }
    .cabecera { display: flex; justify-content: space-between; gap: 8px; }
    .detalle, .respuesta { display: block; font-size: 0.875rem; color: var(--mat-sys-on-surface-variant); }
    .respuesta { color: var(--mat-sys-on-surface); }
    .estado { padding: 1px 8px; border-radius: 12px; font-size: 0.8rem; background: var(--mat-sys-surface-container); }
    .estado-RECHAZADA { background: var(--mat-sys-error-container); }
    .estado-APROBADA, .estado-COMPLETADA { background: var(--mat-sys-primary-container); }
  `,
})
export class MisSolicitudes implements OnInit {
  private readonly http = inject(HttpClient);
  protected readonly solicitudes = signal<Solicitud[]>([]);

  ngOnInit(): void {
    this.recargar();
  }

  recargar(): void {
    this.http.get<Solicitud[]>(`${environment.apiUrl}/tienda/devoluciones`).subscribe({
      next: (s) => this.solicitudes.set(s),
      error: () => this.solicitudes.set([]),
    });
  }

  protected rotulo(estado: EstadoSolicitud): string {
    return ROTULO_SOLICITUD[estado];
  }
}
