import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';

import { OfflineService } from '../../../core/services/offline.service';
import type { MetodoOffline, OperacionDeSucursal } from '../../../core/models/offline.models';
import { BsPipe } from '../../../shared/bs.pipe';

/**
 * CU-19 · Atender operaciones rechazadas y devolver el dinero.
 * «boundary» PantallaRechazadas. Solo web, del Encargado.
 *
 * Una venta hecha sin conexión que el servidor rechazó (otra llegó primero y
 * se llevó la última unidad, RN-06) ya se cobró: el cliente pagó por una
 * prenda que no puede llevarse. Esta pantalla es donde eso se cierra.
 *
 * NO SE TOCA LA CAJA: la venta rechazada nunca entró al arqueo, así que el
 * billete que se devuelve es justamente el que sobraba en el cajón.
 */
@Component({
  selector: 'app-rechazadas',
  imports: [
    BsPipe,
    DatePipe,
    ReactiveFormsModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
  ],
  templateUrl: './rechazadas.html',
  styleUrl: './rechazadas.scss',
})
export class Rechazadas implements OnInit {
  private readonly offline = inject(OfflineService);
  private readonly aviso = inject(MatSnackBar);

  protected readonly cargando = signal(true);
  protected readonly vista = signal<'por-devolver' | 'todas'>('por-devolver');
  protected readonly filas = signal<OperacionDeSucursal[]>([]);

  /** La que se está devolviendo; una a la vez. */
  protected readonly abierta = signal<string | null>(null);
  protected readonly metodo = signal<MetodoOffline>('EFECTIVO');
  protected readonly guardando = signal(false);
  protected readonly referencia = new FormControl('', { nonNullable: true });
  protected readonly observacion = new FormControl('', { nonNullable: true });

  ngOnInit(): void {
    this.cargar();
  }

  protected cambiarVista(vista: 'por-devolver' | 'todas'): void {
    this.vista.set(vista);
    this.cargar();
  }

  private cargar(): void {
    this.cargando.set(true);
    this.offline.deSucursal(this.vista() === 'por-devolver').subscribe({
      next: (filas) => {
        this.filas.set(filas);
        this.cargando.set(false);
      },
      error: (e: HttpErrorResponse) => {
        this.cargando.set(false);
        this.mostrar(e, 'No se pudieron leer las operaciones.');
      },
    });
  }

  protected abrir(fila: OperacionDeSucursal): void {
    this.abierta.set(fila.uuid);
    // Por omisión, se devuelve por el mismo medio por el que se cobró.
    this.metodo.set(fila.metodo_pago === 'QR' ? 'QR' : 'EFECTIVO');
    this.referencia.setValue('');
    this.observacion.setValue('');
  }

  protected devolver(fila: OperacionDeSucursal): void {
    const referencia = this.referencia.value.trim();
    if (this.metodo() === 'QR' && !referencia) {
      this.aviso.open('Anote la referencia de la transferencia de devolución.', 'Entendido', {
        duration: 5000,
      });
      return;
    }
    this.guardando.set(true);
    this.offline
      .registrarDevolucion(fila.uuid, {
        metodo: this.metodo(),
        referencia: referencia || null,
        observacion: this.observacion.value.trim() || null,
      })
      .subscribe({
        next: () => {
          this.guardando.set(false);
          this.abierta.set(null);
          this.aviso.open(`Devolución de ${fila.monto_cobrado} Bs registrada.`, 'Entendido', {
            duration: 5000,
          });
          this.cargar();
        },
        error: (e: HttpErrorResponse) => {
          this.guardando.set(false);
          this.mostrar(e, 'No se pudo registrar la devolución.');
          this.cargar();
        },
      });
  }

  private mostrar(e: HttpErrorResponse, porOmision: string): void {
    const texto = typeof e.error?.detail === 'string' ? e.error.detail : porOmision;
    this.aviso.open(texto, 'Entendido', { duration: 7000 });
  }
}
