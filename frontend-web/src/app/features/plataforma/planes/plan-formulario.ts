import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import {
  PlataformaService,
  type ErrorPlataforma,
} from '../../../core/services/plataforma.service';
import type {
  FuncionDePlan,
  Plan,
  PlanGuardado,
  PlanGuardar,
} from '../../../core/models/plataforma.models';

export interface DatosPlan {
  funciones: FuncionDePlan[];
  /** null = crear; con valor = editar. */
  plan: Plan | null;
}

/** Entero positivo o vacío (vacío es ilimitado). */
const LIMITE = [Validators.min(1), Validators.pattern(/^\d*$/)];
/** Un cupo admite el 0: «no incluye». */
const CUPO = [Validators.min(0), Validators.pattern(/^\d*$/)];

/**
 * CU-02 · crear y editar un plan — «boundary» PantallaPlanes.
 *
 * Pasos 3 y 4: el nombre, el precio simulado, la duración, los límites y las
 * funciones. Un límite vacío es ilimitado. El código no se pide: lo arma el
 * servidor con el nombre y no cambia después.
 */
@Component({
  selector: 'app-plan-formulario',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatCheckboxModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
  ],
  templateUrl: './plan-formulario.html',
  styleUrls: ['../empresas/empresa-formulario.scss', './plan-formulario.scss'],
})
export class PlanFormulario {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(PlataformaService);

  protected readonly ref = inject(MatDialogRef<PlanFormulario, PlanGuardado | null>);
  protected readonly datos = inject<DatosPlan>(MAT_DIALOG_DATA);
  protected readonly esEdicion = this.datos.plan !== null;

  protected readonly guardando = signal(false);
  protected readonly error = signal<string | null>(null);

  private readonly plan = this.datos.plan;

  protected readonly formulario = this.fb.group({
    nombre: this.fb.nonNullable.control(this.plan?.nombre ?? '', [
      Validators.required,
      Validators.maxLength(40),
    ]),
    precio_mensual: this.fb.control<number | null>(this.plan?.precio_mensual ?? null, [
      Validators.required,
      Validators.min(0),
    ]),
    duracion_dias: this.fb.control<number | null>(this.plan?.duracion_dias ?? 30, [
      Validators.required,
      Validators.min(1),
      Validators.max(366),
    ]),
    max_sucursales: this.fb.control<number | null>(this.plan?.max_sucursales ?? null, LIMITE),
    max_empleados: this.fb.control<number | null>(this.plan?.max_empleados ?? null, LIMITE),
    cupo_reportes_ia: this.fb.control<number | null>(this.plan?.cupo_reportes_ia ?? null, CUPO),
    cupo_fotos_ia: this.fb.control<number | null>(this.plan?.cupo_fotos_ia ?? null, CUPO),
    bitacora_dias: this.fb.control<number | null>(this.plan?.bitacora_dias ?? null, LIMITE),
  });

  protected readonly elegidas = signal<Set<string>>(new Set(this.plan?.funciones ?? []));

  protected alternar(clave: string, marcada: boolean): void {
    const nuevas = new Set(this.elegidas());
    if (marcada) nuevas.add(clave);
    else nuevas.delete(clave);
    this.elegidas.set(nuevas);
  }

  protected guardar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }
    const v = this.formulario.getRawValue();
    // Un campo numérico vacío llega como null o como '': los dos son «ilimitado».
    const numero = (x: number | string | null) => (x === null || x === '' ? null : Number(x));
    const datos: PlanGuardar = {
      nombre: v.nombre.trim(),
      precio_mensual: Number(v.precio_mensual),
      duracion_dias: Number(v.duracion_dias),
      max_sucursales: numero(v.max_sucursales),
      max_empleados: numero(v.max_empleados),
      cupo_reportes_ia: numero(v.cupo_reportes_ia),
      cupo_fotos_ia: numero(v.cupo_fotos_ia),
      bitacora_dias: numero(v.bitacora_dias),
      // En el orden de la lista, no en el que se marcaron.
      funciones: this.datos.funciones.map((f) => f.clave).filter((c) => this.elegidas().has(c)),
    };

    this.guardando.set(true);
    this.error.set(null);
    const pedido = this.esEdicion
      ? this.api.editarPlan(this.plan!.id, datos)
      : this.api.crearPlan(datos);
    pedido.subscribe({
      next: (guardado) => {
        this.guardando.set(false);
        this.ref.close(guardado);
      },
      error: (e: ErrorPlataforma) => {
        this.guardando.set(false);
        this.error.set(e.mensaje);
        // Alternativo 4a: se marca el campo.
        if (e.tipo === 'nombre-repetido') {
          this.formulario.controls.nombre.setErrors({ repetido: true });
        }
      },
    });
  }
}
