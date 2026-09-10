import { Component, OnInit, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
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

import {
  ProductosService,
  type ErrorProductos,
} from '../../../core/services/productos.service';
import { MaestrosService } from '../../../core/services/maestros.service';
import { TemporadasService } from '../../../core/services/temporadas.service';
import { ProveedoresService } from '../../../core/services/proveedores.service';
import type { PaginaProductos, ProductoResumen } from '../../../core/models/productos.models';
import {
  aplanarCategorias,
  type Categoria,
  type CategoriaPlana,
  type Color,
  type Talla,
} from '../../../core/models/maestros.models';
import type { Coleccion, Temporada } from '../../../core/models/temporadas.models';
import type { Proveedor } from '../../../core/models/proveedores.models';
import { Confirmacion, type DatosConfirmacion } from '../../../shared/confirmacion/confirmacion';
import { Galeria, type DatosGaleria } from './galeria';
import { ProductoFormulario, type DatosProductoFormulario } from './producto-formulario';
import { Variantes, type DatosVariantes } from './variantes';

/**
 * CU-10 · Gestionar productos y variantes — «boundary» PantallaProductos.
 *
 * Realiza el paso 2 (listado con búsqueda, filtros y paginación) y desde ahí
 * abre las dos operaciones del caso de uso: el formulario del producto (pasos
 * 4 a 6 y flujo 3a) y el panel de variantes (paso 7 y flujos 7a a 7c).
 *
 * **Con paginación, a diferencia de los maestros.** Categorías, tallas y
 * colores son decenas y caben en una pantalla; los productos son el catálogo
 * entero de la tienda, y cada uno arrastra sus variantes. El backend tiene tope
 * de 100 por página justamente para que esta pantalla no pueda pedir todo.
 *
 * Los maestros —categorías, tallas, colores, temporadas, colecciones y
 * proveedores— se cargan una vez al entrar y se le pasan a los diálogos. Sirven
 * para los filtros de acá, así que volver a pedirlos al abrir cada formulario
 * serían seis consultas por cada alta.
 */
@Component({
  selector: 'app-productos',
  imports: [
    ReactiveFormsModule,
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
  templateUrl: './productos.html',
  styleUrl: './productos.scss',
})
export class Productos implements OnInit {
  private readonly api = inject(ProductosService);
  private readonly maestros = inject(MaestrosService);
  private readonly temporadasApi = inject(TemporadasService);
  private readonly proveedoresApi = inject(ProveedoresService);
  private readonly dialogo = inject(MatDialog);
  private readonly aviso = inject(MatSnackBar);

  protected readonly columnas = [
    'codigo',
    'nombre',
    'categoria',
    'precio',
    'variantes',
    'imagenes',
    'estado',
    'acciones',
  ];

  protected readonly cargando = signal(false);
  /** Mensaje del último fallo al listar, o null. Distingue «no se pudo
   *  consultar» de «no hay nada», que en pantalla se confundían. */
  protected readonly error = signal<string | null>(null);
  protected readonly pagina = signal<PaginaProductos | null>(null);

  // Maestros, para los filtros y para los diálogos.
  private readonly arbolCategorias = signal<Categoria[]>([]);
  protected readonly categorias = signal<CategoriaPlana[]>([]);
  protected readonly tallas = signal<Talla[]>([]);
  protected readonly colores = signal<Color[]>([]);
  protected readonly temporadas = signal<Temporada[]>([]);
  protected readonly colecciones = signal<Coleccion[]>([]);
  protected readonly proveedores = signal<Proveedor[]>([]);

  protected readonly busqueda = new FormControl('', { nonNullable: true });
  protected readonly filtroCategoria = new FormControl<number | ''>('', { nonNullable: true });
  protected readonly filtroTemporada = new FormControl<number | ''>('', { nonNullable: true });
  protected readonly filtroProveedor = new FormControl<number | ''>('', { nonNullable: true });
  protected readonly filtroEstado = new FormControl<string>('', { nonNullable: true });

  private indice = 0;
  private tamano = 20;

  ngOnInit(): void {
    this.cargarMaestros();

    // El debounce evita disparar una consulta por cada tecla.
    this.busqueda.valueChanges
      .pipe(debounceTime(350), distinctUntilChanged())
      .subscribe(() => this.reiniciarYCargar());
    this.filtroCategoria.valueChanges.subscribe(() => this.reiniciarYCargar());
    this.filtroTemporada.valueChanges.subscribe(() => this.reiniciarYCargar());
    this.filtroProveedor.valueChanges.subscribe(() => this.reiniciarYCargar());
    this.filtroEstado.valueChanges.subscribe(() => this.reiniciarYCargar());

    this.cargar();
  }

  private cargarMaestros(): void {
    this.maestros.categorias().subscribe({
      next: (arbol) => {
        this.arbolCategorias.set(arbol);
        this.categorias.set(aplanarCategorias(arbol));
      },
    });
    this.maestros.tallas().subscribe({ next: (t) => this.tallas.set(t) });
    this.maestros.colores().subscribe({ next: (c) => this.colores.set(c) });
    this.temporadasApi.listarTemporadas().subscribe({ next: (t) => this.temporadas.set(t) });
    this.temporadasApi.listarColecciones().subscribe({ next: (c) => this.colecciones.set(c) });
    this.proveedoresApi.listar().subscribe({ next: (p) => this.proveedores.set(p) });
  }

  private reiniciarYCargar(): void {
    // Cambiar un filtro con la página 3 abierta dejaría una tabla vacía sin
    // explicación: se vuelve siempre a la primera.
    this.indice = 0;
    this.cargar();
  }

  protected cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    const estado = this.filtroEstado.value;
    const categoria = this.filtroCategoria.value;
    const temporada = this.filtroTemporada.value;
    const proveedor = this.filtroProveedor.value;

    this.api
      .listar({
        busqueda: this.busqueda.value || undefined,
        categoria_id: categoria === '' ? undefined : categoria,
        temporada_id: temporada === '' ? undefined : temporada,
        proveedor_id: proveedor === '' ? undefined : proveedor,
        activo: estado === '' ? undefined : estado === 'activos',
        pagina: this.indice + 1,
        tamano: this.tamano,
      })
      .subscribe({
        next: (p) => {
          this.pagina.set(p);
          this.cargando.set(false);
        },
        error: (e: ErrorProductos) => {
          this.cargando.set(false);
          this.error.set(e.mensaje);
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
    this.filtroCategoria.setValue('', { emitEvent: false });
    this.filtroTemporada.setValue('', { emitEvent: false });
    this.filtroProveedor.setValue('', { emitEvent: false });
    this.filtroEstado.setValue('', { emitEvent: false });
    this.reiniciarYCargar();
  }

  protected get hayFiltros(): boolean {
    return !!(
      this.busqueda.value ||
      this.filtroCategoria.value !== '' ||
      this.filtroTemporada.value !== '' ||
      this.filtroProveedor.value !== '' ||
      this.filtroEstado.value
    );
  }

  // --- Producto ----------------------------------------------------------

  protected nuevo(): void {
    this.abrirFormulario(null);
  }

  /** Flujo alternativo 3a. */
  protected editar(fila: ProductoResumen): void {
    // El listado no trae la descripción ni las variantes: se pide el detalle
    // para que el formulario abra con todo, y no borre la descripción al
    // guardar por no haberla tenido nunca.
    this.cargando.set(true);
    this.api.obtener(fila.id).subscribe({
      next: (producto) => {
        this.cargando.set(false);
        this.abrirFormulario(producto);
      },
      error: (e: ErrorProductos) => {
        this.cargando.set(false);
        this.mostrar(e.mensaje);
      },
    });
  }

  private abrirFormulario(producto: DatosProductoFormulario['producto']): void {
    this.dialogo
      .open(ProductoFormulario, {
        data: {
          producto,
          arbolCategorias: this.arbolCategorias(),
          temporadas: this.temporadas(),
          colecciones: this.colecciones(),
          proveedores: this.proveedores(),
        } satisfies DatosProductoFormulario,
        width: '720px',
        maxWidth: '95vw',
      })
      .afterClosed()
      .subscribe((guardado) => {
        if (!guardado) return;
        this.mostrar(producto ? 'Producto actualizado.' : 'Producto registrado.');
        this.cargar();
      });
  }

  /** Paso 7 y flujos 7a a 7c. */
  protected verVariantes(fila: ProductoResumen): void {
    this.cargando.set(true);
    this.api.obtener(fila.id).subscribe({
      next: (producto) => {
        this.cargando.set(false);
        this.dialogo
          .open(Variantes, {
            data: {
              producto,
              tallas: this.tallas(),
              colores: this.colores(),
            } satisfies DatosVariantes,
            width: '900px',
            maxWidth: '95vw',
          })
          .afterClosed()
          .subscribe((hubocambios) => {
            // Solo se recarga si algo cambió: el conteo de variantes de la
            // tabla es lo único que pudo quedar viejo.
            if (hubocambios) this.cargar();
          });
      },
      error: (e: ErrorProductos) => {
        this.cargando.set(false);
        this.mostrar(e.mensaje);
      },
    });
  }

  /** CU-11 · la galería del producto. */
  protected verImagenes(fila: ProductoResumen): void {
    // Se pide el detalle para que el diálogo pueda ofrecer las variantes a las
    // que asociar cada imagen; el listado no las trae.
    this.cargando.set(true);
    this.api.obtener(fila.id).subscribe({
      next: (producto) => {
        this.cargando.set(false);
        this.dialogo
          .open(Galeria, {
            data: { producto } satisfies DatosGaleria,
            width: '960px',
            maxWidth: '95vw',
          })
          .afterClosed()
          .subscribe((hubocambios) => {
            if (hubocambios) this.cargar();
          });
      },
      error: (e: ErrorProductos) => {
        this.cargando.set(false);
        this.mostrar(e.mensaje);
      },
    });
  }

  /** Flujo alternativo 3b. */
  protected cambiarEstado(fila: ProductoResumen): void {
    const desactivando = fila.activo;
    const mensaje = desactivando
      ? `«${fila.nombre}» dejará de ofrecerse y sus ${fila.variantes_activas} variante(s) activa(s) se desactivarán con él. Se conserva en las existencias y reservas que ya lo referencian.`
      : `«${fila.nombre}» volverá a ofrecerse. Sus variantes quedan como están: actívelas una por una si corresponde.`;

    this.dialogo
      .open(Confirmacion, {
        data: {
          titulo: desactivando ? 'Desactivar producto' : 'Activar producto',
          mensaje,
          confirmar: desactivando ? 'Desactivar' : 'Activar',
        } satisfies DatosConfirmacion,
      })
      .afterClosed()
      .subscribe((confirmado) => {
        if (!confirmado) return;
        this.cargando.set(true);
        this.api.cambiarEstado(fila.id, !fila.activo).subscribe({
          next: () => {
            this.mostrar(desactivando ? 'Producto desactivado.' : 'Producto activado.');
            this.cargar();
          },
          error: (e: ErrorProductos) => {
            this.cargando.set(false);
            this.mostrar(e.mensaje);
          },
        });
      });
  }

  protected eliminar(fila: ProductoResumen): void {
    this.dialogo
      .open(Confirmacion, {
        data: {
          titulo: 'Eliminar producto',
          mensaje: `Se eliminará «${fila.nombre}» junto con sus ${fila.variantes_totales} variante(s). Si ya tiene existencias o reservas, no se podrá.`,
          confirmar: 'Eliminar',
          peligrosa: true,
        } satisfies DatosConfirmacion,
      })
      .afterClosed()
      .subscribe((confirmado) => {
        if (!confirmado) return;
        this.cargando.set(true);
        this.api.eliminar(fila.id).subscribe({
          next: () => {
            this.mostrar('Producto eliminado.');
            this.cargar();
          },
          error: (e: ErrorProductos) => {
            this.cargando.set(false);
            // Excepcion E3: no es un fallo, es una regla, y el caso de uso pide
            // ofrecer la alternativa en vez de dejar al Administrador probando.
            if (e.tipo === 'con-dependencias') {
              this.ofrecerDesactivar(fila, e.mensaje);
              return;
            }
            this.mostrar(e.mensaje);
          },
        });
      });
  }

  private ofrecerDesactivar(fila: ProductoResumen, mensaje: string): void {
    this.dialogo
      .open(Confirmacion, {
        data: {
          titulo: 'No se puede eliminar',
          mensaje: `${mensaje} ¿Desea desactivarlo?`,
          confirmar: 'Desactivar',
        } satisfies DatosConfirmacion,
      })
      .afterClosed()
      .subscribe((confirmado) => {
        if (!confirmado) return;
        this.cargando.set(true);
        this.api.cambiarEstado(fila.id, false).subscribe({
          next: () => {
            this.mostrar('Producto desactivado.');
            this.cargar();
          },
          error: (e: ErrorProductos) => {
            this.cargando.set(false);
            this.mostrar(e.mensaje);
          },
        });
      });
  }

  private mostrar(mensaje: string): void {
    this.aviso.open(mensaje, 'Cerrar', { duration: 4000 });
  }
}
