import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Observable } from 'rxjs';

import { MaestrosService, type ErrorMaestros } from '../../../core/services/maestros.service';
import {
  aplanarCategorias,
  type Categoria,
  type CategoriaPlana,
  type Color,
  type Talla,
} from '../../../core/models/maestros.models';
import { Confirmacion, type DatosConfirmacion } from '../../../shared/confirmacion/confirmacion';
import { CategoriaFormulario, type DatosCategoria } from './categoria-formulario';
import { ColorFormulario, type DatosColor } from './color-formulario';
import { TallaFormulario, type DatosTalla } from './talla-formulario';

/**
 * CU-08 · Gestionar categorías, tallas y colores — «boundary» PantallaMaestros.
 *
 * Las tres entidades viven en una sola pantalla con pestañas porque así las
 * plantea el caso de uso: el paso 1 entra a *los maestros del catálogo* y
 * elige, y los flujos 1a y 1b son las otras dos pestañas. Separarlas en tres
 * rutas obligaría a volver al menú para pasar de una a otra.
 */
@Component({
  selector: 'app-maestros',
  imports: [
    MatButtonModule,
    MatCardModule,
    MatDialogModule,
    MatIconModule,
    MatMenuModule,
    MatProgressBarModule,
    MatTableModule,
    MatTabsModule,
    MatTooltipModule,
  ],
  templateUrl: './maestros.html',
  styleUrl: './maestros.scss',
})
export class Maestros implements OnInit {
  private readonly api = inject(MaestrosService);
  private readonly dialogo = inject(MatDialog);
  private readonly aviso = inject(MatSnackBar);

  protected readonly columnasCategorias = ['nombre', 'orden', 'estado', 'acciones'];
  protected readonly columnasTallas = ['tipo', 'codigo', 'orden', 'estado', 'acciones'];
  protected readonly columnasColores = ['muestra', 'nombre', 'hexadecimal', 'estado', 'acciones'];

  protected readonly cargando = signal(false);
  protected readonly categorias = signal<Categoria[]>([]);
  protected readonly tallas = signal<Talla[]>([]);
  protected readonly colores = signal<Color[]>([]);

  /**
   * El árbol aplanado, con la profundidad de cada nodo.
   *
   * `mat-table` necesita una lista; la sangría de la primera columna es la que
   * conserva la jerarquía a la vista.
   */
  protected readonly categoriasPlanas = computed<CategoriaPlana[]>(() =>
    aplanarCategorias(this.categorias()),
  );

  ngOnInit(): void {
    this.cargarTodo();
  }

  private cargarTodo(): void {
    this.cargarCategorias();
    this.cargarTallas();
    this.cargarColores();
  }

  private cargarCategorias(): void {
    this.cargando.set(true);
    this.api.categorias().subscribe({
      next: (arbol) => {
        this.categorias.set(arbol);
        this.cargando.set(false);
      },
      error: (e: ErrorMaestros) => {
        this.cargando.set(false);
        this.aviso.open(e.mensaje, 'Cerrar', { duration: 5000 });
      },
    });
  }

  private cargarTallas(): void {
    this.api.tallas().subscribe({
      next: (lista) => this.tallas.set(lista),
      error: (e: ErrorMaestros) => this.aviso.open(e.mensaje, 'Cerrar', { duration: 5000 }),
    });
  }

  private cargarColores(): void {
    this.api.colores().subscribe({
      next: (lista) => this.colores.set(lista),
      error: (e: ErrorMaestros) => this.aviso.open(e.mensaje, 'Cerrar', { duration: 5000 }),
    });
  }

  // --- Categorías --------------------------------------------------------

  protected nuevaCategoria(): void {
    this.abrirCategoria(null);
  }

  protected editarCategoria(categoria: Categoria): void {
    this.abrirCategoria(categoria);
  }

  private abrirCategoria(categoria: Categoria | null): void {
    const datos: DatosCategoria = { arbol: this.categorias(), categoria };
    this.dialogo
      .open<CategoriaFormulario, DatosCategoria, boolean>(CategoriaFormulario, {
        width: '520px',
        maxWidth: '94vw',
        data: datos,
      })
      .afterClosed()
      .subscribe((guardado) => {
        if (!guardado) return;
        this.cargarCategorias();
        this.aviso.open(categoria ? 'Categoría actualizada.' : 'Categoría registrada.', 'Cerrar', {
          duration: 3500,
        });
      });
  }

  protected cambiarEstadoCategoria(categoria: Categoria): void {
    this.api.cambiarEstadoCategoria(categoria.id, !categoria.activa).subscribe({
      next: () => this.cargarCategorias(),
      error: (e: ErrorMaestros) => this.aviso.open(e.mensaje, 'Cerrar', { duration: 5000 }),
    });
  }

  protected eliminarCategoria(categoria: Categoria): void {
    this.confirmarBorrado({
      titulo: 'Eliminar categoría',
      mensaje: `¿Eliminar «${categoria.nombre}»? Esta acción no se puede deshacer.`,
      alBorrar: () => this.api.eliminarCategoria(categoria.id),
      alTerminar: () => this.cargarCategorias(),
      alDesactivar: () => this.api.cambiarEstadoCategoria(categoria.id, false),
      nombre: categoria.nombre,
    });
  }

  // --- Tallas ------------------------------------------------------------

  protected nuevaTalla(): void {
    this.abrirTalla(null);
  }

  protected editarTalla(talla: Talla): void {
    this.abrirTalla(talla);
  }

  private abrirTalla(talla: Talla | null): void {
    const datos: DatosTalla = {
      talla,
      tipos: [...new Set(this.tallas().map((t) => t.tipo_prenda))].sort(),
    };
    this.dialogo
      .open<TallaFormulario, DatosTalla, boolean>(TallaFormulario, {
        width: '460px',
        maxWidth: '94vw',
        data: datos,
      })
      .afterClosed()
      .subscribe((guardado) => {
        if (!guardado) return;
        this.cargarTallas();
        this.aviso.open(talla ? 'Talla actualizada.' : 'Talla registrada.', 'Cerrar', {
          duration: 3500,
        });
      });
  }

  protected cambiarEstadoTalla(talla: Talla): void {
    this.api.cambiarEstadoTalla(talla.id, !talla.activa).subscribe({
      next: () => this.cargarTallas(),
      error: (e: ErrorMaestros) => this.aviso.open(e.mensaje, 'Cerrar', { duration: 5000 }),
    });
  }

  protected eliminarTalla(talla: Talla): void {
    this.confirmarBorrado({
      titulo: 'Eliminar talla',
      mensaje: `¿Eliminar la talla «${talla.codigo}» de ${talla.tipo_prenda}?`,
      alBorrar: () => this.api.eliminarTalla(talla.id),
      alTerminar: () => this.cargarTallas(),
      alDesactivar: () => this.api.cambiarEstadoTalla(talla.id, false),
      nombre: talla.codigo,
    });
  }

  // --- Colores -----------------------------------------------------------

  protected nuevoColor(): void {
    this.abrirColor(null);
  }

  protected editarColor(color: Color): void {
    this.abrirColor(color);
  }

  private abrirColor(color: Color | null): void {
    const datos: DatosColor = { color };
    this.dialogo
      .open<ColorFormulario, DatosColor, boolean>(ColorFormulario, {
        width: '460px',
        maxWidth: '94vw',
        data: datos,
      })
      .afterClosed()
      .subscribe((guardado) => {
        if (!guardado) return;
        this.cargarColores();
        this.aviso.open(color ? 'Color actualizado.' : 'Color registrado.', 'Cerrar', {
          duration: 3500,
        });
      });
  }

  protected cambiarEstadoColor(color: Color): void {
    this.api.cambiarEstadoColor(color.id, !color.activo).subscribe({
      next: () => this.cargarColores(),
      error: (e: ErrorMaestros) => this.aviso.open(e.mensaje, 'Cerrar', { duration: 5000 }),
    });
  }

  protected eliminarColor(color: Color): void {
    this.confirmarBorrado({
      titulo: 'Eliminar color',
      mensaje: `¿Eliminar el color «${color.nombre}»?`,
      alBorrar: () => this.api.eliminarColor(color.id),
      alTerminar: () => this.cargarColores(),
      alDesactivar: () => this.api.cambiarEstadoColor(color.id, false),
      nombre: color.nombre,
    });
  }

  // --- Borrado con la salida de la excepción E3 --------------------------

  /**
   * Confirma, borra, y si el servidor responde que hay dependencias, ofrece
   * desactivar en su lugar.
   *
   * Esa segunda oferta es literalmente lo que pide la excepción E3: no alcanza
   * con informar que no se puede: el caso de uso dice «y ofrece desactivarla».
   */
  private confirmarBorrado(opciones: {
    titulo: string;
    mensaje: string;
    nombre: string;
    alBorrar: () => Observable<void>;
    alDesactivar: () => Observable<unknown>;
    alTerminar: () => void;
  }): void {
    const confirmacion: DatosConfirmacion = {
      titulo: opciones.titulo,
      mensaje: opciones.mensaje,
      confirmar: 'Eliminar',
      peligrosa: true,
    };

    this.dialogo
      .open<Confirmacion, DatosConfirmacion, boolean>(Confirmacion, { data: confirmacion })
      .afterClosed()
      .subscribe((confirmado) => {
        if (!confirmado) return;
        opciones.alBorrar().subscribe({
          next: () => {
            opciones.alTerminar();
            this.aviso.open('Elemento eliminado.', 'Cerrar', { duration: 3500 });
          },
          error: (e: ErrorMaestros) => {
            if (e.tipo !== 'no-eliminable') {
              this.aviso.open(e.mensaje, 'Cerrar', { duration: 5000 });
              return;
            }
            this.ofrecerDesactivar(opciones.nombre, e.mensaje, opciones.alDesactivar, opciones.alTerminar);
          },
        });
      });
  }

  private ofrecerDesactivar(
    nombre: string,
    motivo: string,
    alDesactivar: () => Observable<unknown>,
    alTerminar: () => void,
  ): void {
    const datos: DatosConfirmacion = {
      titulo: 'No se puede eliminar',
      mensaje: `${motivo} ¿Desactivar «${nombre}» en su lugar? Deja de ofrecerse para variantes nuevas, pero se conserva en las que ya lo usan.`,
      confirmar: 'Desactivar',
    };

    this.dialogo
      .open<Confirmacion, DatosConfirmacion, boolean>(Confirmacion, { data: datos })
      .afterClosed()
      .subscribe((desactivar) => {
        if (!desactivar) return;
        alDesactivar().subscribe({
          next: () => {
            alTerminar();
            this.aviso.open('Elemento desactivado.', 'Cerrar', { duration: 3500 });
          },
          error: (e: ErrorMaestros) => this.aviso.open(e.mensaje, 'Cerrar', { duration: 5000 }),
        });
      });
  }
}
