import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar } from '@angular/material/snack-bar';

import { environment } from '../../../../environments/environment';
import {
  ROTULO_SOLICITUD,
  type EstadoSolicitud,
  type Solicitud,
} from '../../../core/models/devoluciones-web.models';
import { BsPipe } from '../../../shared/bs.pipe';
import { NotaDevolucionDialogo } from '../../caja/devolucion/nota-devolucion';

/**
 * CU-24 · Mis solicitudes de cambio o devolución — «boundary» ListaMisSolicitudes.
 *
 * Lo que el cliente pidió por la web y en qué quedó, con la respuesta de la
 * tienda cuando la rechazó (RF-36).
 */
@Component({
  selector: 'app-mis-solicitudes',
  imports: [
    DatePipe,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    BsPipe,
  ],
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
              @if (s.estado === 'APROBADA' && s.tipo === 'CAMBIO') {
                <span class="respuesta">Pasá por {{ s.sucursal }} con la prenda: el cambio se hace en caja.</span>
              } @else if (s.estado === 'APROBADA') {
                <span class="respuesta">Llevá o enviá la prenda a {{ s.sucursal }}: al recibirla te devolvemos el dinero.</span>
              }
              <!-- CU-25 (RN-20): la nota se cierra con tu conformidad. -->
              @if (s.devolucion_id) {
                <span class="detalle">
                  Nota {{ s.numero_nota }}
                  @if (s.reembolso_monto) { · te devolvimos {{ s.reembolso_monto | bs }} por el mismo medio de pago }
                  · {{ s.nota_estado === 'CERRADA' ? 'cerrada' : 'abierta' }}
                </span>
                <div class="acciones">
                  <button matButton type="button" (click)="verNota(s)">
                    <mat-icon>receipt_long</mat-icon> Ver nota
                  </button>
                </div>
                @if (s.nota_estado === 'ABIERTA') {
                  <div class="acciones">
                    <mat-form-field appearance="outline" class="obs">
                      <mat-label>Tu observación (opcional)</mat-label>
                      <input matInput maxlength="300" #obs />
                    </mat-form-field>
                    <button matButton="filled" class="vb-boton-marca" type="button" (click)="conformidad(s, true, obs.value)">
                      Estoy conforme
                    </button>
                    <button matButton="outlined" type="button" (click)="conformidad(s, false, obs.value)">
                      No estoy conforme
                    </button>
                  </div>
                  @if (s.conforme === false) {
                    <span class="respuesta">Dijiste que no estás conforme: la tienda lo va a revisar.</span>
                  }
                }
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
    .acciones { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-top: 6px; }
    .obs { flex: 1 1 240px; }
    .estado { padding: 1px 8px; border-radius: 12px; font-size: 0.8rem; background: var(--mat-sys-surface-container); }
    .estado-RECHAZADA { background: var(--mat-sys-error-container); }
    .estado-APROBADA, .estado-COMPLETADA { background: var(--mat-sys-primary-container); }
  `,
})
export class MisSolicitudes implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly dialogo = inject(MatDialog);
  private readonly aviso = inject(MatSnackBar);
  private readonly base = `${environment.apiUrl}/tienda/devoluciones`;
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

  protected verNota(s: Solicitud): void {
    this.dialogo.open(NotaDevolucionDialogo, {
      data: { url: `${this.base}/${s.id}/nota` },
      width: '760px',
      maxWidth: '95vw',
    });
  }

  /** CU-25 (RN-20): conforme cierra la nota; no conforme la deja abierta. */
  protected conformidad(s: Solicitud, conforme: boolean, observacion: string): void {
    this.http
      .post<Solicitud>(`${this.base}/${s.id}/conformidad`, {
        conforme,
        observacion: observacion.trim() || null,
      })
      .subscribe({
        next: () => {
          this.aviso.open(conforme ? 'Gracias: la nota quedó cerrada.' : 'Listo: la tienda va a revisarlo.', 'Cerrar', {
            duration: 5000,
          });
          this.recargar();
        },
        error: () => this.aviso.open('No se pudo guardar tu respuesta.', 'Cerrar', { duration: 5000 }),
      });
  }

  protected rotulo(estado: EstadoSolicitud): string {
    return ROTULO_SOLICITUD[estado];
  }
}
