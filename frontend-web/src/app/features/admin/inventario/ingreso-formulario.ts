import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';

import {
  InventarioService,
  type ErrorInventario,
} from '../../../core/services/inventario.service';
import { ProductosService } from '../../../core/services/productos.service';
import type {
  AvisoDeIngreso,
  LineaIngreso,
} from '../../../core/models/inventario.models';
import type { ProductoResumen, Variante } from '../../../core/models/productos.models';
import type { SucursalBreve } from '../../../core/models/organizacion.models';
import type { Proveedor } from '../../../core/models/proveedores.models';

/** Una línea del remito, ya con la prenda resuelta para poder mostrarla. */
interface LineaEnPantalla extends LineaIngreso {
  sku: string;
  producto: string;
  talla: string;
  color: string;
  /** E1: el servidor rechazó esta línea. Se marca en vez de invalidar todo. */
  rechazada?: boolean;
  /** Cuánto había anunciado el proveedor, si la línea vino de un aviso. */
  anunciado?: number;
}

export interface DatosIngresoFormulario {
  sucursales: SucursalBreve[];
  proveedores: Proveedor[];
  /**
   * Sucursal impuesta cuando quien opera es un Encargado.
   *
   * Su ámbito viaja en el token y el servidor la rechaza si manda otra, así
   * que el selector se fija en vez de ofrecerle una lista que no puede usar.
   */
  sucursalFijada: number | null;
}

/**
 * CU-13 · Registrar ingreso de mercadería — pasos 4 a 7.
 *
 * **El remito se arma entero antes de enviarse.** Las líneas se agregan a una
 * lista en pantalla y recién al confirmar viajan todas juntas en una sola
 * petición: el ingreso es una transacción, y mandar las líneas de a una dejaría
 * medio remito cargado si se corta la conexión (excepción E9).
 *
 * **La prenda se elige en dos pasos: producto y después variante.** Un catálogo
 * de sesenta productos con cinco tallas y cuatro colores son mil doscientas
 * variantes, y un desplegable con mil doscientas entradas no se puede usar. Se
 * busca el producto —que es lo que dice el remito— y ahí aparecen sus
 * combinaciones.
 *
 * **Lo anunciado aparece arriba, antes del buscador (CU-39).** Quien recibe
 * un camión casi siempre está recibiendo algo que el proveedor ya anunció, y
 * hacerle buscar la variante a mano es pedirle que reconstruya un dato que el
 * sistema ya tiene. Peor: así el aviso no se cerraba nunca, y el consolidado
 * seguía prometiendo mercadería que ya estaba en el saldo.
 *
 * Tocar un aviso agrega la línea con la cantidad pendiente **ya puesta y
 * editable**: lo más común es que llegue todo, y lo segundo más común es que
 * llegue parte.
 *
 * **La misma prenda no puede ir en dos líneas** (excepción E4). Se comprueba
 * acá al agregar, para no dejar que el remito se arme mal y falle al confirmar;
 * el servidor lo vuelve a comprobar porque el formulario no es la única puerta.
 */
@Component({
  selector: 'app-ingreso-formulario',
  imports: [
    ReactiveFormsModule,
    MatAutocompleteModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatSelectModule,
    MatTableModule,
    MatTooltipModule,
  ],
  templateUrl: './ingreso-formulario.html',
  styleUrl: './ingreso-formulario.scss',
})
export class IngresoFormulario {
  private readonly api = inject(InventarioService);
  private readonly catalogo = inject(ProductosService);
  private readonly fb = inject(FormBuilder);
  protected readonly datos = inject<DatosIngresoFormulario>(MAT_DIALOG_DATA);
  private readonly dialogo = inject(MatDialogRef<IngresoFormulario>);

  protected readonly columnas = ['sku', 'prenda', 'cantidad', 'quitar'];

  protected readonly guardando = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly lineas = signal<LineaEnPantalla[]>([]);

  /** CU-39: lo anunciado que todavía no llegó. */
  protected readonly avisos = signal<AvisoDeIngreso[]>([]);

  /** Los que todavía no se pasaron al remito, para no ofrecerlos dos veces. */
  protected readonly avisosDisponibles = computed(() => {
    const yaEstan = new Set(this.lineas().map((l) => l.variante_id));
    return this.avisos().filter((a) => !yaEstan.has(a.variante_id));
  });
  protected readonly unidades = computed(() =>
    this.lineas().reduce((suma, l) => suma + l.cantidad, 0),
  );

  // --- Cabecera -----------------------------------------------------------

  protected readonly cabecera = this.fb.nonNullable.group({
    sucursal_id: [
      this.datos.sucursalFijada ?? (null as number | null),
      Validators.required,
    ],
    proveedor_id: [null as number | null, Validators.required],
    referencia: ['', Validators.maxLength(40)],
    observacion: ['', Validators.maxLength(120)],
  });

  /** El Encargado no elige sucursal: ya la tiene. */
  protected readonly sucursalFija = this.datos.sucursalFijada !== null;

  // --- Elección de la prenda ----------------------------------------------

  protected readonly busqueda = new FormControl('', { nonNullable: true });
  protected readonly productos = signal<ProductoResumen[]>([]);
  protected readonly variantes = signal<Variante[]>([]);
  protected readonly productoElegido = signal<ProductoResumen | null>(null);
  protected readonly buscando = signal(false);

  protected readonly varianteElegida = new FormControl<number | null>(null);
  protected readonly cantidad = new FormControl<number | null>(null, [
    Validators.min(1),
  ]);

  constructor() {
    // Sin avisos la pantalla sigue sirviendo igual: se pierde el atajo, no
    // el ingreso. Por eso el error se traga en vez de mostrar un cartel.
    this.api.avisosDeIngreso().subscribe({
      next: (a) => this.avisos.set(a),
      error: () => undefined,
    });

    this.busqueda.valueChanges
      .pipe(debounceTime(300), distinctUntilChanged())
      .subscribe((texto) => this.buscarProductos(texto));
  }

  private buscarProductos(texto: string): void {
    if (texto.trim().length < 2) {
      this.productos.set([]);
      return;
    }
    this.buscando.set(true);
    this.catalogo.listar({ busqueda: texto.trim(), activo: true, tamano: 20 }).subscribe({
      next: (p) => {
        this.productos.set(p.items);
        this.buscando.set(false);
      },
      error: () => {
        this.productos.set([]);
        this.buscando.set(false);
      },
    });
  }

  protected elegirProducto(producto: ProductoResumen): void {
    this.productoElegido.set(producto);
    this.varianteElegida.reset();
    this.variantes.set([]);
    this.catalogo.obtener(producto.id).subscribe({
      next: (detalle) => this.variantes.set(detalle.variantes.filter((v) => v.activa)),
      error: (e) => this.error.set(e.mensaje),
    });
  }

  protected nombreDeProducto(producto: ProductoResumen | string | null): string {
    if (!producto || typeof producto === 'string') return (producto as string) ?? '';
    return `${producto.codigo} · ${producto.nombre}`;
  }

  // --- Líneas del remito --------------------------------------------------

  protected agregarLinea(): void {
    const producto = this.productoElegido();
    const varianteId = this.varianteElegida.value;
    const cuantas = this.cantidad.value;

    if (!producto || !varianteId || !cuantas || cuantas < 1) {
      this.error.set('Elija la prenda y una cantidad mayor que cero.');
      return;
    }

    // Excepción E4: dos líneas de la misma variante casi siempre son la misma
    // caja contada dos veces. Se avisa acá para que el remito no se arme mal.
    if (this.lineas().some((l) => l.variante_id === varianteId)) {
      this.error.set(
        'Esa prenda ya está en el remito. Modifique su cantidad en vez de agregarla otra vez.',
      );
      return;
    }

    const variante = this.variantes().find((v) => v.id === varianteId)!;
    this.lineas.update((actuales) => [
      ...actuales,
      {
        variante_id: varianteId,
        cantidad: cuantas,
        sku: variante.sku,
        producto: producto.nombre,
        talla: variante.talla_codigo ?? '',
        color: variante.color_nombre ?? '',
      },
    ]);

    this.error.set(null);
    this.varianteElegida.reset();
    this.cantidad.reset();
  }

  /** Pasa un aviso al remito, con lo que falta ya puesto. */
  protected recibirAviso(aviso: AvisoDeIngreso): void {
    if (this.lineas().some((l) => l.variante_id === aviso.variante_id)) {
      this.error.set('Esa prenda ya está en el remito.');
      return;
    }

    // El proveedor del remito lo fija el PRIMER aviso que se toma: el
    // ingreso es de un solo proveedor, y mezclar avisos de dos haría que el
    // servidor rechace el segundo — después de que la persona lo agregó.
    const cabeceraProveedor = this.cabecera.controls.proveedor_id;
    if (!cabeceraProveedor.value) {
      cabeceraProveedor.setValue(aviso.proveedor_id);
    } else if (cabeceraProveedor.value !== aviso.proveedor_id) {
      this.error.set(
        `Ese aviso es de ${aviso.proveedor}. Un remito es de un solo proveedor: ` +
          'registre este ingreso y arme otro para el resto.',
      );
      return;
    }

    this.lineas.update((actuales) => [
      ...actuales,
      {
        variante_id: aviso.variante_id,
        cantidad: aviso.cantidad_pendiente,
        abastecimiento_id: aviso.id,
        anunciado: aviso.cantidad_pendiente,
        sku: aviso.sku,
        producto: aviso.prenda,
        talla: aviso.talla,
        color: aviso.color,
      },
    ]);
    this.error.set(null);
  }

  /** Cuánto le quedaría al aviso con la cantidad que se puso. */
  protected restanteDe(linea: LineaEnPantalla): number | null {
    if (linea.anunciado === undefined) return null;
    return Math.max(linea.anunciado - linea.cantidad, 0);
  }

  protected quitarLinea(variante_id: number): void {
    this.lineas.update((actuales) => actuales.filter((l) => l.variante_id !== variante_id));
  }

  // --- Confirmación -------------------------------------------------------

  protected confirmar(): void {
    if (this.cabecera.invalid || !this.lineas().length) {
      this.cabecera.markAllAsTouched();
      this.error.set('Indique el proveedor, la sucursal y al menos una prenda.');
      return;
    }

    const valores = this.cabecera.getRawValue();
    this.guardando.set(true);
    this.error.set(null);

    this.api
      .registrarIngreso({
        sucursal_id: valores.sucursal_id!,
        proveedor_id: valores.proveedor_id!,
        referencia: valores.referencia.trim() || null,
        observacion: valores.observacion.trim() || null,
        lineas: this.lineas().map(({ variante_id, cantidad, abastecimiento_id }) => ({
          variante_id,
          cantidad,
          abastecimiento_id: abastecimiento_id ?? null,
        })),
      })
      .subscribe({
        next: (registrado) => this.dialogo.close(registrado),
        error: (e: ErrorInventario) => {
          this.guardando.set(false);
          this.error.set(e.mensaje);

          // E1: el servidor dice CUÁLES prendas fallaron. Se marcan esas
          // líneas en vez de invalidar el remito entero, que es lo que
          // obligaría a volver a cargar las quince que sí estaban bien.
          if (e.tipo === 'lineas-invalidas') {
            this.lineas.update((actuales) =>
              actuales.map((l) => ({
                ...l,
                rechazada: e.variantes.includes(l.variante_id),
              })),
            );
          }
        },
      });
  }

  protected cancelar(): void {
    this.dialogo.close(null);
  }
}
