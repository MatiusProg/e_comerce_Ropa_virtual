import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators, type FormControl } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import { AuthLayout } from '../auth-layout/auth-layout';
import { AuthService, type ErrorLogin } from '../../../core/services/auth.service';

/**
 * CU-02 · Iniciar sesión — «boundary» FormularioLogin.
 *
 * Realiza el flujo principal y muestra las excepciones E1 (credenciales
 * inválidas) y E2 (cuenta desactivada). El flujo alternativo 6a —volver a la
 * ruta que se quiso abrir sin sesión— se resuelve con el parámetro `destino`
 * que dejan la guarda y el interceptor.
 */
@Component({
  selector: 'app-login',
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
  templateUrl: './login.html',
  styleUrl: './login.scss',
})
export class Login {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);

  protected readonly enviando = signal(false);
  protected readonly error = signal<ErrorLogin | null>(null);
  protected readonly verContrasena = signal(false);

  protected readonly formulario = this.fb.nonNullable.group({
    correo: ['', [Validators.required, Validators.email, Validators.maxLength(120)]],
    contrasena: ['', [Validators.required]],
  });

  protected control(nombre: keyof typeof this.formulario.controls): FormControl<string> {
    return this.formulario.controls[nombre];
  }

  protected enviar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }

    const { correo, contrasena } = this.formulario.getRawValue();
    this.enviando.set(true);
    this.error.set(null);

    this.auth.iniciarSesion({ correo: correo.trim().toLowerCase(), contrasena }).subscribe({
      next: () => {
        this.enviando.set(false);
        // Flujo alternativo 6a: si se llegó acá por intentar abrir otra ruta,
        // se vuelve a ella; si no, al área que corresponde al rol.
        const destino = this.ruta.snapshot.queryParamMap.get('destino');
        this.router.navigateByUrl(destino || this.auth.inicioDelRol());
      },
      error: (e: ErrorLogin) => {
        this.enviando.set(false);
        this.error.set(e);
        // La contraseña se limpia, el correo no: reescribir el correo en cada
        // intento fallido es molesto y no aporta nada.
        this.control('contrasena').reset();
      },
    });
  }
}
