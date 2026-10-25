import { Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';

import {
  PlataformaService,
  type ErrorPlataforma,
} from '../../../core/services/plataforma.service';
import type {
  Plan,
  Suscripcion,
  SuscripcionGuardada,
} from '../../../core/models/plataforma.models';
import { BsPipe, formatoBs } from '../../../shared/bs.pipe';

export interface DatosCambiarPlan {
  empresaId: number;
  empresa: string;
  /** Solo los planes que se ofrecen. */
  planes: Plan[];
  actual: Suscripcion | null;
}

/** Hoy en la zona del navegador, como `YYYY-MM-DD` para el `<input type="date">`. */
function hoyIso(): string {
  const d = new Date();
  const dos = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())}`;
}

function sumarDias(iso: string, dias: number): string {
  const [a, m, d] = iso.split('-').map(Number);
  const fecha = new Date(a, m - 1, d + dias);
  return fecha.toLocaleDateString('es-BO', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

/**
 * CU-03 · asignar o cambiar el plan — «boundary» PantallaSuscripcion.
 *
 * Paso 3: el plan y la fecha de inicio. Antes de confirmar se ve el
 * vencimiento (paso 4) y lo que se cobra en el pago simulado.
 */
@Component({
  selector: 'app-cambiar-plan',
  imports: [
    BsPipe,
    ReactiveFormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatSelectModule,
  ],
  template: `
    <h2 mat-dialog-title class="vb-titulo">
      {{ datos.actual ? 'Cambiar el plan' : 'Asignar un plan' }}
    </h2>
    @if (guardando()) {
      <mat-progress-bar mode="indeterminate" />
    }
    <mat-dialog-content>
      @if (error(); as e) {
        <div class="aviso" role="alert">
          <mat-icon>error_outline</mat-icon>
          <span>{{ e }}</span>
        </div>
      }
      <p class="explicacion">
        {{ datos.empresa }}
        @if (datos.actual; as a) {
          tiene hoy el plan <strong>{{ a.plan_nombre }}</strong>. La suscripción actual se
          cierra y queda en el historial.
        } @else {
          no tiene una suscripción vigente.
        }
      </p>

      <form [formGroup]="formulario" (ngSubmit)="guardar()" id="formulario-cambiar-plan">
        <mat-form-field appearance="outline" class="ancho-completo">
          <mat-label>Plan</mat-label>
          <mat-select formControlName="plan_id">
            @for (p of datos.planes; track p.id) {
              <mat-option [value]="p.id">
                {{ p.nombre }} · {{ p.precio_mensual | bs }} al mes
              </mat-option>
            }
          </mat-select>
          <mat-error>Elija un plan.</mat-error>
        </mat-form-field>

        <mat-form-field appearance="outline" class="ancho-completo">
          <mat-label>Fecha de inicio</mat-label>
          <input matInput type="date" formControlName="inicio" [min]="hoy" />
          <mat-error>No puede ser anterior a hoy.</mat-error>
        </mat-form-field>
      </form>

      @if (resumen(); as r) {
        <ul class="resumen">
          <li>Vence el <strong>{{ r.vencimiento }}</strong> ({{ r.dias }} días).</li>
          <li>Pago simulado: <strong>{{ r.monto }}</strong>.</li>
          @for (l of r.limites; track l) {
            <li>{{ l }}</li>
          }
        </ul>
      }
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button matButton type="button" (click)="ref.close(null)" [disabled]="guardando()">
        Cancelar
      </button>
      <button
        matButton="filled"
        class="vb-boton-marca"
        type="submit"
        form="formulario-cambiar-plan"
        [disabled]="guardando()"
      >
        Confirmar y registrar el pago
      </button>
    </mat-dialog-actions>
  `,
  styleUrls: ['./empresa-formulario.scss'],
  styles: `
    .explicacion { margin: 0 0 1rem; }
    .resumen { margin: 0; line-height: 1.8; color: var(--mat-sys-on-surface-variant); }
    form { padding-top: 0.5rem; }
  `,
})
export class CambiarPlan {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(PlataformaService);

  protected readonly ref = inject(MatDialogRef<CambiarPlan, SuscripcionGuardada | null>);
  protected readonly datos = inject<DatosCambiarPlan>(MAT_DIALOG_DATA);
  protected readonly hoy = hoyIso();

  protected readonly guardando = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly formulario = this.fb.group({
    plan_id: this.fb.control<number | null>(null, Validators.required),
    inicio: this.fb.nonNullable.control(this.hoy, Validators.required),
  });

  private readonly valores = toSignal(this.formulario.valueChanges, {
    initialValue: this.formulario.getRawValue(),
  });

  /** Paso 4, antes de confirmar: el vencimiento, el monto y los límites del plan. */
  protected readonly resumen = computed(() => {
    const { plan_id, inicio } = this.valores();
    const plan = this.datos.planes.find((p) => p.id === plan_id);
    if (!plan || !inicio) return null;
    const limite = (valor: number | null, nombre: string) =>
      valor === null ? `${nombre}: ilimitadas.` : `${nombre}: hasta ${valor}.`;
    return {
      vencimiento: sumarDias(inicio, plan.duracion_dias),
      dias: plan.duracion_dias,
      monto: formatoBs((plan.precio_mensual * plan.duracion_dias) / 30),
      limites: [
        limite(plan.max_sucursales, 'Sucursales activas'),
        limite(plan.max_empleados, 'Empleados activos').replace('ilimitadas', 'ilimitados'),
      ],
    };
  });

  protected guardar(): void {
    const { plan_id, inicio } = this.formulario.getRawValue();
    if (this.formulario.invalid || plan_id === null || inicio < this.hoy) {
      this.formulario.markAllAsTouched();
      if (inicio < this.hoy) this.formulario.controls.inicio.setErrors({ min: true });
      return;
    }
    this.guardando.set(true);
    this.error.set(null);
    this.api.asignarPlan(this.datos.empresaId, { plan_id, inicio }).subscribe({
      next: (r) => this.ref.close(r),
      error: (e: ErrorPlataforma) => {
        this.guardando.set(false);
        this.error.set(e.mensaje);
      },
    });
  }
}
