import { Component, OnInit, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { DatePipe } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatMenuModule } from '@angular/material/menu';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';

import { AuthService } from '../../../core/services/auth.service';
import type { Rol } from '../../../core/models/auth.models';
import { UsuariosService, type ErrorUsuarios } from '../../../core/services/usuarios.service';
import {
  ETIQUETA_ROL,
  type PaginaUsuarios,
  type RolAsignable,
  type UsuarioResumen,
} from '../../../core/models/usuarios.models';
import { Confirmacion, type DatosConfirmacion } from '../../../shared/confirmacion/confirmacion';
import { UsuarioFormulario, type DatosFormulario } from './usuario-formulario';

/**
 * CU-03 · Gestionar usuarios y roles — «boundary» PantallaUsuarios.
 *
 * Realiza el paso 2 (listado con búsqueda, filtros y paginación) y ofrece las
 * acciones de los flujos alternativos 3a (editar), 3b (activar/desactivar) y
 * 3c (eliminar).
 */
@Component({
  selector: 'app-usuarios',
  imports: [
    ReactiveFormsModule,
    DatePipe,
    MatButtonModule,
    MatCardModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatMenuModule,
    MatPaginatorModule,
    MatProgressBarModule,
    MatSelectModule,
    MatTableModule,
    MatTooltipModule,
  ],
  templateUrl: './usuarios.html',
  styleUrl: './usuarios.scss',
})
export class Usuarios implements OnInit {
  private readonly api = inject(UsuariosService);
  private readonly auth = inject(AuthService);
  private readonly dialogo = inject(MatDialog);
  private readonly aviso = inject(MatSnackBar);

  protected readonly columnas = ['usuario', 'rol', 'sucursal', 'estado', 'alta', 'acciones'];
  protected readonly etiquetaRol = ETIQUETA_ROL;

  /**
   * Nombre legible de un rol.
   *
   * Es un método y no un acceso directo al mapa porque las filas de
   * `mat-table` llegan a la plantilla sin tipo, y en modo estricto no pueden
   * indexar un `Record<Rol, string>`.
   */
  protected nombreRol(rol: string): string {
    return ETIQUETA_ROL[rol as Rol] ?? rol;
  }

  protected readonly cargando = signal(false);
  protected readonly pagina = signal<PaginaUsuarios | null>(null);
  protected readonly roles = signal<RolAsignable[]>([]);

  /** Identificador del propio administrador, para no ofrecerle acciones sobre sí mismo (E3). */
  protected readonly miId = signal<number | null>(null);

  protected readonly busqueda = new FormControl('', { nonNullable: true });
  protected readonly filtroRol = new FormControl<string>('', { nonNullable: true });
  protected readonly filtroEstado = new FormControl<string>('', { nonNullable: true });

  private indice = 0;
  private tamano = 10;

  ngOnInit(): void {
    this.miId.set(this.auth.usuario()?.id ?? null);
    this.api.roles().subscribe({ next: (r) => this.roles.set(r) });

    // El debounce evita disparar una consulta por cada tecla.
    this.busqueda.valueChanges
      .pipe(debounceTime(350), distinctUntilChanged())
      .subscribe(() => this.reiniciarYCargar());

    this.filtroRol.valueChanges.subscribe(() => this.reiniciarYCargar());
    this.filtroEstado.valueChanges.subscribe(() => this.reiniciarYCargar());

    this.cargar();
  }

  private reiniciarYCargar(): void {
    // Cambiar un filtro con la página 3 abierta dejaría una tabla vacía sin
    // explicación: se vuelve siempre a la primera.
    this.indice = 0;
    this.cargar();
  }

  protected cargar(): void {
    this.cargando.set(true);
    const estado = this.filtroEstado.value;
    this.api
      .listar({
        busqueda: this.busqueda.value || undefined,
        rol: this.filtroRol.value || undefined,
        activo: estado === '' ? undefined : estado === 'activos',
        pagina: this.indice + 1,
        tamano: this.tamano,
      })
      .subscribe({
        next: (p) => {
          this.pagina.set(p);
          this.cargando.set(false);
        },
        error: (e: ErrorUsuarios) => {
          this.cargando.set(false);
          this.mostrar(e.mensaje);
        },
      });
  }

  protected paginar(evento: PageEvent): void {
    this.indice = evento.pageIndex;
    this.tamano = evento.pageSize;
    this.cargar();
  }

  protected limpiarFiltros(): void {
    this.busqueda.setValue('', { emitEvent: false });
    this.filtroRol.setValue('', { emitEvent: false });
    this.filtroEstado.setValue('', { emitEvent: false });
    this.reiniciarYCargar();
  }

  protected get hayFiltros(): boolean {
    return !!(this.busqueda.value || this.filtroRol.value || this.filtroEstado.value);
  }

  // --- Acciones ----------------------------------------------------------

  protected nuevo(): void {
    this.abrirFormulario({ roles: this.roles(), usuario: null });
  }

  /** Flujo alternativo 3a. */
  protected editar(usuario: UsuarioResumen): void {
    this.abrirFormulario({ roles: this.roles(), usuario });
  }

  private abrirFormulario(datos: DatosFormulario): void {
    this.dialogo
      .open(UsuarioFormulario, { data: datos, width: '620px', maxWidth: '95vw' })
      .afterClosed()
      .subscribe((guardado) => {
        if (guardado) {
          this.mostrar(
            datos.usuario ? 'Usuario actualizado.' : 'Usuario creado correctamente.',
          );
          this.cargar();
        }
      });
  }

  /** Flujo alternativo 3b: el caso de uso pide confirmación explícita. */
  protected cambiarEstado(usuario: UsuarioResumen): void {
    const desactivando = usuario.activo;
    const datos: DatosConfirmacion = {
      titulo: desactivando ? 'Desactivar cuenta' : 'Activar cuenta',
      mensaje: desactivando
        ? `${usuario.nombres} ${usuario.apellidos} no podrá volver a iniciar sesión, y sus sesiones abiertas se cerrarán de inmediato.`
        : `${usuario.nombres} ${usuario.apellidos} volverá a poder iniciar sesión.`,
      confirmar: desactivando ? 'Desactivar' : 'Activar',
      peligrosa: desactivando,
    };

    this.confirmar(datos, () =>
      this.api.cambiarEstado(usuario.id, !usuario.activo).subscribe({
        next: () => {
          this.mostrar(desactivando ? 'Cuenta desactivada.' : 'Cuenta activada.');
          this.cargar();
        },
        error: (e: ErrorUsuarios) => this.mostrar(e.mensaje),
      }),
    );
  }

  /** Flujo alternativo 3c. */
  protected eliminar(usuario: UsuarioResumen): void {
    const datos: DatosConfirmacion = {
      titulo: 'Eliminar usuario',
      mensaje: `Se eliminará la cuenta de ${usuario.nombres} ${usuario.apellidos}. Esta acción no se puede deshacer.`,
      confirmar: 'Eliminar',
      peligrosa: true,
    };

    this.confirmar(datos, () =>
      this.api.eliminar(usuario.id).subscribe({
        next: () => {
          this.mostrar('Usuario eliminado.');
          this.cargar();
        },
        error: (e: ErrorUsuarios) => {
          // El caso de uso dice: si no se puede eliminar, ofrecer desactivar
          // en su lugar. Eso es exactamente lo que se hace acá.
          if (e.tipo === 'no-eliminable' && usuario.activo) {
            this.ofrecerDesactivar(usuario, e.mensaje);
          } else {
            this.mostrar(e.mensaje);
          }
        },
      }),
    );
  }

  private ofrecerDesactivar(usuario: UsuarioResumen, motivo: string): void {
    this.confirmar(
      {
        titulo: 'No se puede eliminar',
        mensaje: `${motivo} ¿Desea desactivarla?`,
        confirmar: 'Desactivar',
        peligrosa: true,
      },
      () =>
        this.api.cambiarEstado(usuario.id, false).subscribe({
          next: () => {
            this.mostrar('Cuenta desactivada.');
            this.cargar();
          },
          error: (e: ErrorUsuarios) => this.mostrar(e.mensaje),
        }),
    );
  }

  private confirmar(datos: DatosConfirmacion, accion: () => void): void {
    this.dialogo
      .open(Confirmacion, { data: datos, width: '460px', maxWidth: '95vw' })
      .afterClosed()
      .subscribe((si) => si && accion());
  }

  private mostrar(mensaje: string): void {
    this.aviso.open(mensaje, 'Cerrar', { duration: 5000 });
  }
}
