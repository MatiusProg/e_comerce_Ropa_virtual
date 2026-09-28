import { CurrencyPipe, DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatCardModule } from '@angular/material/card';
import { MatDialog } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';

import { CajaService } from '../../../core/services/caja.service';
import { PosService, type ErrorPos } from '../../../core/services/pos.service';
import type {
  LineaEnCurso,
  MetodoDePago,
  PrendaEnMostrador,
  ReservaPorCobrar,
  Ticket,
} from '../../../core/models/pos.models';
import { CobroQr, type DatosCobroQrDialogo, type ResultadoCobroQr } from './cobro-qr';

/** Los tres estados de la pantalla. No hay dos a la vez. */
type Cara = 'armando' | 'cobrado';

/**
 * CU-31 · Registrar venta presencial — «boundary» PantallaVenta.
 *
 * TRES COSAS QUE ESTA PANTALLA HACE A PROPOSITO
 * ----------------------------------------------
 * **1. No deja cobrar sin turno abierto, y lo dice antes.** El servidor lo
 * rechaza igual —la base exige `turno_caja_id` en toda venta presencial—, pero
 * enterarse recién al pulsar «Cobrar», con el cliente esperando y el ticket
 * armado, es la peor manera de saberlo. El turno se consulta al entrar.
 *
 * **2. El total se calcula acá y se manda como `total_esperado`.** No para
 * confiar en él —el servidor recalcula y manda—, sino para que si el precio
 * cambió entre que la pantalla lo mostró y el cajero confirmó, el cobro se
 * detenga en vez de entregar un ticket por un importe distinto del que se le
 * dijo al cliente. Es la misma decisión que CU-27 tomó para el checkout.
 *
 * **3. El vuelto se muestra mientras se escribe.** Un cajero con billetes en la
 * mano no puede estar esperando a que el servidor le diga cuánto devolver.
 *
 * **4. Con QR, primero el banco y después la venta.** «Cobrar» abre el diálogo
 * del QR (`cobro-qr.ts`, una simulación del circuito bancario) y la venta se
 * registra solo si vuelve aprobado. Rechazado o vencido, no queda nada: ni
 * venta, ni stock descontado, ni movimiento en el turno.
 *
 * EL DINERO NO SE CONVIERTE A `number` PARA GUARDARLO
 * ----------------------------------------------------
 * Se suma en centavos enteros y se vuelve a texto con dos decimales. Sumar
 * `250.00 + 0.1 + 0.2` en coma flotante da `250.30000000000001`, y ese es
 * exactamente el centavo que el arqueo de CU-30 encuentra al cierre del turno.
 */
@Component({
  selector: 'app-venta',
  imports: [
    CurrencyPipe,
    DatePipe,
    RouterLink,
    ReactiveFormsModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatTooltipModule,
  ],
  templateUrl: './venta.html',
  styleUrl: './venta.scss',
})
export class Venta implements OnInit {
  private readonly api = inject(PosService);
  private readonly caja = inject(CajaService);
  private readonly aviso = inject(MatSnackBar);
  private readonly dialogo = inject(MatDialog);

  protected readonly cara = signal<Cara>('armando');
  protected readonly cargando = signal(true);
  protected readonly buscando = signal(false);
  protected readonly cobrando = signal(false);
  protected readonly error = signal<string | null>(null);

  /** Nulo mientras no se sabe; `false` manda a abrir caja. */
  protected readonly hayTurno = signal<boolean | null>(null);
  protected readonly turno = this.caja.turno;

  protected readonly origen = signal<'prendas' | 'reservas'>('prendas');

  protected readonly prendas = signal<PrendaEnMostrador[]>([]);
  protected readonly reservas = signal<ReservaPorCobrar[]>([]);

  /** El ticket que se está armando (camino A). */
  protected readonly lineas = signal<LineaEnCurso[]>([]);
  /** La reserva que se está cobrando (camino B). Excluyente con `lineas`. */
  protected readonly reserva = signal<ReservaPorCobrar | null>(null);

  protected readonly metodo = signal<MetodoDePago>('EFECTIVO');

  /**
   * Los tres métodos, en un campo y no en un literal dentro de la plantilla:
   * un `['EFECTIVO', …]` escrito ahí sería un arreglo nuevo en cada ciclo de
   * detección, y el `@for` volvería a dibujar los botones cada vez.
   */
  protected readonly metodos: readonly MetodoDePago[] = ['EFECTIVO', 'TARJETA', 'QR'];
  protected readonly ticket = signal<Ticket | null>(null);
  /** La referencia que devolvió el banco, si la venta se cobró con QR. */
  protected readonly referenciaQr = signal<string | null>(null);

  protected readonly busqueda = new FormControl('', { nonNullable: true });
  protected readonly recibido = new FormControl('', {
    nonNullable: true,
    validators: [Validators.pattern(/^\d+([.,]\d{1,2})?$/)],
  });

  /**
   * El total en centavos enteros, CON los descuentos de CU-12 aplicados.
   *
   * Tiene que coincidir con el del servidor: este número se manda como
   * `total_esperado` y CU-31 rechaza con 409 si no da. Sumando el precio de
   * lista, ninguna prenda en promoción se podría cobrar.
   */
  protected readonly totalCentavos = computed(() => {
    const r = this.reserva();
    // El total de la reserva ya viene con el descuento aplicado del servidor.
    if (r) return this.aCentavos(r.total);
    return this.lineas().reduce(
      (suma, l) => suma + this.unitarioCentavos(l.prenda) * l.cantidad,
      0,
    );
  });

  protected readonly total = computed(() => this.aTexto(this.totalCentavos()));
  protected readonly hayQueCobrar = computed(
    () => this.lineas().length > 0 || this.reserva() !== null,
  );

  /**
   * Lo escrito en «con cuánto paga», COMO SEÑAL.
   *
   * POR QUÉ NO SE LEE `recibido.value` DIRECTO EN EL `computed`
   * -----------------------------------------------------------
   * Porque el valor de un `FormControl` **no es una señal**: un `computed` que
   * lo lee no registra ninguna dependencia, no se invalida nunca y devuelve
   * para siempre lo que calculó la primera vez. El vuelto quedaba clavado en
   * nulo por más que el cajero escribiera, y nada avisaba — la pantalla se
   * dibuja igual, solo que con el número de antes.
   *
   * Lo encontró `venta.spec.ts`: tres comprobaciones que ponían un monto y
   * esperaban el vuelto recibían `null`. Sin esas pruebas el defecto llegaba
   * al mostrador.
   */
  private readonly loRecibido = toSignal(this.recibido.valueChanges, {
    initialValue: '',
  });

  /**
   * El vuelto, calculado mientras se escribe. Nulo si todavía no se puede.
   *
   * Solo con efectivo: dar vuelto por un cobro con tarjeta sería sacar plata
   * del cajón por un pago que no entró.
   */
  protected readonly vuelto = computed(() => {
    if (this.metodo() !== 'EFECTIVO') return null;
    const recibido = this.aCentavosSeguro(this.loRecibido());
    if (recibido === null) return null;
    return recibido - this.totalCentavos();
  });

  ngOnInit(): void {
    this.caja.miTurno().subscribe({
      next: (t) => {
        this.hayTurno.set(t !== null);
        this.cargando.set(false);
        if (t !== null) {
          this.cargarPrendas('');
          this.cargarReservas();
        }
      },
      error: () => {
        this.hayTurno.set(false);
        this.cargando.set(false);
      },
    });

    // Se escucha lo que se escribe con un respiro de 300 ms: una consulta por
    // tecla llenaría la red de peticiones que nadie llega a ver. La primera
    // carga la hace el `next` de arriba, no este flujo.
    this.busqueda.valueChanges
      .pipe(debounceTime(300), distinctUntilChanged())
      .subscribe((texto) => this.cargarPrendas(texto));
  }

  private cargarPrendas(texto: string): void {
    if (this.hayTurno() === false) return;
    this.buscando.set(true);
    this.api.prendas(texto, 1, 40).subscribe({
      next: (pagina) => {
        this.prendas.set(pagina.items);
        this.buscando.set(false);
      },
      error: (e: ErrorPos) => {
        this.buscando.set(false);
        this.manejar(e);
      },
    });
  }

  private cargarReservas(): void {
    this.api.reservasPorCobrar().subscribe({
      next: (filas) => this.reservas.set(filas),
      error: (e: ErrorPos) => this.manejar(e),
    });
  }

  // --- Armar el ticket ----------------------------------------------------

  protected agregar(prenda: PrendaEnMostrador): void {
    // Los dos caminos son excluyentes: el servidor rechaza los dos juntos y
    // tiene razón. Acá se avisa en vez de dejar armar algo que va a fallar.
    if (this.reserva()) {
      this.aviso.open(
        'Está cobrando una reserva. Suéltela antes de agregar otras prendas.',
        'Entendido',
        { duration: 5000 },
      );
      return;
    }

    const actuales = this.lineas();
    const yaEsta = actuales.find((l) => l.prenda.variante_id === prenda.variante_id);

    if (!yaEsta) {
      this.lineas.set([...actuales, { prenda, cantidad: 1 }]);
      return;
    }
    // Volver a pulsar una prenda ya agregada sube la cantidad; no la duplica.
    // `detalle_venta` tiene UNIQUE (venta_id, variante_id) y dos líneas de la
    // misma prenda reventarían con un error de integridad.
    this.cambiarCantidad(yaEsta, yaEsta.cantidad + 1);
  }

  protected cambiarCantidad(linea: LineaEnCurso, cantidad: number): void {
    if (cantidad <= 0) {
      this.quitar(linea);
      return;
    }
    if (cantidad > linea.prenda.disponible) {
      this.aviso.open(
        `De «${linea.prenda.producto}» quedan ${linea.prenda.disponible}.`,
        'Entendido',
        { duration: 4000 },
      );
      return;
    }
    this.lineas.set(
      this.lineas().map((l) =>
        l.prenda.variante_id === linea.prenda.variante_id ? { ...l, cantidad } : l,
      ),
    );
  }

  protected quitar(linea: LineaEnCurso): void {
    this.lineas.set(
      this.lineas().filter((l) => l.prenda.variante_id !== linea.prenda.variante_id),
    );
  }

  protected cargarReserva(fila: ReservaPorCobrar): void {
    if (this.lineas().length) {
      this.aviso.open(
        'Termine o vacíe el ticket antes de cargar una reserva.',
        'Entendido',
        { duration: 5000 },
      );
      return;
    }
    this.reserva.set(fila);
    this.origen.set('prendas');
  }

  protected soltarReserva(): void {
    this.reserva.set(null);
  }

  protected vaciar(): void {
    this.lineas.set([]);
    this.reserva.set(null);
    this.recibido.setValue('');
  }

  protected elegirMetodo(metodo: MetodoDePago): void {
    this.metodo.set(metodo);
    // Con tarjeta o QR se cobra el importe exacto: el campo deja de tener
    // sentido y quedaría mintiendo con un valor viejo.
    if (metodo !== 'EFECTIVO') this.recibido.setValue('');
  }

  // --- Cobrar -------------------------------------------------------------

  protected cobrar(): void {
    if (!this.hayQueCobrar() || this.cobrando() || this.recibido.invalid) return;
    if (this.vuelto() !== null && this.vuelto()! < 0) return;

    if (this.metodo() === 'QR') {
      this.cobrarConQr();
      return;
    }
    this.registrar(null);
  }

  /**
   * Abre el QR y espera la respuesta del banco. Mientras el diálogo está
   * abierto `cobrando` queda en alto: un segundo clic en «Cobrar» no abre un
   * segundo QR por la misma venta.
   */
  private cobrarConQr(): void {
    const turno = this.turno();
    this.cobrando.set(true);
    this.dialogo
      .open<CobroQr, DatosCobroQrDialogo, ResultadoCobroQr>(CobroQr, {
        data: {
          total: this.total(),
          sucursal: turno?.sucursal_nombre ?? '',
          caja: turno?.caja_nombre ?? '',
        },
        // Un clic fuera del diálogo no puede tirar un cobro que el cliente
        // quizá ya está pagando desde su teléfono.
        disableClose: true,
        autoFocus: false,
        // Ancho fijo: el contenido cambia con cada estado y, sin esto, el
        // diálogo se achica y se agranda delante del cliente. Alcanza para que
        // el QR se lea desde un teléfono al otro lado del mostrador.
        width: '26rem',
        maxWidth: '95vw',
      })
      .afterClosed()
      .subscribe((referencia) => {
        this.cobrando.set(false);
        if (!referencia) {
          this.aviso.open(
            'El cobro con QR no se completó. No se registró ninguna venta.',
            'Entendido',
            { duration: 6000 },
          );
          return;
        }
        this.registrar(referencia);
      });
  }

  /**
   * Registra la venta en el servidor. `referenciaQr` viene solo si se cobró
   * con QR y el banco ya aprobó.
   */
  private registrar(referenciaQr: string | null): void {
    this.cobrando.set(true);
    this.error.set(null);

    const reserva = this.reserva();
    const recibido = this.aCentavosSeguro(this.recibido.value);

    this.api
      .cobrar({
        metodo_pago: this.metodo(),
        ...(reserva
          ? { reserva_id: reserva.reserva_id }
          : {
              lineas: this.lineas().map((l) => ({
                variante_id: l.prenda.variante_id,
                cantidad: l.cantidad,
              })),
            }),
        total_esperado: this.total(),
        ...(this.metodo() === 'EFECTIVO' && recibido !== null
          ? { monto_recibido: this.aTexto(recibido) }
          : {}),
      })
      .subscribe({
        next: (ticket) => {
          this.cobrando.set(false);
          this.ticket.set(ticket);
          this.referenciaQr.set(referenciaQr);
          this.cara.set('cobrado');
          this.lineas.set([]);
          this.reserva.set(null);
          this.recibido.setValue('');
          // El arqueo del turno acaba de cambiar: si el cajero va a «Mi turno»
          // sin recargar, tiene que ver el efectivo nuevo y no el de antes.
          this.caja.miTurno().subscribe({ error: () => undefined });
        },
        error: (e: ErrorPos) => {
          this.cobrando.set(false);
          if (referenciaQr) {
            // El caso incómodo: el banco ya cobró y la venta no entró (se
            // acabó el stock, cambió un precio). El cajero tiene que saberlo
            // con la referencia en la mano, para anular ese cobro y no dejar
            // al cliente pagando por una prenda que no se lleva.
            this.aviso.open(
              `El QR ${referenciaQr} quedó APROBADO pero la venta no se registró: ` +
                `${e.mensaje} Anule ese cobro antes de volver a intentar.`,
              'Entendido',
            );
          } else {
            this.manejar(e);
          }
          // Si el precio cambió o se acabó el stock, la lista quedó vieja: se
          // vuelve a pedir en vez de dejarla mintiendo.
          if (e.tipo === 'precio-cambio' || e.tipo === 'sin-stock') {
            this.cargarPrendas(this.busqueda.value);
          }
          if (e.tipo === 'no-existe' && this.reserva()) {
            this.soltarReserva();
            this.cargarReservas();
          }
        },
      });
  }

  protected nuevaVenta(): void {
    this.ticket.set(null);
    this.referenciaQr.set(null);
    this.cara.set('armando');
    this.metodo.set('EFECTIVO');
    this.cargarPrendas(this.busqueda.value);
    this.cargarReservas();
  }

  protected imprimir(): void {
    const t = this.ticket();
    if (!t) return;
    this.api.comprobante(t.codigo).subscribe({
      next: (blob) => {
        // Se abre con un enlace temporal y no con `window.open(url)` directo:
        // el PDF necesita el token en la cabecera, y una ventana nueva que
        // pida la URL por su cuenta iría sin él y recibiría un 401.
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank');
        // No se revoca en el acto: la pestaña todavía no terminó de leerlo.
        setTimeout(() => URL.revokeObjectURL(url), 60_000);
      },
      error: (e: ErrorPos) => this.manejar(e),
    });
  }

  // --- Utilidades ---------------------------------------------------------

  private manejar(e: ErrorPos): void {
    if (e.tipo === 'sin-turno') {
      this.hayTurno.set(false);
      return;
    }
    this.aviso.open(e.mensaje, 'Entendido', { duration: 7000 });
  }

  /** De «250.00» a 25000. El dinero se suma en enteros, nunca en coma flotante. */
  private aCentavos(texto: string): number {
    return Math.round(Number(texto.replace(',', '.')) * 100);
  }

  /** Igual, pero devuelve nulo si lo escrito todavía no es un monto. */
  private aCentavosSeguro(texto: string): number | null {
    const limpio = texto.trim().replace(',', '.');
    if (!/^\d+(\.\d{1,2})?$/.test(limpio)) return null;
    return Math.round(Number(limpio) * 100);
  }

  private aTexto(centavos: number): string {
    return (centavos / 100).toFixed(2);
  }

  /** Para el `currency` de la plantilla, que sí necesita un número. */
  protected enBs(centavos: number): number {
    return centavos / 100;
  }

  /** El subtotal de una línea del ticket, en Bs, sumado en centavos enteros. */
  protected subtotalDe(linea: LineaEnCurso): number {
    return this.enBs(this.unitarioCentavos(linea.prenda) * linea.cantidad);
  }

  /** Lo que se cobra por unidad: con el descuento de CU-12 si lo tiene. */
  private unitarioCentavos(prenda: PrendaEnMostrador): number {
    return this.aCentavos(prenda.descuento?.precio_final ?? prenda.precio);
  }


  protected iconoDe(metodo: MetodoDePago): string {
    if (metodo === 'EFECTIVO') return 'payments';
    return metodo === 'TARJETA' ? 'credit_card' : 'qr_code_2';
  }

  protected nombreDe(metodo: MetodoDePago): string {
    if (metodo === 'EFECTIVO') return 'Efectivo';
    return metodo === 'TARJETA' ? 'Tarjeta' : 'QR';
  }
}
