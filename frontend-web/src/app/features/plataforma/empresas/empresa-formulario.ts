import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';

import {
  PlataformaService,
  type ErrorPlataforma,
} from '../../../core/services/plataforma.service';
import {
  PATRON_SLUG,
  type Empresa,
  type EmpresaCreada,
  type PlanOferta,
} from '../../../core/models/plataforma.models';
import type { Ciudad } from '../../../core/models/organizacion.models';

export interface DatosEmpresa {
  planes: PlanOferta[];
  ciudades: Ciudad[];
  /** null = alta (pasos 3 a 6); con valor = edición (alternativo 3a). */
  empresa: Empresa | null;
}

/** Del nombre de la empresa a un slug válido: «Moda Andina» → «moda-andina». */
function sugerirSlug(nombre: string): string {
  return nombre
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 40);
}

/**
 * CU-01 · alta y edición de una empresa — «boundary» PantallaEmpresas.
 *
 * El alta pide, en un solo formulario, todo lo que el paso 5 crea en una
 * transacción: la empresa, su plan, su sucursal principal y su administrador.
 * En la edición el slug no aparece: no se cambia después del alta (RN-14).
 */
@Component({
  selector: 'app-empresa-formulario',
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
  templateUrl: './empresa-formulario.html',
  styleUrl: './empresa-formulario.scss',
})
export class EmpresaFormulario {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(PlataformaService);

  protected readonly ref = inject(MatDialogRef<EmpresaFormulario, Empresa | EmpresaCreada | null>);
  protected readonly datos = inject<DatosEmpresa>(MAT_DIALOG_DATA);
  protected readonly esEdicion = this.datos.empresa !== null;

  protected readonly guardando = signal(false);
  protected readonly error = signal<string | null>(null);
  /** Mientras el slug no se toque a mano, sigue al nombre. */
  private slugEditado = this.esEdicion;

  private readonly soloAlta = (validadores: any[]) => (this.esEdicion ? [] : validadores);

  protected readonly formulario = this.fb.nonNullable.group({
    nombre: [this.datos.empresa?.nombre ?? '', [Validators.required, Validators.maxLength(120)]],
    razon_social: [this.datos.empresa?.razon_social ?? '', [Validators.maxLength(160)]],
    nit: [this.datos.empresa?.nit ?? '', [Validators.maxLength(30)]],
    correo_contacto: [this.datos.empresa?.correo_contacto ?? '', [Validators.email]],
    slug: ['', this.soloAlta([Validators.required, Validators.pattern(PATRON_SLUG)])],
    plan_codigo: [this.datos.planes[0]?.codigo ?? '', this.soloAlta([Validators.required])],
    ciudad_id: [null as number | null, this.soloAlta([Validators.required])],
    sucursal_nombre: ['Casa matriz', this.soloAlta([Validators.required])],
    sucursal_direccion: ['', this.soloAlta([Validators.required])],
    admin_correo: ['', this.soloAlta([Validators.required, Validators.email])],
    admin_nombres: ['', this.soloAlta([Validators.required])],
    admin_apellidos: ['', this.soloAlta([Validators.required])],
  });

  constructor() {
    this.formulario.controls.nombre.valueChanges.subscribe((nombre) => {
      if (!this.slugEditado) {
        this.formulario.controls.slug.setValue(sugerirSlug(nombre), { emitEvent: false });
      }
    });
  }

  protected tocarSlug(): void {
    this.slugEditado = true;
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
      next: (empresa: Empresa | EmpresaCreada) => {
        this.guardando.set(false);
        this.ref.close(empresa);
      },
      error: (e: ErrorPlataforma) => {
        this.guardando.set(false);
        this.error.set(e.mensaje);
        // Alternativo 4a: se marca el campo que causó el conflicto.
        if (e.tipo === 'slug-repetido') {
          this.formulario.controls.slug.setErrors({ repetido: true });
        }
        if (e.tipo === 'correo-repetido') {
          this.formulario.controls.admin_correo.setErrors({ repetido: true });
        }
      },
    };

    const comunes = {
      nombre: v.nombre.trim(),
      razon_social: v.razon_social.trim() || null,
      nit: v.nit.trim() || null,
      correo_contacto: v.correo_contacto.trim() || null,
    };

    if (this.esEdicion) {
      this.api.editarEmpresa(this.datos.empresa!.id, comunes).subscribe(alTerminar);
      return;
    }
    this.api
      .crearEmpresa({
        ...comunes,
        slug: v.slug.trim(),
        plan_codigo: v.plan_codigo,
        sucursal: {
          ciudad_id: v.ciudad_id!,
          nombre: v.sucursal_nombre.trim(),
          direccion: v.sucursal_direccion.trim(),
        },
        administrador: {
          correo: v.admin_correo.trim().toLowerCase(),
          nombres: v.admin_nombres.trim(),
          apellidos: v.admin_apellidos.trim(),
        },
      })
      .subscribe(alTerminar);
  }
}
