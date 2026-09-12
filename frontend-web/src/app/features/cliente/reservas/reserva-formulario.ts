import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatButtonModule } from '@angular/material/button';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatNativeDateModule } from '@angular/material/core';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';

import {
  ReservasService,
  type ErrorReservas,
} from '../../../core/services/reservas.service';
import { TiendaService } from '../../../core/services/tienda.service';
import type { LineaReserva } from '../../../core/models/reservas.models';
import type {
  Disponibilidad,
  DisponibilidadSucursal,
  FichaProducto,
  ProductoVitrina,
  VarianteVitrina,
} from '../../../core/models/tienda.models';

/** Una línea ya armada, con la prenda resuelta para poder mostrarla. */
interface LineaEnPantalla extends LineaReserva {
  sku: string;
  producto: string;
  talla: string;
  color: string;
  /** E1: el servidor rechazó esta prenda. Se marca en vez de invalidar todo. */
  rechazada?: boolean;
}

/** Las duraciones que ofrece el selector, dentro de lo que admite el servidor. */
const DURACIONES = [15, 30, 45, 60, 90, 120];

/**
 * Convierte una fecha local a ISO **conservando la hora de pared**.
 *
 * `toISOString()` no sirve acá y el motivo no es evidente: convierte a UTC, de
 * modo que las 15:00 de Bolivia salen como `19:00Z`. El servidor compara la
 * hora de la franja contra `sucursal.horario_apertura`, que es un `TIME` sin
 * zona y significa «abre a las nueve» en esa tienda; con la hora convertida,
 * un local que cierra a las 18:00 rechazaría una reserva de las 15:00.
 *
 * Lo que hace falta es mandar la hora tal cual **más el desfase** —
 * `2026-09-12T15:00:00-04:00`—, que es lo que el backend exige y lo que
 * `timestamptz` guarda sin ambigüedad.
 */
function conDesfase(fecha: Date): string {
  const p = (n: number) => String(n).padStart(2, '0');
  const minutos = -fecha.getTimezoneOffset();
  const signo = minutos >= 0 ? '+' : '-';
  const hh = p(Math.floor(Math.abs(minutos) / 60));
  const mm = p(Math.abs(minutos) % 60);
  return (
    `${fecha.getFullYear()}-${p(fecha.getMonth() + 1)}-${p(fecha.getDate())}` +
    `T${p(fecha.getHours())}:${p(fecha.getMinutes())}:00${signo}${hh}:${mm}`
  );
}

/**
 * CU-22 · Crear reserva de prendas — pasos 2 a 7.
 *
 * **La sucursal se elige DESPUÉS de las prendas, y no antes.** Es el orden
 * contrario al que pide el formulario del servidor, y es deliberado: la
 * pregunta del cliente es «¿dónde puedo probarme esto?», no «¿qué hay en la
 * sucursal Centro?». Eligiendo primero las prendas, el selector de sucursal
 * puede ofrecer **solo las que tienen stock de todas ellas** —usando CU-19, que
 * se apoya en la costura C1— en vez de dejar que arme una combinación que el
 * servidor va a rechazar.
 *
 * **La prenda se elige en dos pasos: producto y después variante.** Un catálogo
 * de sesenta productos con cinco tallas y cuatro colores son mil doscientas
 * variantes; un desplegable con eso no se puede usar. Mismo criterio que el
 * remito de CU-13.
 */
@Component({
  selector: 'app-reserva-formulario',
  imports: [
    ReactiveFormsModule,
    MatAutocompleteModule,
    MatButtonModule,
    MatDatepickerModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatNativeDateModule,
    MatProgressBarModule,
    MatSelectModule,
    MatTableModule,
    MatTooltipModule,
  ],
  templateUrl: './reserva-formulario.html',
  styleUrl: './reserva-formulario.scss',
})
export class ReservaFormulario {
  private readonly api = inject(ReservasService);
  private readonly tienda = inject(TiendaService);
  private readonly fb = inject(FormBuilder);
  private readonly dialogo = inject(MatDialogRef<ReservaFormulario>);

  protected readonly columnas = ['sku', 'prenda', 'cantidad', 'quitar'];
  protected readonly duraciones = DURACIONES;

  protected readonly guardando = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly lineas = signal<LineaEnPantalla[]>([]);
  protected readonly unidades = computed(() =>
    this.lineas().reduce((suma, l) => suma + l.cantidad, 0),
  );

  // --- Elección de la prenda ----------------------------------------------

  protected readonly busqueda = new FormControl('', { nonNullable: true });
  protected readonly productos = signal<ProductoVitrina[]>([]);
  protected readonly ficha = signal<FichaProducto | null>(null);
  protected readonly varianteElegida = new FormControl<number | null>(null);
  protected readonly cantidad = new FormControl<number>(1, [
    Validators.min(1),
    Validators.max(10),
  ]);

  // --- Sucursales que pueden cumplir con TODA la reserva -------------------

  protected readonly sucursalesPosibles = signal<DisponibilidadSucursal[]>([]);
  protected readonly buscandoSucursales = signal(false);

  // --- Franja --------------------------------------------------------------

  protected readonly franja = this.fb.nonNullable.group({
    sucursal_id: [null as number | null, Validators.required],
    dia: [this.manana(), Validators.required],
    hora: ['15:00', Validators.required],
    duracion: [60, Validators.required],
  });

  /** Desde mañana: hoy puede haber pasado ya según la hora. */
  protected readonly minimo = new Date();
  protected readonly maximo = (() => {
    const tope = new Date();
    // Tres días, que es `RESERVA_ANTICIPACION_MAXIMA_HORAS` por defecto. Es una
    // conveniencia del selector, no la regla: la regla la aplica el servidor y
    // el mensaje de E5 lo dice si alguien llega igual.
    tope.setDate(tope.getDate() + 3);
    return tope;
  })();

  constructor() {
    this.busqueda.valueChanges
      .pipe(debounceTime(300), distinctUntilChanged())
      .subscribe((texto) => this.buscarProductos(texto));
  }

  private manana(): Date {
    const dia = new Date();
    dia.setDate(dia.getDate() + 1);
    return dia;
  }

  private buscarProductos(texto: string): void {
    if (texto.trim().length < 2) {
      this.productos.set([]);
      return;
    }
    this.tienda.listar({ busqueda: texto.trim(), tamano: 20 }).subscribe({
      next: (p) => this.productos.set(p.items),
      error: () => this.productos.set([]),
    });
  }

  protected elegirProducto(producto: ProductoVitrina): void {
    this.varianteElegida.reset();
    this.ficha.set(null);
    this.tienda.obtenerFicha(producto.id).subscribe({
      next: (ficha) => this.ficha.set(ficha),
      error: (e: ErrorReservas) => this.error.set(e.mensaje),
    });
  }

  protected nombreDeProducto(producto: ProductoVitrina | string | null): string {
    if (!producto || typeof producto === 'string') return (producto as string) ?? '';
    return producto.nombre;
  }

  protected etiquetaDeVariante(variante: VarianteVitrina): string {
    return `${variante.talla_codigo} · ${variante.color_nombre}`;
  }

  // --- Líneas ---------------------------------------------------------------

  protected agregarLinea(): void {
    const ficha = this.ficha();
    const varianteId = this.varianteElegida.value;
    const cuantas = this.cantidad.value;

    if (!ficha || !varianteId || !cuantas || cuantas < 1) {
      this.error.set('Elegí la prenda, la talla y el color.');
      return;
    }
    if (this.lineas().some((l) => l.variante_id === varianteId)) {
      this.error.set(
        'Esa prenda ya está en la reserva. Si querés más de una unidad, subí la cantidad.',
      );
      return;
    }

    const variante = ficha.variantes.find((v) => v.id === varianteId)!;
    this.lineas.update((actuales) => [
      ...actuales,
      {
        variante_id: varianteId,
        cantidad: cuantas,
        sku: variante.sku,
        producto: ficha.nombre,
        talla: variante.talla_codigo ?? '',
        color: variante.color_nombre ?? '',
      },
    ]);

    this.error.set(null);
    this.varianteElegida.reset();
    this.cantidad.setValue(1);
    this.recalcularSucursales();
  }

  protected quitarLinea(variante_id: number): void {
    this.lineas.update((a) => a.filter((l) => l.variante_id !== variante_id));
    this.recalcularSucursales();
  }

  /**
   * Deja en el selector solo las sucursales que tienen **todas** las prendas.
   *
   * Se cruza la disponibilidad de cada variante (CU-19) y se queda con la
   * intersección. Ofrecer una sucursal que tiene dos de las tres prendas sería
   * dejar armar una reserva que el servidor rechaza con un 409, después de que
   * el cliente ya eligió día y hora.
   */
  private recalcularSucursales(): void {
    const lineas = this.lineas();
    if (!lineas.length) {
      this.sucursalesPosibles.set([]);
      this.franja.controls.sucursal_id.reset();
      return;
    }

    this.buscandoSucursales.set(true);
    const disponibilidades: Disponibilidad[] = [];
    let pendientes = lineas.length;

    for (const linea of lineas) {
      this.tienda.obtenerDisponibilidad(linea.variante_id).subscribe({
        next: (d) => disponibilidades.push(d),
        error: () => undefined,
        complete: () => {
          if (--pendientes === 0) this.cruzar(lineas, disponibilidades);
        },
      });
    }
  }

  private cruzar(lineas: LineaEnPantalla[], disponibilidades: Disponibilidad[]): void {
    this.buscandoSucursales.set(false);
    if (disponibilidades.length !== lineas.length) {
      this.sucursalesPosibles.set([]);
      return;
    }

    const porVariante = new Map(disponibilidades.map((d) => [d.variante_id, d]));
    let candidatas: DisponibilidadSucursal[] | null = null;

    for (const linea of lineas) {
      const sucursales = (porVariante.get(linea.variante_id)?.sucursales ?? []).filter(
        (s) => s.cantidad_disponible >= linea.cantidad,
      );
      candidatas =
        candidatas === null
          ? sucursales
          : candidatas.filter((c) => sucursales.some((s) => s.sucursal_id === c.sucursal_id));
    }

    this.sucursalesPosibles.set(candidatas ?? []);

    // Si la sucursal elegida dejó de servir —porque se agregó otra prenda que
    // ahí no hay—, se deselecciona en vez de quedar mostrando algo inválido.
    const elegida = this.franja.controls.sucursal_id.value;
    if (elegida && !(candidatas ?? []).some((s) => s.sucursal_id === elegida)) {
      this.franja.controls.sucursal_id.reset();
    }
  }

  // --- Confirmación ---------------------------------------------------------

  protected confirmar(): void {
    if (this.franja.invalid || !this.lineas().length) {
      this.franja.markAllAsTouched();
      this.error.set('Elegí al menos una prenda, la sucursal y la franja.');
      return;
    }

    const valores = this.franja.getRawValue();
    const [hora, minuto] = valores.hora.split(':').map(Number);

    const inicio = new Date(valores.dia);
    inicio.setHours(hora, minuto, 0, 0);
    const fin = new Date(inicio);
    fin.setMinutes(fin.getMinutes() + valores.duracion);

    this.guardando.set(true);
    this.error.set(null);

    this.api
      .crear({
        sucursal_id: valores.sucursal_id!,
        franja_inicio: conDesfase(inicio),
        franja_fin: conDesfase(fin),
        lineas: this.lineas().map(({ variante_id, cantidad }) => ({
          variante_id,
          cantidad,
        })),
      })
      .subscribe({
        next: (reserva) => this.dialogo.close(reserva),
        error: (e: ErrorReservas) => {
          this.guardando.set(false);
          this.error.set(e.mensaje);

          if (e.tipo === 'lineas-invalidas') {
            this.lineas.update((actuales) =>
              actuales.map((l) => ({
                ...l,
                rechazada: e.variantes.includes(l.variante_id),
              })),
            );
          }
          // Si perdimos la carrera por el stock (R5), la disponibilidad que
          // mostramos ya no vale: se vuelve a pedir en vez de dejar al cliente
          // reintentando contra un número viejo.
          if (e.tipo === 'sin-stock') {
            this.recalcularSucursales();
          }
        },
      });
  }

  protected cancelar(): void {
    this.dialogo.close(null);
  }
}
