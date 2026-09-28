import { CurrencyPipe } from '@angular/common';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { encode } from 'uqr';

import { contenidoQr, nuevaReferencia } from './qr-emv';

export interface DatosCobroQrDialogo {
  /** El total exacto a cobrar, «250.00». */
  total: string;
  sucursal: string;
  caja: string;
}

/**
 * Lo que devuelve el diálogo: la referencia del banco si el pago se aprobó, o
 * `null` si se rechazó, venció o el cajero desistió. Con `null` NO se registra
 * ninguna venta.
 */
export type ResultadoCobroQr = string | null;

type Estado = 'esperando' | 'confirmando' | 'aprobado' | 'rechazado' | 'vencido';

/** Cuánto vale un QR antes de vencer, en segundos. */
export const VIGENCIA_QR_S = 120;

/** Lo que tarda el «banco» en contestar. Da tiempo a leer el estado. */
const DEMORA_BANCO_MS = 1500;

/** Lo que se muestra el «aprobado» antes de cerrar y registrar la venta. */
const PAUSA_APROBADO_MS = 1200;

/** Motivos con los que un banco rechaza un pago QR. */
const MOTIVOS_RECHAZO = [
  'Fondos insuficientes en la cuenta del cliente.',
  'El cliente canceló el pago desde su aplicación.',
  'La cuenta del cliente superó su límite diario.',
];

/**
 * CU-31 · Cobro con QR — SIMULACIÓN del circuito bancario.
 *
 * CÓMO FUNCIONA UN COBRO QR DE VERDAD
 * -----------------------------------
 * 1. La caja genera un QR **dinámico**: lleva el monto y una referencia única.
 * 2. El cliente lo escanea con la aplicación de su banco y confirma.
 * 3. El banco **devuelve aprobación o rechazo** a la caja, con la referencia.
 * 4. Recién con la aprobación la caja entrega la prenda.
 *
 * QUÉ ES REAL Y QUÉ ES SIMULADO
 * -----------------------------
 * El código es real: sigue el formato EMVCo (`qr-emv.ts`) y cualquier lector
 * de QR lo decodifica. Lo simulado es el banco. En su lugar, esta pantalla
 * ofrece dos botones —«el cliente pagó» y «el banco rechazó»— que hacen lo que
 * haría la respuesta del banco. Integrar un banco real exige un convenio
 * comercial, igual que Libélula (ver `docs/06-decisiones-tecnicas.md`).
 *
 * LA REGLA QUE IMPORTA
 * --------------------
 * **La venta se registra DESPUÉS de la aprobación, nunca antes.** Si el banco
 * rechaza o el QR vence, no queda venta, no se descuenta stock y el turno no
 * cambia. Por eso el diálogo no llama al servidor: solo devuelve la referencia,
 * y es `Venta` quien registra la venta cuando la recibe.
 */
@Component({
  selector: 'app-cobro-qr',
  imports: [
    CurrencyPipe,
    MatButtonModule,
    MatDialogModule,
    MatIconModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './cobro-qr.html',
  styleUrl: './cobro-qr.scss',
})
export class CobroQr {
  protected readonly ref = inject(MatDialogRef<CobroQr, ResultadoCobroQr>);
  protected readonly datos = inject<DatosCobroQrDialogo>(MAT_DIALOG_DATA);

  protected readonly estado = signal<Estado>('esperando');
  protected readonly referencia = signal(nuevaReferencia());
  protected readonly restante = signal(VIGENCIA_QR_S);
  protected readonly motivo = signal('');

  /** La cadena EMVCo. Cambia con la referencia: cada intento es un QR nuevo. */
  protected readonly contenido = computed(() =>
    contenidoQr({
      monto: this.datos.total,
      referencia: this.referencia(),
      sucursal: this.datos.sucursal,
      caja: this.datos.caja,
    }),
  );

  /**
   * El QR como un solo `path` de SVG: un cuadradito por módulo oscuro.
   *
   * Se dibuja así y no con `innerHTML`: Angular sanea el HTML que entra por
   * ahí y borra los `<svg>`, y saltearse el saneado para un dibujo que se
   * puede armar con atributos sería abrir una puerta sin necesidad.
   */
  protected readonly qr = computed(() => {
    // Corrección M: el QR se sigue leyendo con un reflejo sobre la pantalla.
    const { data, size } = encode(this.contenido(), { ecc: 'M', border: 2 });
    let d = '';
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        if (data[y][x]) d += `M${x} ${y}h1v1h-1z`;
      }
    }
    return { d, size };
  });

  /** «1:45». */
  protected readonly reloj = computed(() => {
    const s = this.restante();
    return `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`;
  });

  protected readonly porcentaje = computed(() => (this.restante() / VIGENCIA_QR_S) * 100);

  private intervalo: ReturnType<typeof setInterval> | null = null;
  private espera: ReturnType<typeof setTimeout> | null = null;

  constructor() {
    this.arrancarReloj();
    // Si el diálogo se cierra por cualquier lado, que no quede un reloj
    // corriendo ni una respuesta del «banco» por llegar a un diálogo muerto.
    inject(DestroyRef).onDestroy(() => this.detener());
  }

  /** Hace de banco: el cliente escaneó y confirmó en su aplicación. */
  protected simularPago(): void {
    if (this.estado() !== 'esperando') return;
    this.pararReloj();
    this.estado.set('confirmando');
    this.espera = setTimeout(() => {
      this.estado.set('aprobado');
      this.espera = setTimeout(() => this.ref.close(this.referencia()), PAUSA_APROBADO_MS);
    }, DEMORA_BANCO_MS);
  }

  /** Hace de banco: el pago no pasó. */
  protected simularRechazo(): void {
    if (this.estado() !== 'esperando') return;
    this.pararReloj();
    this.estado.set('confirmando');
    this.espera = setTimeout(() => {
      this.motivo.set(MOTIVOS_RECHAZO[Math.floor(Math.random() * MOTIVOS_RECHAZO.length)]);
      this.estado.set('rechazado');
    }, DEMORA_BANCO_MS);
  }

  /**
   * Otro intento con un QR NUEVO. No se reusa la referencia: un QR dinámico
   * vale para un solo cobro, y reusarlo permitiría pagar dos veces lo mismo.
   */
  protected reintentar(): void {
    this.detener();
    this.referencia.set(nuevaReferencia());
    this.restante.set(VIGENCIA_QR_S);
    this.motivo.set('');
    this.estado.set('esperando');
    this.arrancarReloj();
  }

  protected desistir(): void {
    this.ref.close(null);
  }

  private arrancarReloj(): void {
    this.intervalo = setInterval(() => {
      const s = this.restante() - 1;
      this.restante.set(Math.max(s, 0));
      if (s <= 0) {
        this.pararReloj();
        this.estado.set('vencido');
      }
    }, 1000);
  }

  private pararReloj(): void {
    if (this.intervalo !== null) clearInterval(this.intervalo);
    this.intervalo = null;
  }

  private detener(): void {
    this.pararReloj();
    if (this.espera !== null) clearTimeout(this.espera);
    this.espera = null;
  }
}
