import { Component, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';

import { ComprasService, type ErrorCompras } from '../../../core/services/compras.service';
import { DictadoService } from '../../../core/services/dictado.service';
import {
  MisComprobantesService,
  type ComprobanteCliente,
  type ResultadoComprobantes,
} from '../../../core/services/mis-comprobantes.service';
import { BsPipe, formatoBs } from '../../../shared/bs.pipe';
import { NavegacionCliente } from '../../../shared/navegacion-cliente/navegacion-cliente';

/** Cómo se lee cada estado en la tarjeta. */
const ESTADOS: Record<string, string> = {
  PAGADA: 'Pagada',
  ENTREGADA: 'Entregada',
  PENDIENTE_PAGO: 'Pendiente de pago',
  CANCELADA: 'Cancelada',
  ABIERTA: 'Abierta',
  CERRADA: 'Cerrada',
};

const DOCUMENTOS: Record<string, string> = {
  RECIBO: 'Recibo',
  NOTA_DEVOLUCION: 'Nota de devolución',
  NOTA_CAMBIO: 'Nota de cambio',
};

/**
 * CU-46 · Consultar mis comprobantes por voz — el «reporte transaccional».
 *
 * El cliente pide con sus palabras («mis últimas 3 compras», «mis recibos de
 * octubre», «mis devoluciones»), escribiendo o dictando, y recibe sus
 * comprobantes en tarjetas, cada una con su QR de verificación.
 *
 * Es el mismo patrón que CU-27 (reportes con IA): el dictado lo hace el
 * navegador con Web Speech API (`DictadoService`), y el servidor interpreta la
 * frase. La diferencia es que acá **no hay IA**: el servidor usa solo reglas,
 * para no gastar el cupo de la tienda en las consultas de los clientes.
 */
@Component({
  selector: 'app-mis-comprobantes',
  imports: [
    ReactiveFormsModule,
    RouterLink,
    NavegacionCliente,
    BsPipe,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatTooltipModule,
  ],
  templateUrl: './mis-comprobantes.html',
  styleUrl: './mis-comprobantes.scss',
})
export class MisComprobantes {
  private readonly api = inject(MisComprobantesService);
  private readonly compras = inject(ComprasService);
  private readonly aviso = inject(MatSnackBar);
  protected readonly dictado = inject(DictadoService);

  protected readonly pedido = new FormControl('', {
    nonNullable: true,
    validators: [Validators.required, Validators.minLength(2), Validators.maxLength(300)],
  });

  protected readonly consultando = signal(false);
  protected readonly resultado = signal<ResultadoComprobantes | null>(null);
  protected readonly descargando = signal<string | null>(null);

  protected readonly ejemplos = [
    'Mis últimas 3 compras',
    'Mis recibos de octubre',
    'Mis devoluciones',
    'Mis compras del mes pasado',
    'Todos mis comprobantes de este año',
  ];

  protected estado(c: ComprobanteCliente): string {
    return ESTADOS[c.estado] ?? c.estado;
  }

  protected documento(c: ComprobanteCliente): string {
    return c.documento ? DOCUMENTOS[c.documento] ?? c.documento : 'Pedido sin pagar';
  }

  protected qr(token: string): string {
    return this.api.urlQr(token);
  }

  protected usarEjemplo(frase: string): void {
    this.pedido.setValue(frase);
    this.consultar();
  }

  protected hablar(): void {
    if (this.dictado.escuchando()) {
      this.dictado.detener();
      return;
    }
    this.dictado.escuchar((frase) => {
      this.pedido.setValue(frase);
      this.consultar();
    });
  }

  protected consultar(): void {
    const texto = this.pedido.value.trim();
    if (texto.length < 2 || this.consultando()) {
      this.pedido.markAsTouched();
      return;
    }
    this.consultando.set(true);
    this.api.consultar(texto).subscribe({
      next: (r) => {
        this.consultando.set(false);
        this.resultado.set(r);
      },
      error: (mensaje: string) => {
        this.consultando.set(false);
        this.aviso.open(mensaje, 'Cerrar', { duration: 7000 });
      },
    });
  }

  /** El PDF del recibo: el mismo endpoint de «Mis compras» (CU-29). */
  protected descargar(c: ComprobanteCliente): void {
    if (!c.descargable || this.descargando()) return;
    this.descargando.set(c.referencia);
    this.compras.comprobante(c.referencia).subscribe({
      next: (blob) => {
        this.guardar(blob, `${c.codigo}.pdf`);
        this.descargando.set(null);
      },
      error: (e: ErrorCompras) => {
        this.descargando.set(null);
        this.aviso.open(e.mensaje, 'Entendido', { duration: 6000 });
      },
    });
  }

  /**
   * Exporta la lista a CSV (se abre en Excel). Se arma en el navegador con lo
   * que ya está en pantalla: no hace falta otra consulta al servidor.
   */
  protected exportar(): void {
    const r = this.resultado();
    if (!r?.items.length) return;
    const filas = [
      ['Tipo', 'Documento', 'Código', 'Pedido', 'Fecha', 'Total (Bs)', 'Estado', 'Verificación'],
      ...r.items.map((c) => [
        c.tipo === 'COMPRA' ? 'Compra' : 'Devolución',
        this.documento(c),
        c.codigo,
        c.referencia,
        c.fecha_texto,
        formatoBs(c.total).replace('Bs ', ''),
        this.estado(c),
        c.url_verificacion ?? '',
      ]),
    ];
    const csv = filas
      .map((fila) => fila.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(';'))
      .join('\r\n');
    // El BOM hace que Excel lea bien las tildes.
    this.guardar(new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' }), 'mis-comprobantes.csv');
  }

  private guardar(blob: Blob, nombre: string): void {
    const url = URL.createObjectURL(blob);
    const enlace = document.createElement('a');
    enlace.href = url;
    enlace.download = nombre;
    enlace.click();
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  }
}
