import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import { environment } from '../../../../environments/environment';
import type { NotaDevolucion } from '../../../core/models/devoluciones.models';
import { BsPipe } from '../../../shared/bs.pipe';

/**
 * CU-22 · La nota de devolución — «boundary» DialogoNotaDevolucion.
 *
 * RF-37: lo que volvió y lo que salió con su talla y su precio, la diferencia,
 * el motivo y la conformidad del cliente (RN-20). Se puede imprimir para que
 * el cliente se la lleve.
 */
@Component({
  selector: 'app-nota-devolucion',
  imports: [DatePipe, MatButtonModule, MatDialogModule, MatIconModule, MatProgressBarModule, BsPipe],
  template: `
    @if (cargando()) {
      <mat-progress-bar mode="indeterminate" />
    }
    <mat-dialog-content class="nota">
      @if (error(); as e) {
        <p class="error" role="alert">{{ e }}</p>
      }
      @if (nota(); as n) {
        <header>
          <div>
            <h2>Nota de {{ n.tipo === 'CAMBIO' ? 'cambio' : 'devolución' }} {{ n.numero }}</h2>
            <p>
              {{ n.sucursal }} · {{ n.caja }} · {{ n.creado_en | date: 'dd/MM/yyyy HH:mm' }} ·
              atendió {{ n.cajero }}
            </p>
            <p>
              Venta original {{ n.venta_codigo }} del {{ n.venta_creada_en | date: 'dd/MM/yyyy HH:mm' }}
              ({{ n.horas_desde_la_venta }} h antes)
            </p>
          </div>
          <span class="estado" [class.abierta]="n.estado === 'ABIERTA'">{{ n.estado }}</span>
        </header>

        <h3>Lo que devolvió</h3>
        <table>
          <tr><th>Prenda</th><th>Talla</th><th>Color</th><th>Cant.</th><th>Precio pagado</th><th>Subtotal</th></tr>
          @for (l of n.devueltas; track l.variante_id) {
            <tr>
              <td>{{ l.producto }} <small>{{ l.sku }}</small></td>
              <td>{{ l.talla }}</td><td>{{ l.color }}</td><td>{{ l.cantidad }}</td>
              <td>{{ l.precio_unitario | bs }}</td><td>{{ l.subtotal | bs }}</td>
            </tr>
          }
          <tr class="total"><td colspan="5">Valor devuelto</td><td>{{ n.valor_devuelto | bs }}</td></tr>
        </table>

        @if (n.llevadas.length) {
          <h3>Lo que se llevó ({{ n.venta_nueva_codigo }})</h3>
          <table>
            <tr><th>Prenda</th><th>Talla</th><th>Color</th><th>Cant.</th><th>Precio</th><th>Subtotal</th></tr>
            @for (l of n.llevadas; track l.variante_id) {
              <tr>
                <td>{{ l.producto }} <small>{{ l.sku }}</small></td>
                <td>{{ l.talla }}</td><td>{{ l.color }}</td><td>{{ l.cantidad }}</td>
                <td>{{ l.precio_unitario | bs }}</td><td>{{ l.subtotal | bs }}</td>
              </tr>
            }
            <tr class="total"><td colspan="5">Total llevado</td><td>{{ n.total_llevado | bs }}</td></tr>
          </table>
          <p class="saldo">
            @switch (n.a_favor_de) {
              @case ('CLIENTE') { El cliente pagó la diferencia: <strong>{{ n.diferencia | bs }}</strong> }
              @case ('TIENDA') { La tienda devolvió la diferencia: <strong>{{ sinSigno(n.diferencia) | bs }}</strong> }
              @default { El cambio salió parejo: no hubo diferencia. }
            }
            @if (n.metodo_diferencia) { ({{ n.metodo_diferencia }}) }
          </p>
        } @else {
          <p class="saldo">
            Reintegrado del cajón: <strong>{{ n.monto_reintegrado | bs }}</strong>
            @if (esCero(n.monto_reintegrado)) { (no se cobró en efectivo: vuelve por el mismo medio) }
          </p>
        }

        <p><strong>Motivo:</strong> {{ n.motivo }}</p>
        <p class="conformidad">
          <mat-icon>{{ n.conforme ? 'verified' : 'help_outline' }}</mat-icon>
          @if (n.conforme === true) {
            El cliente dio su conformidad.
          } @else if (n.conforme === null) {
            Registrada antes de la nota de devolución: sin conformidad anotada.
          } @else {
            Espera la conformidad del cliente.
          }
          @if (n.observacion_cliente) { <em>«{{ n.observacion_cliente }}»</em> }
        </p>
      }
    </mat-dialog-content>
    <mat-dialog-actions align="end" class="no-imprimir">
      <button matButton type="button" mat-dialog-close>Cerrar</button>
      <button matButton="filled" class="vb-boton-marca" type="button" [disabled]="!nota()" (click)="imprimir()">
        <mat-icon>print</mat-icon> Imprimir
      </button>
    </mat-dialog-actions>
  `,
  styles: `
    .nota header { display: flex; justify-content: space-between; gap: 12px; }
    .nota h2 { margin: 0; font-size: 1.2rem; }
    .nota header p { margin: 2px 0; color: var(--mat-sys-on-surface-variant); font-size: 0.875rem; }
    .estado { align-self: flex-start; padding: 2px 8px; border-radius: 12px; background: var(--mat-sys-primary-container); }
    .estado.abierta { background: var(--mat-sys-error-container); }
    h3 { font-size: 1rem; margin: 16px 0 6px; }
    table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
    th, td { text-align: left; padding: 4px 6px; border-bottom: 1px solid var(--mat-sys-outline-variant); }
    small { color: var(--mat-sys-on-surface-variant); }
    .total td { font-weight: 600; }
    .saldo { margin-top: 10px; }
    .conformidad { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
    .error { color: var(--mat-sys-error); }
  `,
})
export class NotaDevolucionDialogo implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly id = inject<number>(MAT_DIALOG_DATA);

  protected readonly nota = signal<NotaDevolucion | null>(null);
  protected readonly cargando = signal(true);
  protected readonly error = signal<string | null>(null);

  ngOnInit(): void {
    this.http.get<NotaDevolucion>(`${environment.apiUrl}/pos/notas-devolucion/${this.id}`).subscribe({
      next: (n) => {
        this.nota.set(n);
        this.cargando.set(false);
      },
      error: (e: HttpErrorResponse) => {
        this.error.set(typeof e.error?.detail === 'string' ? e.error.detail : 'No se pudo abrir la nota.');
        this.cargando.set(false);
      },
    });
  }

  protected sinSigno(monto: string): string {
    return Math.abs(Number(monto)).toFixed(2);
  }

  protected esCero(monto: string): boolean {
    return Number(monto) === 0;
  }

  protected imprimir(): void {
    window.print();
  }
}
