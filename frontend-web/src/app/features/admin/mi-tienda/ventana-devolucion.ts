import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar } from '@angular/material/snack-bar';

import { environment } from '../../../../environments/environment';

/**
 * CU-23 · Configurar la ventana de devolución — «boundary» PanelVentanaDevolucion.
 *
 * RF-35 / RN-08: cuántas horas después de la compra o la entrega se acepta un
 * cambio o una devolución. Es de cada empresa y vale desde que se guarda,
 * también para las ventas anteriores: el plazo se calcula al pedir el cambio.
 * No depende del plan.
 */
@Component({
  selector: 'app-ventana-devolucion',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
  ],
  template: `
    <mat-card class="ventana vb-filete-superior" appearance="outlined">
      <mat-card-content>
        <h2><mat-icon>assignment_return</mat-icon> Ventana de devolución</h2>
        <p class="ayuda">
          Cuántas horas después de la compra o de la entrega se aceptan cambios y
          devoluciones, en caja y por la web. Fuera de la ventana se rechazan.
        </p>
        <div class="fila">
          <mat-form-field appearance="outline">
            <mat-label>Horas</mat-label>
            <input matInput type="number" min="1" max="720" [formControl]="horas" />
            <mat-hint>{{ comoTexto() }}</mat-hint>
            @if (horas.invalid) {
              <mat-error>Entre 1 hora y 720 (30 días).</mat-error>
            }
          </mat-form-field>
          @for (atajo of atajos; track atajo) {
            <button matButton="outlined" type="button" (click)="horas.setValue(atajo)">
              {{ atajo }} h
            </button>
          }
          <button
            matButton="filled"
            class="vb-boton-marca"
            type="button"
            [disabled]="horas.invalid || guardando() || horas.value === guardadas()"
            (click)="guardar()"
          >
            Guardar
          </button>
        </div>
        @if (error(); as e) {
          <p class="error" role="alert">{{ e }}</p>
        }
      </mat-card-content>
    </mat-card>
  `,
  styles: `
    .ventana { margin-top: 24px; }
    h2 { display: flex; gap: 8px; align-items: center; font-size: 1.1rem; margin: 0 0 4px; }
    .ayuda { color: var(--mat-sys-on-surface-variant); margin: 0 0 12px; }
    .fila { display: flex; gap: 8px; align-items: flex-start; flex-wrap: wrap; }
    .error { color: var(--mat-sys-error); }
  `,
})
export class VentanaDevolucion implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly aviso = inject(MatSnackBar);
  private readonly url = `${environment.apiUrl}/plataforma/mi-tienda/devoluciones`;

  protected readonly atajos = [24, 48, 72];
  protected readonly horas = new FormControl<number>(48, {
    nonNullable: true,
    validators: [Validators.required, Validators.min(1), Validators.max(720)],
  });
  protected readonly guardadas = signal<number | null>(null);
  protected readonly guardando = signal(false);
  protected readonly error = signal<string | null>(null);

  ngOnInit(): void {
    this.http.get<{ horas: number }>(this.url).subscribe({
      next: (v) => {
        this.guardadas.set(v.horas);
        this.horas.setValue(v.horas);
      },
      error: (e: HttpErrorResponse) => this.error.set(this.mensaje(e)),
    });
  }

  protected comoTexto(): string {
    const h = Number(this.horas.value);
    if (!h || h < 1) return '';
    if (h % 24 === 0) return h === 24 ? '1 día' : `${h / 24} días`;
    return h === 1 ? '1 hora' : `${h} horas`;
  }

  protected guardar(): void {
    this.guardando.set(true);
    this.http.put<{ horas: number }>(this.url, { horas: Number(this.horas.value) }).subscribe({
      next: (v) => {
        this.guardando.set(false);
        this.guardadas.set(v.horas);
        this.error.set(null);
        this.aviso.open(`Ventana de devolución: ${this.comoTexto()}.`, 'Cerrar', { duration: 4000 });
      },
      error: (e: HttpErrorResponse) => {
        this.guardando.set(false);
        this.error.set(this.mensaje(e));
      },
    });
  }

  private mensaje(e: HttpErrorResponse): string {
    return typeof e.error?.detail === 'string' ? e.error.detail : 'No se pudo guardar la ventana.';
  }
}
