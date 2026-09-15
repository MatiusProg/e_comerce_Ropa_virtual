import { Component, inject, signal } from '@angular/core';
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
  type AbstractControl,
  type FormControl,
  type ValidationErrors,
} from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import { AuthLayout } from '../auth-layout/auth-layout';
import { AuthService, type ErrorRecuperacion } from '../../../core/services/auth.service';
import {
  CONTRASENA_LONGITUD_MINIMA,
  CONTRASENA_PATRON,
} from '../../../core/models/auth.models';

/**
 * Las dos contraseñas tienen que coincidir.
 *
 * Se valida acá además de en el servidor —que también lo hace— porque
 * descubrirlo recién al enviar, con un 422 genérico, no le dice a nadie cuál de
 * los dos campos reescribir.
 */
function contrasenasCoinciden(grupo: AbstractControl): ValidationErrors | null {
  const nueva = grupo.get('contrasena_nueva')?.value;
  const repetida = grupo.get('contrasena_repetida')?.value;
  return nueva && repetida && nueva !== repetida ? { noCoinciden: true } : null;
}

/**
 * CU-41 · Recuperar contraseña — «boundary» FormularioContrasenaNueva.
 *
 * Realiza los pasos 6 a 9: se llega desde el enlace del correo, se elige la
 * contraseña nueva y se vuelve a iniciar sesión.
 *
 * EL TOKEN LLEGA POR LA URL Y SE MANDA POR EL CUERPO. No hay otra forma de
 * llevarlo en un enlace, pero sí de devolverlo: ponerlo en la cadena de
 * consulta de la llamada lo escribiría en el registro de accesos del servidor,
 * y mientras vive ES la credencial de la cuenta.
 *
 * Tampoco se muestra en pantalla. Alguien que abra el enlace donde no debe ya
 * tiene el token en la barra de direcciones; repetirlo en el cuerpo de la
 * página solo agrega un lugar más de donde leerlo —una captura, alguien
 * mirando— sin darle nada a quien sí es el dueño de la cuenta.
 */
@Component({
  selector: 'app-restablecer',
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
  templateUrl: './restablecer.html',
  styleUrl: './restablecer.scss',
})
export class Restablecer {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);

  protected readonly longitudMinima = CONTRASENA_LONGITUD_MINIMA;

  /** El token del enlace. Cadena vacía si alguien entró a mano a esta ruta. */
  private readonly token = this.ruta.snapshot.paramMap.get('token') ?? '';

  protected readonly enviando = signal(false);
  protected readonly error = signal<ErrorRecuperacion | null>(null);

  /** Paso 9: la contraseña quedó cambiada. */
  protected readonly listo = signal(false);

  protected readonly verContrasena = signal(false);

  protected readonly formulario = this.fb.nonNullable.group(
    {
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
    { validators: contrasenasCoinciden },
  );

  protected control(nombre: keyof typeof this.formulario.controls): FormControl<string> {
    return this.formulario.controls[nombre];
  }

  /** Sin token no hay nada que canjear: se muestra el aviso, no el formulario. */
  protected get sinToken(): boolean {
    return this.token.length === 0;
  }

  protected enviar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }

    const { contrasena_nueva, contrasena_repetida } = this.formulario.getRawValue();
    this.enviando.set(true);
    this.error.set(null);

    this.auth
      .confirmarRecuperacion({
        token: this.token,
        contrasena_nueva,
        contrasena_repetida,
      })
      .subscribe({
        next: () => {
          this.enviando.set(false);
          this.listo.set(true);
        },
        error: (e: ErrorRecuperacion) => {
          this.enviando.set(false);
          this.error.set(e);
          // Las dos se limpian: si el enlace ya no sirve no hay nada que
          // reintentar acá, y si el error fue de red conviene reescribirlas.
          this.formulario.reset();
        },
      });
  }

  protected irAlLogin(): void {
    this.router.navigate(['/login']);
  }
}
