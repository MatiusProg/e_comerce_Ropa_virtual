import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators, type FormControl } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import { AuthLayout } from '../auth-layout/auth-layout';
import { AuthService, type ErrorRecuperacion } from '../../../core/services/auth.service';

/**
 * CU-41 · Recuperar contraseña — «boundary» FormularioOlvideContrasena.
 *
 * Realiza los pasos 1 y 2 del flujo principal: pedir el correo y solicitar el
 * enlace. Los pasos 6 a 9 ocurren en la otra pantalla, a la que se llega desde
 * el correo.
 *
 * ESTA PANTALLA NO SABE SI LA CUENTA EXISTE, y no es una limitación: el
 * servidor responde lo mismo en los dos casos, a propósito. Si acá se pudiera
 * distinguir, esta pantalla —pública y sin sesión— sería una forma de
 * averiguar qué correos están registrados en la tienda, probándolos de a uno.
 * Por eso el acuse que se muestra lo redacta el servidor y dice «si el correo
 * corresponde a una cuenta», en condicional.
 */
@Component({
  selector: 'app-olvide',
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
  templateUrl: './olvide.html',
  styleUrl: './olvide.scss',
})
export class Olvide {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);

  protected readonly enviando = signal(false);
  protected readonly error = signal<ErrorRecuperacion | null>(null);

  /** El acuse del servidor. Reemplaza al formulario cuando llega. */
  protected readonly acuse = signal<string | null>(null);

  protected readonly formulario = this.fb.nonNullable.group({
    correo: ['', [Validators.required, Validators.email, Validators.maxLength(120)]],
  });

  protected control(nombre: keyof typeof this.formulario.controls): FormControl<string> {
    return this.formulario.controls[nombre];
  }

  protected enviar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }

    const { correo } = this.formulario.getRawValue();
    this.enviando.set(true);
    this.error.set(null);

    this.auth.solicitarRecuperacion({ correo: correo.trim().toLowerCase() }).subscribe({
      next: (r) => {
        this.enviando.set(false);
        this.acuse.set(r.mensaje);
      },
      error: (e: ErrorRecuperacion) => {
        this.enviando.set(false);
        this.error.set(e);
      },
    });
  }
}
