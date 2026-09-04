import { Component, inject, signal } from '@angular/core';
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
  type FormControl,
} from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import { AuthLayout } from '../auth-layout/auth-layout';
import { AuthService, type ErrorRegistro } from '../../../core/services/auth.service';
import {
  CONTRASENA_LONGITUD_MINIMA,
  CONTRASENA_PATRON,
} from '../../../core/models/auth.models';

/**
 * CU-01 · Registrar cliente — «boundary» FormularioRegistro.
 *
 * Realiza los pasos 1 a 3 y 8 del flujo principal, el flujo alternativo 4a y
 * el mostrado de la excepción E1. La creación efectiva ocurre en el backend.
 */
@Component({
  selector: 'app-registro',
  imports: [
    ReactiveFormsModule,
    RouterLink,
    AuthLayout,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
  ],
  templateUrl: './registro.html',
  styleUrl: './registro.scss',
})
export class Registro {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  protected readonly longitudMinima = CONTRASENA_LONGITUD_MINIMA;

  /** Deshabilita el formulario mientras la petición está en curso. */
  protected readonly enviando = signal(false);

  /** Mensaje de la excepción E1 o de un fallo de sistema. */
  protected readonly error = signal<ErrorRegistro | null>(null);

  /** Paso 8: se muestra la confirmación en lugar del formulario. */
  protected readonly registrado = signal(false);

  /** Oculta o revela la contraseña escrita. */
  protected readonly verContrasena = signal(false);

  /**
   * Paso 2: los campos que pide el caso de uso, en ese orden.
   * Documento y teléfono son opcionales — en el esquema físico `documento` y
   * `telefono` de la tabla `cliente` aceptan NULL.
   */
  protected readonly formulario = this.fb.nonNullable.group({
    nombres: ['', [Validators.required, Validators.maxLength(80)]],
    apellidos: ['', [Validators.required, Validators.maxLength(80)]],
    documento: ['', [Validators.maxLength(20)]],
    telefono: ['', [Validators.maxLength(20)]],
    correo: ['', [Validators.required, Validators.email, Validators.maxLength(120)]],
    contrasena: [
      '',
      [
        Validators.required,
        Validators.minLength(CONTRASENA_LONGITUD_MINIMA),
        Validators.pattern(CONTRASENA_PATRON),
      ],
    ],
  });

  protected control(nombre: keyof typeof this.formulario.controls): FormControl<string> {
    return this.formulario.controls[nombre];
  }

  /** Paso 3: el cliente confirma. */
  protected enviar(): void {
    // Flujo alternativo 4a: se marcan todos los campos para que se vean los
    // errores, y NO se limpia nada de lo ya escrito.
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }

    const valores = this.formulario.getRawValue();
    this.enviando.set(true);
    this.error.set(null);

    this.auth
      .registrar({
        nombres: valores.nombres.trim(),
        apellidos: valores.apellidos.trim(),
        // Cadena vacía y «sin dato» no son lo mismo para una columna UNIQUE:
        // dos cadenas vacías chocan entre sí, dos NULL no.
        documento: valores.documento.trim() || null,
        telefono: valores.telefono.trim() || null,
        correo: valores.correo.trim().toLowerCase(),
        contrasena: valores.contrasena,
      })
      .subscribe({
        next: () => {
          // Paso 8: registro exitoso, se invita a iniciar sesión.
          this.enviando.set(false);
          this.registrado.set(true);
        },
        error: (error: ErrorRegistro) => {
          this.enviando.set(false);
          this.error.set(error);

          // Excepción E1: se señala el campo culpable sin borrar el formulario.
          if (error.tipo === 'correo-duplicado') {
            this.control('correo').setErrors({ duplicado: true });
          } else if (error.tipo === 'documento-duplicado') {
            this.control('documento').setErrors({ duplicado: true });
          }
        },
      });
  }

  protected irALogin(): void {
    this.router.navigate(['/login']);
  }
}
