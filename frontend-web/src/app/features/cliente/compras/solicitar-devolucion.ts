import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { minimoSinEspacios } from '../../../shared/validadores';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';

import { environment } from '../../../../environments/environment';
import type {
  LineaDevolvibleWeb,
  PedidoDevolvible,
  Solicitud,
  TipoSolicitud,
} from '../../../core/models/devoluciones-web.models';
import { BsPipe } from '../../../shared/bs.pipe';

interface Eleccion {
  linea: LineaDevolvibleWeb;
  cantidad: number;
  nueva: number | null;
}

/**
 * CU-24 · Solicitar cambio o devolución por la web — «boundary» DialogoSolicitud.
 *
 * El cliente elige qué prendas vuelven y, en un cambio, por cuál talla o color.
 * La ventana corre desde la entrega (RF-35) y la valida el servidor (RN-08);
 * acá se informa antes, para no armar una solicitud que va a rebotar.
 */
@Component({
  selector: 'app-solicitar-devolucion',
  imports: [
    DatePipe,
    ReactiveFormsModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatSelectModule,
    BsPipe,
  ],
  template: `
    <h2 mat-dialog-title>Cambio o devolución · {{ codigo }}</h2>
    @if (cargando()) {
      <mat-progress-bar mode="indeterminate" />
    }
    <mat-dialog-content>
      @if (error(); as e) {
        <p class="error" role="alert"><mat-icon>error_outline</mat-icon> {{ e }}</p>
      }
      @if (pedido(); as p) {
        <p class="plazo" [class.vencido]="!p.dentro_de_plazo">
          <mat-icon>{{ p.dentro_de_plazo ? 'schedule' : 'event_busy' }}</mat-icon>
          <span>
            @if (p.dentro_de_plazo) {
              Podés pedirlo hasta el <strong>{{ p.vence_en | date: 'dd/MM/yyyy HH:mm' }}</strong>
              ({{ p.ventana_horas }} horas desde la entrega). La atiende {{ p.sucursal }}.
            } @else {
              El plazo de {{ p.ventana_horas }} horas desde la entrega venció el
              {{ p.vence_en | date: 'dd/MM/yyyy HH:mm' }}.
            }
          </span>
        </p>

        @if (p.dentro_de_plazo) {
          <mat-button-toggle-group [value]="tipo()" (change)="cambiarTipo($event.value)">
            <mat-button-toggle value="DEVOLUCION"><mat-icon>assignment_return</mat-icon> Devolver</mat-button-toggle>
            <mat-button-toggle value="CAMBIO"><mat-icon>swap_horiz</mat-icon> Cambiar talla o color</mat-button-toggle>
          </mat-button-toggle-group>

          @for (e of elecciones(); track e.linea.variante_id) {
            <div class="linea">
              <div class="prenda">
                <strong>{{ e.linea.producto }}</strong>
                <span>{{ e.linea.talla }} · {{ e.linea.color }} · pagaste {{ e.linea.precio_pagado | bs }}</span>
                @if (e.linea.comprometidas) {
                  <small>{{ e.linea.comprometidas }} ya volvieron o están pedidas</small>
                }
              </div>
              <div class="cantidad">
                <button matIconButton type="button" [disabled]="e.cantidad === 0" (click)="mover(e, -1)"
                        [attr.aria-label]="'Una menos de ' + e.linea.producto">
                  <mat-icon>remove</mat-icon>
                </button>
                <span>{{ e.cantidad }} / {{ e.linea.devolvibles }}</span>
                <button matIconButton type="button" [disabled]="e.cantidad >= e.linea.devolvibles" (click)="mover(e, 1)"
                        [attr.aria-label]="'Una más de ' + e.linea.producto">
                  <mat-icon>add</mat-icon>
                </button>
              </div>
              @if (tipo() === 'CAMBIO' && e.cantidad > 0) {
                <mat-form-field appearance="outline" class="nueva">
                  <mat-label>A cambio de</mat-label>
                  <mat-select [value]="e.nueva" (selectionChange)="elegirNueva(e, $event.value)">
                    @for (o of e.linea.opciones_de_cambio; track o.variante_id) {
                      <mat-option [value]="o.variante_id">
                        {{ o.talla }} · {{ o.color }} · {{ o.precio | bs }} ({{ o.disponible }} en tienda)
                      </mat-option>
                    }
                  </mat-select>
                  @if (!e.linea.opciones_de_cambio.length) {
                    <mat-hint>No hay otra talla o color en la sucursal.</mat-hint>
                  }
                </mat-form-field>
              }
            </div>
          }

          @if (tipo() === 'CAMBIO' && diferencia() !== null) {
            <p class="diferencia">
              @if (diferencia()! > 0) {
                Al retirar pagás la diferencia: <strong>{{ enTexto(diferencia()!) | bs }}</strong>.
              } @else if (diferencia()! < 0) {
                Al retirar te devolvemos <strong>{{ enTexto(diferencia()!) | bs }}</strong>.
              } @else {
                El cambio sale parejo.
              }
              El precio final lo confirma la tienda al entregarte la prenda.
            </p>
          }

          <mat-form-field appearance="outline" class="ancho">
            <mat-label>¿Por qué?</mat-label>
            <textarea matInput rows="2" maxlength="300" [formControl]="motivo"></textarea>
            @if (motivo.invalid && motivo.touched) {
              <mat-error>Contanos el motivo (al menos 5 letras).</mat-error>
            }
          </mat-form-field>
        }
      }
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button matButton type="button" mat-dialog-close>Cancelar</button>
      <button
        matButton="filled"
        class="vb-boton-marca"
        type="button"
        [disabled]="!sePuede() || enviando()"
        (click)="enviar()"
      >
        Enviar solicitud
      </button>
    </mat-dialog-actions>
  `,
  styles: `
    .plazo { display: flex; gap: 8px; align-items: center; }
    .plazo.vencido, .error { color: var(--mat-sys-error); }
    .linea { display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: center;
             padding: 8px 0; border-bottom: 1px solid var(--mat-sys-outline-variant); }
    .prenda { display: flex; flex-direction: column; }
    .prenda span, .prenda small { color: var(--mat-sys-on-surface-variant); font-size: 0.875rem; }
    .cantidad { display: flex; align-items: center; gap: 4px; }
    .nueva { grid-column: 1 / -1; }
    .ancho { width: 100%; margin-top: 12px; }
    mat-button-toggle-group { margin: 8px 0; }
    .diferencia { margin-top: 8px; }
  `,
})
export class SolicitarDevolucion implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly ref = inject(MatDialogRef<SolicitarDevolucion, Solicitud | undefined>);
  protected readonly codigo = inject<string>(MAT_DIALOG_DATA);
  private readonly base = `${environment.apiUrl}/tienda/devoluciones`;

  protected readonly pedido = signal<PedidoDevolvible | null>(null);
  protected readonly elecciones = signal<Eleccion[]>([]);
  protected readonly tipo = signal<TipoSolicitud>('DEVOLUCION');
  protected readonly cargando = signal(true);
  protected readonly enviando = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly motivo = new FormControl('', {
    nonNullable: true,
    validators: [minimoSinEspacios(5), Validators.maxLength(300)],
  });

  protected readonly elegidas = computed(() => this.elecciones().filter((e) => e.cantidad > 0));

  /** En un cambio: lo nuevo menos lo pagado, en Bs. Null si falta elegir. */
  protected readonly diferencia = computed(() => {
    const elegidas = this.elegidas();
    if (!elegidas.length || elegidas.some((e) => e.nueva === null)) return null;
    let total = 0;
    for (const e of elegidas) {
      const opcion = e.linea.opciones_de_cambio.find((o) => o.variante_id === e.nueva)!;
      total += (Number(opcion.precio) - Number(e.linea.precio_pagado)) * e.cantidad;
    }
    return Math.round(total * 100) / 100;
  });

  protected readonly sePuede = computed(() => {
    if (!this.pedido()?.dentro_de_plazo || !this.elegidas().length) return false;
    if (this.tipo() === 'CAMBIO' && this.elegidas().some((e) => e.nueva === null)) return false;
    return true;
  });

  ngOnInit(): void {
    this.http.get<PedidoDevolvible>(`${this.base}/pedidos/${encodeURIComponent(this.codigo)}`).subscribe({
      next: (p) => {
        this.pedido.set(p);
        this.elecciones.set(p.lineas.map((linea) => ({ linea, cantidad: 0, nueva: null })));
        this.cargando.set(false);
      },
      error: (e: HttpErrorResponse) => {
        this.error.set(this.mensaje(e));
        this.cargando.set(false);
      },
    });
  }

  protected enTexto(monto: number): string {
    return Math.abs(monto).toFixed(2);
  }

  protected cambiarTipo(tipo: TipoSolicitud): void {
    this.tipo.set(tipo);
    this.elecciones.update((es) => es.map((e) => ({ ...e, nueva: null })));
  }

  protected mover(e: Eleccion, paso: number): void {
    this.elecciones.update((es) =>
      es.map((x) => (x === e ? { ...x, cantidad: Math.max(0, x.cantidad + paso) } : x)),
    );
  }

  protected elegirNueva(e: Eleccion, variante: number): void {
    this.elecciones.update((es) => es.map((x) => (x === e ? { ...x, nueva: variante } : x)));
  }

  protected enviar(): void {
    if (this.motivo.invalid) {
      this.motivo.markAsTouched();
      return;
    }
    this.enviando.set(true);
    this.http
      .post<Solicitud>(this.base, {
        venta_codigo: this.codigo,
        tipo: this.tipo(),
        motivo: this.motivo.value.trim(),
        lineas: this.elegidas().map((e) => ({
          variante_id: e.linea.variante_id,
          cantidad: e.cantidad,
          ...(this.tipo() === 'CAMBIO' ? { variante_nueva_id: e.nueva } : {}),
        })),
      })
      .subscribe({
        next: (s) => this.ref.close(s),
        error: (e: HttpErrorResponse) => {
          this.enviando.set(false);
          this.error.set(this.mensaje(e));
        },
      });
  }

  private mensaje(e: HttpErrorResponse): string {
    const d = e.error?.detail;
    return typeof d === 'string' ? d : 'No se pudo completar. Revisá los datos.';
  }
}
