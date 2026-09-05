import { Component, inject, signal } from '@angular/core';
import {
  AbstractControl,
  FormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import { PerfilService, type ErrorPerfil } from '../../../core/services/perfil.service';
import {
  CONTRASENA_LONGITUD_MINIMA,
  CONTRASENA_PATRON,
} from '../../../core/models/auth.models';

/**
 * Verifica que la contraseña nueva se haya escrito igual las dos veces y que
 * sea distinta de la actual.
 *
 * Es la misma regla que aplica el servidor en `CambioContrasenaIn`: acá se
 * repite para avisar antes de enviar, no para reemplazarla.
 */
function contrasenasCoherentes(grupo: AbstractControl): ValidationErrors | null {
  const actual = grupo.get('contrasena_actual')?.value ?? '';
  const nueva = grupo.get('contrasena_nueva')?.value ?? '';
  const repetida = grupo.get('contrasena_repetida')?.value ?? '';

  if (!nueva || !repetida) return null;
  if (nueva !== repetida) return { noCoinciden: true };
  if (actual && nueva === actual) return { sinCambio: true };
  return null;
}

/**
 * Cambio de contraseña del propio cliente — flujo alternativo 3c del CU-04.
 *
 * Al confirmarlo el servidor revoca todas las sesiones abiertas, incluida la
 * que hizo la petición. Por eso el diálogo devuelve `true` y la pantalla que lo
 * abrió se encarga de cerrar sesión: seguir navegando con un token ya revocado
 * solo produciría un 401 sin explicación en la siguiente petición.
 */
@Component({
  selector: 'app-cambio-contrasena',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
  ],
  templateUrl: './cambio-contrasena.html',
  styleUrl: './cambio-contrasena.scss',
})
export class CambioContrasenaDialogo {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(PerfilService);

  protected readonly ref = inject(MatDialogRef<CambioContrasenaDialogo, boolean>);

  protected readonly longitudMinima = CONTRASENA_LONGITUD_MINIMA;
  protected readonly guardando = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly verActual = signal(false);
  protected readonly verNueva = signal(false);

  protected readonly formulario = this.fb.nonNullable.group(
    {
      contrasena_actual: ['', [Validators.required]],
      contrasena_nueva: [
        '',
        [
          Validators.required,
          Validators.minLength(CONTRASENA_LONGITUD_MINIMA),
          Validators.pattern(CONTRASENA_PATRON),
        ],
      ],
      contrasena_repetida: ['', [Validators.required]],
    },
    { validators: contrasenasCoherentes },
  );

  protected guardar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }

    this.guardando.set(true);
    this.error.set(null);

    this.api.cambiarContrasena(this.formulario.getRawValue()).subscribe({
      next: () => {
        this.guardando.set(false);
        this.ref.close(true);
      },
      error: (e: ErrorPerfil) => {
        this.guardando.set(false);
        this.error.set(e.mensaje);
        // Excepción E1: el flujo devuelve el control al paso 3c, así que el
        // diálogo NO se cierra; solo se marca el campo que falló.
        if (e.tipo === 'contrasena-actual') {
          this.formulario.controls.contrasena_actual.setErrors({ incorrecta: true });
        }
      },
    });
  }
}
