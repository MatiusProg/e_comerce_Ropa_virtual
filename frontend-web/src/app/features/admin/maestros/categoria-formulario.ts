import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';

import { MaestrosService, type ErrorMaestros } from '../../../core/services/maestros.service';
import {
  aplanarCategorias,
  idsProhibidosComoPadre,
  type Categoria,
  type CategoriaEditar,
  type CategoriaPlana,
} from '../../../core/models/maestros.models';

export interface DatosCategoria {
  arbol: Categoria[];
  /** null = alta; con valor = edición (flujo alternativo 3a). */
  categoria: Categoria | null;
}

/**
 * Alta y edición de una categoría (pasos 4 a 7 y flujo alternativo 3a).
 *
 * El selector de categoría madre **no ofrece** ni la propia categoría ni su
 * descendencia: elegir cualquiera de ellas formaría el ciclo de la excepción
 * E2. Prevenirlo en la interfaz es más claro que dejar elegir y mostrar el
 * error después — pero el servidor lo valida igual, porque la interfaz no es
 * la que decide.
 */
@Component({
  selector: 'app-categoria-formulario',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatSelectModule,
  ],
  templateUrl: './categoria-formulario.html',
  styleUrl: './categoria-formulario.scss',
})
export class CategoriaFormulario {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(MaestrosService);

  protected readonly ref = inject(MatDialogRef<CategoriaFormulario, boolean>);
  protected readonly datos = inject<DatosCategoria>(MAT_DIALOG_DATA);

  protected readonly esEdicion = this.datos.categoria !== null;
  protected readonly guardando = signal(false);
  protected readonly error = signal<string | null>(null);

  /** Categorías que se pueden elegir como madre, con su profundidad. */
  protected readonly candidatas = computed<CategoriaPlana[]>(() => {
    const todas = aplanarCategorias(this.datos.arbol);
    const actual = this.datos.categoria;
    if (!actual) return todas;

    const prohibidos = idsProhibidosComoPadre(this.datos.arbol, actual.id);
    return todas.filter((c) => !prohibidos.has(c.categoria.id));
  });

  protected readonly formulario = this.fb.nonNullable.group({
    nombre: [
      this.datos.categoria?.nombre ?? '',
      [Validators.required, Validators.maxLength(60)],
    ],
    categoria_padre_id: [this.datos.categoria?.categoria_padre_id ?? (null as number | null)],
    orden: [this.datos.categoria?.orden ?? 0, [Validators.required, Validators.min(0)]],
  });

  /** Sangría del selector, para que la jerarquía se vea en una lista plana. */
  protected sangria(nivel: number): string {
    return '  '.repeat(nivel);
  }

  protected guardar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }

    const v = this.formulario.getRawValue();
    this.guardando.set(true);
    this.error.set(null);

    const alTerminar = {
      next: () => {
        this.guardando.set(false);
        this.ref.close(true);
      },
      error: (e: ErrorMaestros) => {
        this.guardando.set(false);
        this.error.set(e.mensaje);
        // Excepción E1: el caso de uso pide señalar el campo.
        if (e.tipo === 'duplicado') {
          this.formulario.controls.nombre.setErrors({ duplicado: true });
        } else if (e.tipo === 'ciclo') {
          this.formulario.controls.categoria_padre_id.setErrors({ ciclo: true });
        }
      },
    };

    if (this.esEdicion) {
      // `categoria_padre_id` viaja SIEMPRE, incluso en null: enviarlo en null
      // es lo que convierte la categoría en raíz. Omitirlo la dejaría donde
      // está, que es una intención distinta.
      const cambios: CategoriaEditar = {
        nombre: v.nombre.trim(),
        categoria_padre_id: v.categoria_padre_id,
        orden: v.orden,
      };
      this.api.editarCategoria(this.datos.categoria!.id, cambios).subscribe(alTerminar);
      return;
    }

    this.api
      .crearCategoria({
        nombre: v.nombre.trim(),
        categoria_padre_id: v.categoria_padre_id,
        orden: v.orden,
        activa: true,
      })
      .subscribe(alTerminar);
  }
}
