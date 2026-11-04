import { Component, OnInit, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';

import {
  InventarioService,
  type ErrorInventario,
} from '../../../core/services/inventario.service';
import type { Kardex } from '../../../core/models/inventario.models';

export interface DatosKardex {
  variante_id: number;
  sucursal_id: number;
}

/**
 * CU-21 · Kardex de una prenda — «boundary» DialogoKardex.
 *
 * RF-53: todos los movimientos de la prenda en la sucursal, con el saldo que
 * dejó cada uno: ingresos, ventas, reservas, traspasos, devoluciones y ajustes,
 * también los que se registraron sin conexión. El saldo lo calcula el
 * servidor sobre toda la historia; la pantalla no suma nada.
 */
@Component({
  selector: 'app-kardex-dialogo',
  imports: [
    DatePipe,
    MatButtonModule,
    MatDialogModule,
    MatIconModule,
    MatPaginatorModule,
    MatProgressBarModule,
    MatTableModule,
    MatTooltipModule,
  ],
  template: `
    <h2 mat-dialog-title>Kardex</h2>
    @if (cargando()) {
      <mat-progress-bar mode="indeterminate" />
    }
    <mat-dialog-content>
      @if (error(); as e) {
        <p class="aviso" role="alert"><mat-icon>error_outline</mat-icon>{{ e }}</p>
      }
      @if (kardex(); as k) {
        <div class="prenda">
          <code>{{ k.sku }}</code>
          <div>
            <strong>{{ k.producto }}</strong>
            <span class="detalle">{{ k.talla }} · {{ k.color }} · {{ k.sucursal }}</span>
          </div>
        </div>
        <div class="saldos">
          <span><strong>{{ k.disponible }}</strong> disponibles</span>
          <span><strong>{{ k.reservada }}</strong> reservadas</span>
          <span><strong>{{ k.disponible + k.reservada }}</strong> en el local</span>
        </div>

        @if (k.items.length) {
          <div class="tabla-envoltura">
            <table mat-table [dataSource]="k.items">
              <ng-container matColumnDef="fecha">
                <th mat-header-cell *matHeaderCellDef>Fecha</th>
                <td mat-cell *matCellDef="let m">{{ m.creado_en | date: 'dd/MM/yy HH:mm' }}</td>
              </ng-container>
              <ng-container matColumnDef="tipo">
                <th mat-header-cell *matHeaderCellDef>Tipo</th>
                <td mat-cell *matCellDef="let m">
                  {{ m.tipo }}
                  @if (m.sin_conexion) {
                    <mat-icon class="sin-red" matTooltip="Registrado sin conexión">cloud_off</mat-icon>
                  }
                </td>
              </ng-container>
              <ng-container matColumnDef="cantidad">
                <th mat-header-cell *matHeaderCellDef class="numero">Cantidad</th>
                <td mat-cell *matCellDef="let m" class="numero" [class.entra]="m.cantidad > 0" [class.sale]="m.cantidad < 0">
                  {{ m.cantidad > 0 ? '+' + m.cantidad : m.cantidad }}
                </td>
              </ng-container>
              <ng-container matColumnDef="saldo">
                <th mat-header-cell *matHeaderCellDef class="numero">Saldo</th>
                <td mat-cell *matCellDef="let m" class="numero"><strong>{{ m.saldo }}</strong></td>
              </ng-container>
              <ng-container matColumnDef="detalle">
                <th mat-header-cell *matHeaderCellDef>Detalle</th>
                <td mat-cell *matCellDef="let m" class="motivo">
                  {{ m.motivo || '—' }}
                  @if (m.referencia) { <span class="ref">· {{ m.referencia }}</span> }
                </td>
              </ng-container>
              <ng-container matColumnDef="usuario">
                <th mat-header-cell *matHeaderCellDef>Usuario</th>
                <td mat-cell *matCellDef="let m">{{ m.usuario || 'Sistema' }}</td>
              </ng-container>
              <tr mat-header-row *matHeaderRowDef="columnas"></tr>
              <tr mat-row *matRowDef="let fila; columns: columnas"></tr>
            </table>
          </div>
          <mat-paginator
            [length]="k.total"
            [pageSize]="k.tamano"
            [pageIndex]="k.pagina - 1"
            [hidePageSize]="true"
            (page)="paginar($event)"
          />
        } @else {
          <p class="vacio">Esta prenda todavía no tiene movimientos en la sucursal.</p>
        }
      }
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button matButton mat-dialog-close type="button">Cerrar</button>
    </mat-dialog-actions>
  `,
  styles: `
    .prenda { display: flex; gap: 12px; align-items: center; margin-bottom: 8px; }
    .prenda code { background: var(--mat-sys-surface-container); padding: 2px 6px; border-radius: 4px; }
    .detalle { display: block; color: var(--mat-sys-on-surface-variant); font-size: 0.875rem; }
    .saldos { display: flex; gap: 24px; flex-wrap: wrap; margin: 8px 0 16px; }
    .tabla-envoltura { overflow-x: auto; }
    table { width: 100%; }
    .numero { text-align: right; }
    .entra { color: var(--mat-sys-primary); }
    .sale { color: var(--mat-sys-error); }
    .motivo { max-width: 320px; }
    .ref { color: var(--mat-sys-on-surface-variant); }
    .sin-red { font-size: 16px; width: 16px; height: 16px; vertical-align: middle; margin-left: 4px; }
    .aviso { display: flex; gap: 8px; align-items: center; color: var(--mat-sys-error); }
    .vacio { color: var(--mat-sys-on-surface-variant); }
  `,
})
export class KardexDialogo implements OnInit {
  private readonly api = inject(InventarioService);
  private readonly datos = inject<DatosKardex>(MAT_DIALOG_DATA);

  protected readonly columnas = ['fecha', 'tipo', 'cantidad', 'saldo', 'detalle', 'usuario'];
  protected readonly kardex = signal<Kardex | null>(null);
  protected readonly cargando = signal(false);
  protected readonly error = signal<string | null>(null);

  ngOnInit(): void {
    this.cargar(1);
  }

  protected paginar(evento: PageEvent): void {
    this.cargar(evento.pageIndex + 1);
  }

  private cargar(pagina: number): void {
    this.cargando.set(true);
    this.api.kardex(this.datos.variante_id, this.datos.sucursal_id, pagina, 20).subscribe({
      next: (k) => {
        this.kardex.set(k);
        this.error.set(null);
        this.cargando.set(false);
      },
      error: (e: ErrorInventario) => {
        this.error.set(e.mensaje);
        this.cargando.set(false);
      },
    });
  }
}
