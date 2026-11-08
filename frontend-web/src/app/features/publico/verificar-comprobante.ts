import { Component, OnInit, inject, input, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import {
  MisComprobantesService,
  type VerificacionComprobante,
} from '../../core/services/mis-comprobantes.service';
import { BsPipe } from '../../shared/bs.pipe';

const DOCUMENTOS: Record<string, string> = {
  RECIBO: 'Recibo de compra',
  NOTA_DEVOLUCION: 'Nota de devolución',
  NOTA_CAMBIO: 'Nota de cambio',
};

const ESTADOS: Record<string, string> = {
  PAGADA: 'Pagada',
  ENTREGADA: 'Entregada',
  CANCELADA: 'Cancelada',
  ABIERTA: 'Abierta',
  CERRADA: 'Cerrada',
};

/**
 * CU-46 · La página que abre el QR de un comprobante. **Pública**, sin sesión.
 *
 * Muestra solo lo que sirve para comprobar que el papel es auténtico: la
 * tienda, el número, la fecha, el total y el estado. Nada del cliente. El
 * token del camino es una firma del servidor: si alguien lo altera, la página
 * dice que el comprobante no existe.
 *
 * El botón «Imprimir / guardar PDF» usa el diálogo del navegador: es la forma
 * de exportar también una nota de devolución, que no tiene PDF propio.
 */
@Component({
  selector: 'app-verificar-comprobante',
  imports: [BsPipe, MatButtonModule, MatIconModule, MatProgressBarModule],
  template: `
    <main class="pagina">
      <section class="hoja">
        <p class="marca vb-titulo">Verificación de comprobante</p>
        @if (cargando()) {
          <mat-progress-bar mode="indeterminate" aria-label="Verificando" />
        } @else if (datos(); as d) {
          <div class="sello valido">
            <mat-icon>verified</mat-icon>
            <span>Comprobante auténtico</span>
          </div>
          <h1>{{ d.codigo }}</h1>
          <p class="tienda">{{ documento(d) }} · {{ d.tienda }}</p>
          <dl>
            <dt>Fecha</dt>
            <dd>{{ d.fecha_texto }}</dd>
            <dt>Pedido</dt>
            <dd>{{ d.referencia }}</dd>
            <dt>Total</dt>
            <dd class="total">{{ d.total | bs }}</dd>
            <dt>Estado</dt>
            <dd>{{ estado(d) }}</dd>
          </dl>
          <img class="qr" [src]="qr()" alt="Código QR de este comprobante" />
          <button matButton="outlined" type="button" class="no-imprimir" (click)="imprimir()">
            <mat-icon>print</mat-icon>
            Imprimir / guardar PDF
          </button>
          <p class="nota">Hora de Bolivia. Documento sin validez fiscal.</p>
        } @else {
          <div class="sello invalido" role="alert">
            <mat-icon>gpp_bad</mat-icon>
            <span>{{ error() }}</span>
          </div>
          <p class="nota">
            Si escaneaste el código de un comprobante impreso, revisá que esté completo.
          </p>
        }
      </section>
    </main>
  `,
  styles: `
    .pagina {
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: 1.5rem 1rem;
      background: var(--vb-degradado-suave);
    }
    .hoja {
      width: min(100%, 420px);
      background: #fff;
      border-radius: var(--vb-radio);
      box-shadow: var(--vb-sombra-elevada);
      padding: 1.75rem 1.5rem;
      text-align: center;
      border-top: 4px solid var(--vb-oro);
    }
    .marca {
      margin: 0 0 1rem;
      color: var(--vb-malva-oscuro);
      font-size: 1.15rem;
    }
    h1 {
      margin: 0.75rem 0 0.15rem;
      font-size: 1.6rem;
      font-variant-numeric: tabular-nums;
      color: var(--vb-tinta);
    }
    .tienda {
      margin: 0 0 1rem;
      color: var(--mat-sys-on-surface-variant);
    }
    .sello {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.35rem 0.85rem;
      border-radius: 999px;
      font-weight: 600;
    }
    .valido {
      background: #e3f3ea;
      color: #2e7d55;
    }
    .invalido {
      background: color-mix(in srgb, var(--mat-sys-error) 12%, transparent);
      color: var(--mat-sys-error);
    }
    dl {
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 0.4rem 1rem;
      text-align: left;
      margin: 0 0 1rem;
    }
    dt {
      color: var(--mat-sys-on-surface-variant);
    }
    dd {
      margin: 0;
      font-weight: 600;
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
    .total {
      font-size: 1.15rem;
      color: var(--vb-malva-oscuro);
    }
    .qr {
      width: 140px;
      height: 140px;
      display: block;
      margin: 0 auto 1rem;
    }
    .nota {
      margin: 1rem 0 0;
      font-size: 0.8rem;
      color: var(--mat-sys-on-surface-variant);
    }
    @media print {
      .no-imprimir {
        display: none;
      }
      .pagina {
        background: #fff;
      }
      .hoja {
        box-shadow: none;
      }
    }
  `,
})
export class VerificarComprobante implements OnInit {
  private readonly api = inject(MisComprobantesService);

  /** Del camino `/verificar/:token` (withComponentInputBinding). */
  readonly token = input.required<string>();

  protected readonly cargando = signal(true);
  protected readonly datos = signal<VerificacionComprobante | null>(null);
  protected readonly error = signal('');

  ngOnInit(): void {
    this.api.verificar(this.token()).subscribe({
      next: (d) => {
        this.datos.set(d);
        this.cargando.set(false);
      },
      error: (mensaje: string) => {
        this.error.set(mensaje);
        this.cargando.set(false);
      },
    });
  }

  protected qr(): string {
    return this.api.urlQr(this.token());
  }

  protected documento(d: VerificacionComprobante): string {
    return DOCUMENTOS[d.documento] ?? d.documento;
  }

  protected estado(d: VerificacionComprobante): string {
    return ESTADOS[d.estado] ?? d.estado;
  }

  protected imprimir(): void {
    window.print();
  }
}
