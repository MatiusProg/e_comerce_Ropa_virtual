import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';

import { AuthService } from '../../../core/services/auth.service';
import {
  InventarioService,
  type ErrorInventario,
} from '../../../core/services/inventario.service';
import { OrganizacionService } from '../../../core/services/organizacion.service';
import { ProveedoresService } from '../../../core/services/proveedores.service';
import type {
  Existencia,
  IngresoResumen,
  Movimiento,
  PaginaIngresos,
  PaginaMovimientos,
  TipoMovimiento,
} from '../../../core/models/inventario.models';
import type { SucursalBreve } from '../../../core/models/organizacion.models';
import type { Proveedor } from '../../../core/models/proveedores.models';
import { AjusteFormulario } from './ajuste-formulario';
import { MinimoFormulario, type DatosMinimoFormulario } from './minimo-formulario';
import { IngresoFormulario, type DatosIngresoFormulario } from './ingreso-formulario';
import {
  TransferenciaFormulario,
  type DatosTransferenciaFormulario,
} from './transferencia-formulario';

/**
 * CU-13, CU-15 y CU-16 · Inventario — «boundary» PantallaInventario.
 *
 * Una sola pantalla para los dos casos de uso, con tres vistas:
 *
 *   - **Existencias**: cuánto hay y dónde. Es el punto de partida de los tres.
 *   - **Ingresos** (CU-13, paso 2): los remitos ya recibidos.
 *   - **Movimientos** (CU-15): la trazabilidad completa que pide el RF22.
 *
 * **Por qué una y no dos.** Registrar un ingreso y ajustar un conteo son cosas
 * distintas, pero se hacen mirando el mismo número: el saldo de una prenda en
 * una sucursal. Separarlas en dos rutas obligaría a ir y volver para comprobar
 * si el ajuste que se acaba de hacer dejó lo que se esperaba.
 *
 * **La misma pantalla sirve a dos roles.** El Administrador ve todas las
 * sucursales y puede ajustar y transferir; el Encargado ve la suya —el
 * servidor le acota el alcance, no hace falta que la interfaz lo pida— y solo
 * registra ingresos. Las acciones de CU-15 se ocultan para él porque el
 * servidor las va a rechazar de todos modos, y ofrecer un botón que devuelve
 * 403 es una promesa que la pantalla no puede cumplir.
 */
@Component({
  selector: 'app-inventario',
  imports: [
    DatePipe,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatPaginatorModule,
    MatProgressBarModule,
    MatSelectModule,
    MatTableModule,
    MatTabsModule,
    MatTooltipModule,
  ],
  templateUrl: './inventario.html',
  styleUrl: './inventario.scss',
})
export class Inventario implements OnInit {
  private readonly api = inject(InventarioService);
  private readonly organizacion = inject(OrganizacionService);
  private readonly proveedoresApi = inject(ProveedoresService);
  private readonly auth = inject(AuthService);
  private readonly dialogo = inject(MatDialog);
  private readonly aviso = inject(MatSnackBar);

  /** Solo el Administrador ajusta y transfiere (CU-15). */
  protected readonly esAdministrador = computed(
    () => this.auth.rol() === 'ADMINISTRADOR',
  );

  protected readonly columnasExistencias = [
    'sku',
    'producto',
    'sucursal',
    'disponible',
    'reservada',
    'fisica',
    'minimo',
    'acciones',
  ];
  protected readonly columnasIngresos = [
    'fecha',
    'proveedor',
    'sucursal',
    'referencia',
    'lineas',
    'unidades',
    'usuario',
  ];
  protected readonly columnasMovimientos = [
    'fecha',
    'tipo',
    'sku',
    'producto',
    'sucursal',
    'cantidad',
    'motivo',
    'usuario',
  ];

  protected readonly cargando = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly existencias = signal<Existencia[]>([]);
  protected readonly ingresos = signal<PaginaIngresos | null>(null);
  protected readonly movimientos = signal<PaginaMovimientos | null>(null);

  /** Líneas del ingreso desplegado en el historial, o null si no hay ninguno. */
  protected readonly ingresoAbierto = signal<IngresoResumen | null>(null);
  protected readonly lineasDelIngreso = signal<Movimiento[]>([]);

  protected readonly sucursales = signal<SucursalBreve[]>([]);
  protected readonly proveedores = signal<Proveedor[]>([]);
  protected readonly tipos = signal<TipoMovimiento[]>([]);

  protected readonly filtroSucursal = new FormControl<number | ''>('', {
    nonNullable: true,
  });
  protected readonly filtroTipo = new FormControl<TipoMovimiento | ''>('', {
    nonNullable: true,
  });
  protected readonly soloConSaldo = new FormControl(true, { nonNullable: true });

  private indiceIngresos = 0;
  private indiceMovimientos = 0;
  private readonly tamano = 20;

  ngOnInit(): void {
    this.cargarMaestros();
    this.refrescarTodo();

    this.filtroSucursal.valueChanges.subscribe(() => this.refrescarTodo());
    this.soloConSaldo.valueChanges.subscribe(() => this.cargarExistencias());
    this.filtroTipo.valueChanges.subscribe(() => {
      this.indiceMovimientos = 0;
      this.cargarMovimientos();
    });
  }

  // --- Carga --------------------------------------------------------------

  private cargarMaestros(): void {
    // Las sucursales solo le sirven al Administrador: el Encargado tiene una y
    // el servidor se la impone. Pedirlas igual sería un 403 en su pantalla.
    if (this.esAdministrador()) {
      // Solo las activas: una sucursal dada de baja no recibe mercadería (E2)
      // y un proveedor de baja no la envía (E3). Ofrecerlos en el selector
      // sería prometer algo que el servidor va a rechazar.
      this.organizacion.sucursales().subscribe({
        next: (s) => this.sucursales.set(s),
        error: () => this.sucursales.set([]),
      });
      this.proveedoresApi.listar({ activo: true }).subscribe({
        next: (p) => this.proveedores.set(p),
        error: () => this.proveedores.set([]),
      });
    }
    this.api.tiposManuales().subscribe({
      next: (t) => this.tipos.set(t),
      error: () => this.tipos.set([]),
    });
  }

  protected refrescarTodo(): void {
    this.cargarExistencias();
    this.cargarIngresos();
    this.cargarMovimientos();
  }

  private get sucursalElegida(): number | undefined {
    const valor = this.filtroSucursal.value;
    return valor === '' ? undefined : valor;
  }

  private cargarExistencias(): void {
    this.cargando.set(true);
    this.api
      .listarExistencias({
        sucursal_id: this.sucursalElegida,
        solo_con_saldo: this.soloConSaldo.value,
      })
      .subscribe({
        next: (filas) => {
          this.existencias.set(filas);
          this.error.set(null);
          this.cargando.set(false);
        },
        error: (e: ErrorInventario) => {
          this.existencias.set([]);
          this.error.set(e.mensaje);
          this.cargando.set(false);
        },
      });
  }

  private cargarIngresos(): void {
    this.api
      .listarIngresos({
        sucursal_id: this.sucursalElegida,
        pagina: this.indiceIngresos + 1,
        tamano: this.tamano,
      })
      .subscribe({
        next: (p) => this.ingresos.set(p),
        error: (e: ErrorInventario) => this.error.set(e.mensaje),
      });
  }

  private cargarMovimientos(): void {
    this.api
      .listarMovimientos({
        sucursal_id: this.sucursalElegida,
        tipo: this.filtroTipo.value || undefined,
        pagina: this.indiceMovimientos + 1,
        tamano: this.tamano,
      })
      .subscribe({
        next: (p) => this.movimientos.set(p),
        error: (e: ErrorInventario) => this.error.set(e.mensaje),
      });
  }

  protected paginarIngresos(evento: PageEvent): void {
    this.indiceIngresos = evento.pageIndex;
    this.cargarIngresos();
  }

  protected paginarMovimientos(evento: PageEvent): void {
    this.indiceMovimientos = evento.pageIndex;
    this.cargarMovimientos();
  }

  // --- Detalle de un ingreso ----------------------------------------------

  /**
   * Despliega las líneas de un ingreso, o las pliega si ya estaba abierto.
   *
   * Se piden al desplegar y no junto con el listado: el historial de una
   * sucursal con meses de operación son cientos de remitos, y traer las líneas
   * de todos para mostrar veinte sería pedir el inventario entero.
   */
  protected alternarDetalle(ingreso: IngresoResumen): void {
    const abierto = this.ingresoAbierto();
    if (abierto && abierto.registrado_en === ingreso.registrado_en) {
      this.ingresoAbierto.set(null);
      this.lineasDelIngreso.set([]);
      return;
    }

    this.ingresoAbierto.set(ingreso);
    this.lineasDelIngreso.set([]);
    this.api.detalleDeIngreso(ingreso).subscribe({
      next: (lineas) => this.lineasDelIngreso.set(lineas),
      error: (e: ErrorInventario) => this.aviso.open(e.mensaje, 'Cerrar', { duration: 6000 }),
    });
  }

  protected estaAbierto(ingreso: IngresoResumen): boolean {
    return this.ingresoAbierto()?.registrado_en === ingreso.registrado_en;
  }

  // --- Acciones -----------------------------------------------------------

  protected registrarIngreso(): void {
    const datos: DatosIngresoFormulario = {
      sucursales: this.sucursales(),
      proveedores: this.proveedores(),
      sucursalFijada: this.esAdministrador() ? null : this.auth.usuario()?.sucursal_id ?? null,
    };
    this.dialogo
      .open(IngresoFormulario, { data: datos, width: '860px', disableClose: true })
      .afterClosed()
      .subscribe((registrado) => {
        if (!registrado) return;
        this.aviso.open(
          `Ingreso registrado: ${registrado.unidades} unidades en ${registrado.sucursal}.`,
          'Cerrar',
          { duration: 6000 },
        );
        this.refrescarTodo();
      });
  }

  protected ajustar(existencia: Existencia): void {
    this.dialogo
      .open(AjusteFormulario, { data: { existencia }, width: '560px', disableClose: true })
      .afterClosed()
      .subscribe((ajuste) => {
        if (!ajuste) return;
        const signo = ajuste.diferencia > 0 ? '+' : '';
        this.aviso.open(
          `Ajuste registrado: ${signo}${ajuste.diferencia} unidades.`,
          'Cerrar',
          { duration: 6000 },
        );
        this.refrescarTodo();
      });
  }

  /**
   * CU-16 desde el ámbito del Administrador, que alcanza a toda la red.
   *
   * Es el mismo diálogo que usa el Encargado en `/sucursal/disponibilidad`: la
   * operación es una sola y lo que cambia es sobre qué sucursales se puede.
   */
  protected fijarMinimo(existencia: Existencia): void {
    const datos: DatosMinimoFormulario = { existencia };
    this.dialogo
      .open(MinimoFormulario, { data: datos, width: '520px', disableClose: true })
      .afterClosed()
      .subscribe((actualizada) => {
        if (!actualizada) return;
        this.aviso.open(
          actualizada.stock_minimo === 0
            ? `${actualizada.sku} deja de vigilarse.`
            : `${actualizada.sku} avisará cuando queden ${actualizada.stock_minimo} o menos.`,
          'Cerrar',
          { duration: 5000 },
        );
        this.refrescarTodo();
      });
  }

  protected transferir(existencia: Existencia | null): void {
    const datos: DatosTransferenciaFormulario = {
      existencia,
      existencias: this.existencias(),
      sucursales: this.sucursales(),
    };
    this.dialogo
      .open(TransferenciaFormulario, { data: datos, width: '600px', disableClose: true })
      .afterClosed()
      .subscribe((hecha) => {
        if (!hecha) return;
        this.aviso.open(
          `Transferencia registrada: ${hecha.entrada.cantidad} unidades a ${hecha.destino.sucursal}.`,
          'Cerrar',
          { duration: 6000 },
        );
        this.refrescarTodo();
      });
  }

  // --- Presentación -------------------------------------------------------

  /** El signo se muestra siempre: es lo que distingue una salida de una entrada. */
  protected conSigno(cantidad: number): string {
    return cantidad > 0 ? `+${cantidad}` : `${cantidad}`;
  }

  protected claseDeTipo(tipo: TipoMovimiento): string {
    return `tipo-${tipo.toLowerCase()}`;
  }
}
