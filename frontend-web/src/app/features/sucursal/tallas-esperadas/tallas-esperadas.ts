import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import {
  AvisosTallaService,
  type DemandaTalla,
  type ErrorAvisoTalla,
} from '../../../core/services/avisos-talla.service';

/**
 * Aporte propio · «Tallas esperadas»: las tallas y colores agotados que hay
 * clientes esperando, lo más pedido primero. Es demanda que hoy no se puede
 * vender: le dice al encargado qué pedir por traspaso o reponer primero, y al
 * administrador qué comprar más.
 */
@Component({
  selector: 'app-tallas-esperadas',
  imports: [DatePipe, MatButtonModule, MatCardModule, MatIconModule, MatProgressBarModule],
  templateUrl: './tallas-esperadas.html',
  styleUrl: './tallas-esperadas.scss',
})
export class TallasEsperadas implements OnInit {
  private readonly api = inject(AvisosTallaService);

  protected readonly cargando = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly filas = signal<DemandaTalla[]>([]);
  protected readonly totalClientes = computed(() =>
    this.filas().reduce((suma, f) => suma + f.clientes, 0),
  );

  ngOnInit(): void {
    this.cargar();
  }

  protected cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.api.demanda().subscribe({
      next: (filas) => {
        this.filas.set(filas);
        this.cargando.set(false);
      },
      error: (e: ErrorAvisoTalla) => {
        this.error.set(e.mensaje);
        this.cargando.set(false);
      },
    });
  }
}
