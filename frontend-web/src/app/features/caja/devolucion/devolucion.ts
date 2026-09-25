import { CurrencyPipe, DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { debounceTime, distinctUntilChanged, switchMap } from 'rxjs/operators';
import { of } from 'rxjs';

import { CajaService } from '../../../core/services/caja.service';
import { PosService } from '../../../core/services/pos.service';
import {
  DevolucionesService,
  type ErrorDevolucion,
} from '../../../core/services/devoluciones.service';
import type {
  ComprobanteCambio,
  ComprobanteDevolucion,
  LineaEnDevolucion,
  PrendaQueSeLleva,
  VentaDevolvible,
} from '../../../core/models/devoluciones.models';
import type { PrendaEnMostrador } from '../../../core/models/pos.models';

/** Qué está haciendo el cajero con la prenda que le trajeron. */
export type Modo = 'DEVOLUCION' | 'CAMBIO';

/**
 * CU-32 · Registrar devolución — «boundary» PantallaDevolucion.
 *
 * LO QUE ESTA PANTALLA TIENE QUE DECIR BIEN
 * ------------------------------------------
 * **Cuánto vale lo devuelto y si sale del cajón son dos cosas distintas.** Una
 * venta cobrada con tarjeta se devuelve igual —la prenda vuelve al local— pero
 * el dinero **no sale del cajón**: nunca entró. Mostrar «Bs 250» sin más
 * llevaría al cajero a abrir el cajón y entregarlos, y esa noche el arqueo
 * cerraría con un faltante de 250 Bs que se le anotaría a él.
 *
 * **Lo que ya se devolvió no se puede volver a devolver.** El tope de cada
 * línea es `devolvibles`, no `vendidas`. El servidor lo rechaza igual, pero el
 * cajero no tiene por qué descubrirlo pulsando.
 *
 * El motivo es obligatorio acá y en el servidor. Una devolución sin motivo es
 * mercadería y plata que nadie puede auditar después.
 *
 * LOS DOS FLUJOS COMPARTEN PANTALLA, Y NO ES POR AHORRAR ARCHIVOS
 * ---------------------------------------------------------------
 * El cliente elige entre devolver y cambiar **con la prenda ya sobre el
 * mostrador**, después de que el cajero buscó la venta y vio qué se puede
 * devolver. Dos pantallas obligarían a elegir antes de tener esa información, y
 * a volver atrás y buscar la venta de nuevo cuando el cliente cambia de idea.
 *
 * **La diferencia que se muestra es una cuenta de la pantalla, no la verdad.**
 * La verdad la fija el servidor al confirmar, con las promociones de ese
 * instante. Por eso viaja como `diferencia_esperada`: si no coinciden, el
 * servidor frena y devuelve el número nuevo en vez de cobrar callado algo que
 * el cliente no vio.
 */
@Component({
  selector: 'app-devolucion',
  imports: [
    CurrencyPipe,
    DatePipe,
    RouterLink,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatButtonToggleModule,
    MatSelectModule,
  ],
  templateUrl: './devolucion.html',
  styleUrl: './devolucion.scss',
})
export class Devolucion implements OnInit {
  private readonly api = inject(DevolucionesService);
  private readonly caja = inject(CajaService);
  private readonly pos = inject(PosService);
  private readonly aviso = inject(MatSnackBar);

  protected readonly cargando = signal(true);
  protected readonly buscando = signal(false);
  protected readonly guardando = signal(false);
  protected readonly hayTurno = signal<boolean | null>(null);

  protected readonly venta = signal<VentaDevolvible | null>(null);
  protected readonly lineas = signal<LineaEnDevolucion[]>([]);
  protected readonly comprobante = signal<ComprobanteDevolucion | null>(null);

  // --- El cambio ------------------------------------------------------
  protected readonly modo = signal<Modo>('DEVOLUCION');
  /** Lo que el cliente se lleva. Vacío mientras el modo sea DEVOLUCION. */
  protected readonly llevadas = signal<PrendaQueSeLleva[]>([]);
  protected readonly resultados = signal<PrendaEnMostrador[]>([]);
  protected readonly buscandoPrendas = signal(false);
  protected readonly comprobanteCambio = signal<ComprobanteCambio | null>(null);

  protected readonly codigo = new FormControl('', {
    nonNullable: true,
    validators: [Validators.required, Validators.minLength(3)],
  });
  protected readonly motivo = new FormControl('', {
    nonNullable: true,
    validators: [Validators.required, Validators.minLength(3), Validators.maxLength(200)],
  });
  protected readonly busqueda = new FormControl('', { nonNullable: true });
  /**
   * Cómo se salda la diferencia. Sin valor por defecto a propósito: el cajero
   * tiene que elegirlo mirando lo que pasa sobre el mostrador. Uno por omisión
   * haría que la mitad de los cambios quedaran registrados como efectivo sin
   * que nadie lo decidiera, y el arqueo diría que entró plata que no entró.
   */
  protected readonly metodoDiferencia = new FormControl<string | null>(null);

  /**
   * El método elegido, COMO SEÑAL.
   *
   * POR QUE HACE FALTA ESTE ESPEJO
   * -------------------------------
   * `sePuedeConfirmar` es un `computed`, y un `computed` solo se vuelve a
   * evaluar cuando cambia una SEÑAL que leyó. `FormControl.value` no es una
   * señal: leerlo ahí adentro no suscribe a nada.
   *
   * Sin esto, elegir la forma de pago no despertaba el botón —seguía
   * deshabilitado— y recién se habilitaba al tocar otra cosa que sí fuera
   * señal, como sacar y volver a poner la prenda. El cajero veía un botón
   * muerto con el cliente enfrente.
   *
   * Mismo patrón que `ajuste-formulario.ts` en el inventario del Administrador.
   */
  private readonly metodoElegido = toSignal(this.metodoDiferencia.valueChanges, {
    initialValue: this.metodoDiferencia.value,
  });

  /** El valor de lo que se está devolviendo, en centavos enteros. */
  protected readonly valorCentavos = computed(() =>
    this.lineas().reduce(
      (suma, l) => suma + this.aCentavos(l.linea.precio_unitario) * l.cantidad,
      0,
    ),
  );

  protected readonly hayQueDevolver = computed(() =>
    this.lineas().some((l) => l.cantidad > 0),
  );

  /**
   * Si hay algo devolvible en esta venta.
   *
   * Una venta devuelta entera se busca igual y se encuentra igual: decir «ya se
   * devolvió toda» es una respuesta, y no encontrarla sería mentir.
   */
  protected readonly algoDevolvible = computed(() =>
    (this.venta()?.lineas ?? []).some((l) => l.devolvibles > 0),
  );

  /**
   * Si se puede registrar algo contra esta venta.
   *
   * Es lo que apaga los botones cuando la venta venció. La venta se sigue
   * mostrando: el cajero necesita el dato para explicárselo al cliente.
   */
  protected readonly dentroDePlazo = computed(
    () => this.venta()?.dentro_de_plazo ?? false,
  );

  /** Lo que vale lo que se lleva, con el descuento de CU-12 ya aplicado. */
  protected readonly totalLlevadoCentavos = computed(() =>
    this.llevadas().reduce(
      (suma, p) =>
        suma +
        (this.aCentavos(p.precio) - this.aCentavos(p.descuento_unitario)) * p.cantidad,
      0,
    ),
  );

  /** `total llevado − valor devuelto`, CON SIGNO. Positiva: paga el cliente. */
  protected readonly diferenciaCentavos = computed(
    () => this.totalLlevadoCentavos() - this.valorCentavos(),
  );

  /**
   * Quién pone la plata, en palabras.
   *
   * El servidor manda lo mismo en el comprobante, y por el mismo motivo: el
   * signo de un número es fácil de leer al revés cuando hay que decidir entre
   * cobrar y entregar con el cliente esperando.
   */
  protected readonly aFavorDe = computed<'CLIENTE' | 'TIENDA' | 'NADIE'>(() => {
    const d = this.diferenciaCentavos();
    if (d > 0) return 'CLIENTE';
    if (d < 0) return 'TIENDA';
    return 'NADIE';
  });

  protected readonly hayQueLlevar = computed(() =>
    this.llevadas().some((p) => p.cantidad > 0),
  );

  /**
   * Si el botón de confirmar puede apretarse.
   *
   * En un cambio hace falta, además de lo que vuelve, **algo que se lleve** y
   * —si la cuenta no sale pareja— el método por el que se salda. Sin esto, el
   * cajero descubre lo que falta recién con un 422 del servidor.
   */
  protected readonly sePuedeConfirmar = computed(() => {
    if (!this.dentroDePlazo() || !this.hayQueDevolver()) return false;
    if (this.modo() === 'DEVOLUCION') return true;
    if (!this.hayQueLlevar()) return false;
    return this.diferenciaCentavos() === 0 || !!this.metodoElegido();
  });

  ngOnInit(): void {
    this.caja.miTurno().subscribe({
      next: (t) => {
        this.hayTurno.set(t !== null);
        this.cargando.set(false);
      },
      error: () => {
        this.hayTurno.set(false);
        this.cargando.set(false);
      },
    });

    // La búsqueda de la prenda que se lleva. `switchMap` y no `mergeMap`: si el
    // cajero sigue tecleando, la respuesta de lo que escribió antes ya no le
    // sirve y, llegando tarde, pisaría la lista buena con una vieja.
    this.busqueda.valueChanges
      .pipe(
        debounceTime(300),
        distinctUntilChanged(),
        switchMap((texto) => {
          const limpio = texto.trim();
          if (limpio.length < 2) {
            this.buscandoPrendas.set(false);
            return of(null);
          }
          this.buscandoPrendas.set(true);
          return this.pos.prendas(limpio);
        }),
      )
      .subscribe({
        next: (pagina) => {
          this.buscandoPrendas.set(false);
          this.resultados.set(pagina?.items ?? []);
        },
        error: () => {
          this.buscandoPrendas.set(false);
          this.resultados.set([]);
        },
      });
  }

  protected elegirModo(modo: Modo): void {
    this.modo.set(modo);
    if (modo === 'DEVOLUCION') {
      // Se limpia lo del cambio al volver atrás: dejarlo cargado haría que una
      // devolución se registrara con prendas elegidas para otra cosa si el
      // cajero vuelve a cambiar de idea.
      this.llevadas.set([]);
      this.resultados.set([]);
      this.busqueda.setValue('');
      this.metodoDiferencia.setValue(null);
    }
  }

  protected agregar(prenda: PrendaEnMostrador): void {
    const ya = this.llevadas().find((p) => p.variante_id === prenda.variante_id);
    if (ya) {
      this.cantidadLlevada(ya, ya.cantidad + 1);
      return;
    }
    this.llevadas.set([
      ...this.llevadas(),
      {
        variante_id: prenda.variante_id,
        sku: prenda.sku,
        producto: prenda.producto,
        talla: prenda.talla,
        color: prenda.color,
        precio: prenda.precio,
        // El descuento de CU-12 tiene que llegar hasta acá o la cuenta de la
        // pantalla daría de más y el servidor rechazaría el cambio por
        // `diferencia_esperada` cada vez que la prenda esté en promoción.
        descuento_unitario: prenda.descuento?.monto_unitario ?? '0.00',
        cantidad: 1,
        disponible: prenda.disponible,
      },
    ]);
  }

  protected cantidadLlevada(prenda: PrendaQueSeLleva, cantidad: number): void {
    // El tope es lo que hay en la sucursal. El servidor lo comprueba igual, con
    // su bloqueo de fila; acá se evita que el cajero lo descubra pulsando.
    const nueva = Math.max(0, Math.min(cantidad, prenda.disponible));
    this.llevadas.set(
      nueva === 0
        ? this.llevadas().filter((p) => p.variante_id !== prenda.variante_id)
        : this.llevadas().map((p) =>
            p.variante_id === prenda.variante_id ? { ...p, cantidad: nueva } : p,
          ),
    );
  }

  protected quitar(prenda: PrendaQueSeLleva): void {
    this.llevadas.set(
      this.llevadas().filter((p) => p.variante_id !== prenda.variante_id),
    );
  }

  protected buscar(): void {
    if (this.codigo.invalid || this.buscando()) return;

    this.buscando.set(true);
    this.comprobante.set(null);
    this.comprobanteCambio.set(null);
    this.api.buscarVenta(this.codigo.value.trim()).subscribe({
      next: (venta) => {
        this.buscando.set(false);
        this.venta.set(venta);
        // Se arranca en cero y no en «todo»: devolver la venta entera es una
        // decisión, no el valor por omisión. Con todo marcado, un descuido
        // reingresa mercadería que el cliente no trajo.
        this.lineas.set(venta.lineas.map((linea) => ({ linea, cantidad: 0 })));
        // Cada venta arranca su propio trámite: lo elegido para la anterior no
        // tiene nada que ver con esta.
        this.elegirModo('DEVOLUCION');
      },
      error: (e: ErrorDevolucion) => {
        this.buscando.set(false);
        this.venta.set(null);
        this.lineas.set([]);
        this.manejar(e);
      },
    });
  }

  protected cambiar(fila: LineaEnDevolucion, cantidad: number): void {
    const tope = fila.linea.devolvibles;
    const nueva = Math.max(0, Math.min(cantidad, tope));
    this.lineas.set(
      this.lineas().map((l) =>
        l.linea.variante_id === fila.linea.variante_id ? { ...l, cantidad: nueva } : l,
      ),
    );
  }

  protected todo(): void {
    this.lineas.set(
      this.lineas().map((l) => ({ ...l, cantidad: l.linea.devolvibles })),
    );
  }

  protected registrar(): void {
    const venta = this.venta();
    if (!venta || !this.sePuedeConfirmar() || this.motivo.invalid || this.guardando()) {
      this.motivo.markAsTouched();
      return;
    }

    if (this.modo() === 'CAMBIO') {
      this.registrarCambio(venta);
      return;
    }

    this.guardando.set(true);
    this.api
      .registrar({
        venta_codigo: venta.codigo,
        motivo: this.motivo.value.trim(),
        lineas: this.lineas()
          .filter((l) => l.cantidad > 0)
          .map((l) => ({ variante_id: l.linea.variante_id, cantidad: l.cantidad })),
      })
      .subscribe({
        next: (comprobante) => {
          this.guardando.set(false);
          this.comprobante.set(comprobante);
          this.venta.set(null);
          this.lineas.set([]);
          this.motivo.setValue('');
          this.motivo.markAsUntouched();
          // El arqueo del turno acaba de cambiar si salió plata del cajón.
          this.caja.miTurno().subscribe({ error: () => undefined });
        },
        error: (e: ErrorDevolucion) => {
          this.guardando.set(false);
          this.manejar(e);
          // Si alguien devolvió lo mismo en el medio, la ficha quedó vieja.
          if (e.tipo === 'se-pasa') this.buscar();
        },
      });
  }

  protected otra(): void {
    this.comprobante.set(null);
    this.comprobanteCambio.set(null);
    this.codigo.setValue('');
  }

  private registrarCambio(venta: VentaDevolvible): void {
    this.guardando.set(true);
    const diferencia = this.diferenciaCentavos();

    this.api
      .registrarCambio({
        venta_codigo: venta.codigo,
        motivo: this.motivo.value.trim(),
        devueltas: this.lineas()
          .filter((l) => l.cantidad > 0)
          .map((l) => ({ variante_id: l.linea.variante_id, cantidad: l.cantidad })),
        llevadas: this.llevadas().map((p) => ({
          variante_id: p.variante_id,
          cantidad: p.cantidad,
        })),
        // Los dos campos se omiten cuando no corresponden en vez de mandarse en
        // cero o en nulo: el servidor rechaza un método contra una diferencia
        // de cero, y con razón —quedaría en la base diciendo que se movió plata
        // que no se movió—.
        ...(diferencia !== 0 && this.metodoElegido()
          ? { metodo_diferencia: this.metodoElegido() as string }
          : {}),
        diferencia_esperada: this.enBs(diferencia).toFixed(2),
      })
      .subscribe({
        next: (comprobante) => {
          this.guardando.set(false);
          this.comprobanteCambio.set(comprobante);
          this.venta.set(null);
          this.lineas.set([]);
          this.llevadas.set([]);
          this.resultados.set([]);
          this.busqueda.setValue('');
          this.metodoDiferencia.setValue(null);
          this.motivo.setValue('');
          this.motivo.markAsUntouched();
          this.modo.set('DEVOLUCION');
          // El arqueo del turno acaba de cambiar si la diferencia fue en
          // efectivo, y además salió una venta nueva.
          this.caja.miTurno().subscribe({ error: () => undefined });
        },
        error: (e: ErrorDevolucion) => {
          this.guardando.set(false);
          this.manejar(e);
          // Las dos obligan a releer: o alguien devolvió lo mismo en el medio,
          // o una promoción movió el precio de lo que se lleva.
          if (e.tipo === 'se-pasa' || e.tipo === 'diferencia-movida') this.buscar();
        },
      });
  }

  protected subtotalLlevado(prenda: PrendaQueSeLleva): number {
    return this.enBs(
      (this.aCentavos(prenda.precio) - this.aCentavos(prenda.descuento_unitario)) *
        prenda.cantidad,
    );
  }

  protected subtotalDe(fila: LineaEnDevolucion): number {
    return this.enBs(this.aCentavos(fila.linea.precio_unitario) * fila.cantidad);
  }

  protected enBs(centavos: number): number {
    return centavos / 100;
  }

  private manejar(e: ErrorDevolucion): void {
    if (e.tipo === 'sin-turno') {
      this.hayTurno.set(false);
      return;
    }
    if (e.tipo === 'fuera-de-plazo') {
      // Se marca la venta como vencida además de avisar: si solo se avisara,
      // los botones seguirían encendidos y el cajero volvería a intentarlo.
      const venta = this.venta();
      if (venta) this.venta.set({ ...venta, dentro_de_plazo: false });
    }
    this.aviso.open(e.mensaje, 'Entendido', { duration: 7000 });
  }

  /** El dinero se suma en centavos enteros, nunca en coma flotante. */
  private aCentavos(texto: string): number {
    return Math.round(Number(texto.replace(',', '.')) * 100);
  }
}
