import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatTooltipModule } from '@angular/material/tooltip';

import { AuthService } from '../../../core/services/auth.service';
import { PerfilService, type ErrorPerfil } from '../../../core/services/perfil.service';
import {
  TALLAS_CALZADO,
  TALLAS_INFERIOR,
  TALLAS_SUPERIOR,
  type Direccion,
  type Perfil as PerfilModelo,
  type PerfilEditar,
} from '../../../core/models/perfil.models';
import { Confirmacion, type DatosConfirmacion } from '../../../shared/confirmacion/confirmacion';
import { CambioContrasenaDialogo } from './cambio-contrasena';
import { DireccionFormulario, type DatosDireccion } from './direccion-formulario';

/**
 * CU-04 · Gestionar perfil del cliente — «boundary» PantallaPerfil.
 *
 * Realiza el flujo principal completo y sus tres flujos alternativos. El
 * cliente nunca envía su identificador: el servidor lo resuelve desde el token,
 * de modo que la pantalla no tiene forma de pedir el perfil de otro.
 *
 * Las categorías preferidas del paso 2 quedan fuera del Ciclo 1: dependen de
 * CU-08. Ver §6.11.3 de `docs/06-decisiones-tecnicas.md`.
 */
@Component({
  selector: 'app-perfil',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatSelectModule,
    MatToolbarModule,
    MatTooltipModule,
  ],
  templateUrl: './perfil.html',
  styleUrl: './perfil.scss',
})
export class Perfil {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(PerfilService);
  private readonly auth = inject(AuthService);
  private readonly dialogo = inject(MatDialog);
  private readonly aviso = inject(MatSnackBar);

  protected readonly tallasSuperior = TALLAS_SUPERIOR;
  protected readonly tallasInferior = TALLAS_INFERIOR;
  protected readonly tallasCalzado = TALLAS_CALZADO;

  protected readonly usuario = this.auth.usuario;
  protected readonly cargando = signal(true);
  protected readonly guardando = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly perfil = signal<PerfilModelo | null>(null);
  protected readonly direcciones = signal<Direccion[]>([]);

  protected readonly iniciales = computed(() => {
    const u = this.usuario();
    if (!u) return '';
    return `${u.nombres.charAt(0)}${u.apellidos.charAt(0)}`.toUpperCase();
  });

  protected readonly formulario = this.fb.nonNullable.group({
    nombres: ['', [Validators.required, Validators.maxLength(80)]],
    apellidos: ['', [Validators.required, Validators.maxLength(80)]],
    correo: ['', [Validators.required, Validators.email, Validators.maxLength(120)]],
    documento: ['', [Validators.maxLength(20)]],
    telefono: ['', [Validators.maxLength(20)]],
    talla_superior: ['', [Validators.maxLength(10)]],
    talla_inferior: ['', [Validators.maxLength(10)]],
    talla_calzado: ['', [Validators.maxLength(10)]],
  });

  constructor() {
    this.cargar();
  }

  /** Pasos 1 y 2 del flujo principal. */
  private cargar(): void {
    this.cargando.set(true);
    this.api.obtener().subscribe({
      next: (p) => {
        this.perfil.set(p);
        this.direcciones.set(p.direcciones);
        this.formulario.reset({
          nombres: p.nombres,
          apellidos: p.apellidos,
          correo: p.correo,
          documento: p.documento ?? '',
          telefono: p.telefono ?? '',
          talla_superior: p.talla_superior ?? '',
          talla_inferior: p.talla_inferior ?? '',
          talla_calzado: p.talla_calzado ?? '',
        });
        this.cargando.set(false);
      },
      error: (e: ErrorPerfil) => {
        this.error.set(e.mensaje);
        this.cargando.set(false);
      },
    });
  }

  /** Pasos 3 a 5: solo se envía lo que el cliente realmente cambió. */
  protected guardar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }

    const cambios = this.soloLoModificado();
    if (Object.keys(cambios).length === 0) {
      this.aviso.open('No hay cambios para guardar.', 'Cerrar', { duration: 3500 });
      return;
    }

    this.guardando.set(true);
    this.error.set(null);

    this.api.editar(cambios).subscribe({
      next: (p) => {
        this.guardando.set(false);
        this.perfil.set(p);
        this.direcciones.set(p.direcciones);
        this.formulario.markAsPristine();
        // El nombre y el correo se muestran en la barra superior, que los lee
        // de la sesión: sin volver a pedir /auth/yo, la barra seguiría
        // mostrando los datos viejos hasta la próxima recarga.
        this.auth.restaurarSesion().subscribe();
        this.aviso.open('Perfil actualizado.', 'Cerrar', { duration: 3500 });
      },
      error: (e: ErrorPerfil) => {
        this.guardando.set(false);
        this.error.set(e.mensaje);
        // Excepción E2.
        if (e.tipo === 'correo-duplicado') {
          this.formulario.controls.correo.setErrors({ duplicado: true });
        } else if (e.tipo === 'documento-duplicado') {
          this.formulario.controls.documento.setErrors({ duplicado: true });
        }
      },
    });
  }

  /**
   * Arma el cuerpo del PATCH con los campos que cambiaron respecto del perfil
   * cargado.
   *
   * Enviar el formulario entero funcionaría, pero borraría en el servidor
   * cualquier dato que otra pestaña hubiera modificado mientras tanto. Además,
   * la cadena vacía se manda como null: es la forma de borrar un dato opcional.
   */
  private soloLoModificado(): PerfilEditar {
    const actual = this.perfil();
    if (!actual) return {};

    const v = this.formulario.getRawValue();
    const cambios: PerfilEditar = {};

    if (v.nombres.trim() !== actual.nombres) cambios.nombres = v.nombres.trim();
    if (v.apellidos.trim() !== actual.apellidos) cambios.apellidos = v.apellidos.trim();

    const correo = v.correo.trim().toLowerCase();
    if (correo !== actual.correo) cambios.correo = correo;

    const opcionales = [
      'documento',
      'telefono',
      'talla_superior',
      'talla_inferior',
      'talla_calzado',
    ] as const;

    for (const campo of opcionales) {
      const escrito = v[campo].trim() || null;
      if (escrito !== actual[campo]) cambios[campo] = escrito;
    }

    return cambios;
  }

  protected descartar(): void {
    this.error.set(null);
    const p = this.perfil();
    if (!p) return;
    this.formulario.reset({
      nombres: p.nombres,
      apellidos: p.apellidos,
      correo: p.correo,
      documento: p.documento ?? '',
      telefono: p.telefono ?? '',
      talla_superior: p.talla_superior ?? '',
      talla_inferior: p.talla_inferior ?? '',
      talla_calzado: p.talla_calzado ?? '',
    });
  }

  /** Flujo alternativo 3a. */
  protected agregarDireccion(): void {
    this.dialogo
      .open<DireccionFormulario, DatosDireccion, Direccion[]>(DireccionFormulario, {
        width: '520px',
        maxWidth: '94vw',
        data: { hayDirecciones: this.direcciones().length > 0 },
      })
      .afterClosed()
      .subscribe((lista) => {
        if (!lista) return;
        this.direcciones.set(lista);
        this.aviso.open('Dirección agregada.', 'Cerrar', { duration: 3500 });
      });
  }

  protected marcarPredeterminada(d: Direccion): void {
    this.api.marcarPredeterminada(d.id).subscribe({
      next: (lista) => {
        this.direcciones.set(lista);
        this.aviso.open(`«${d.alias}» es ahora tu dirección predeterminada.`, 'Cerrar', {
          duration: 3500,
        });
      },
      error: (e: ErrorPerfil) => this.aviso.open(e.mensaje, 'Cerrar', { duration: 5000 }),
    });
  }

  /** Flujo alternativo 3b: el caso de uso pide confirmar antes de eliminar. */
  protected eliminarDireccion(d: Direccion): void {
    const datos: DatosConfirmacion = {
      titulo: 'Eliminar dirección',
      mensaje: d.predeterminada
        ? `«${d.alias}» es tu dirección predeterminada. Si la eliminás vas a quedar sin ninguna predeterminada.`
        : `¿Eliminar la dirección «${d.alias}»? Esta acción no se puede deshacer.`,
      confirmar: 'Eliminar',
      peligrosa: true,
    };

    this.dialogo
      .open<Confirmacion, DatosConfirmacion, boolean>(Confirmacion, { data: datos })
      .afterClosed()
      .subscribe((confirmado) => {
        if (!confirmado) return;
        this.api.eliminarDireccion(d.id).subscribe({
          next: (lista) => {
            this.direcciones.set(lista);
            this.aviso.open('Dirección eliminada.', 'Cerrar', { duration: 3500 });
          },
          error: (e: ErrorPerfil) => this.aviso.open(e.mensaje, 'Cerrar', { duration: 5000 }),
        });
      });
  }

  /** Flujo alternativo 3c. */
  protected cambiarContrasena(): void {
    this.dialogo
      .open<CambioContrasenaDialogo, void, boolean>(CambioContrasenaDialogo, {
        width: '480px',
        maxWidth: '94vw',
      })
      .afterClosed()
      .subscribe((cambiada) => {
        if (!cambiada) return;
        // El servidor revocó todas las sesiones, incluida ésta: el token que
        // guarda el navegador ya no sirve. Cerrar sesión acá evita que la
        // próxima petición falle con un 401 sin explicación.
        this.aviso.open('Contraseña actualizada. Iniciá sesión de nuevo.', 'Cerrar', {
          duration: 6000,
        });
        this.auth.cerrarSesion();
      });
  }

  protected salir(): void {
    this.auth.cerrarSesion();
  }
}
