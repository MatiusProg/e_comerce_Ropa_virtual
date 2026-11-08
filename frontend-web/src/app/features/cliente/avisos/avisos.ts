import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';
import { RouterLink } from '@angular/router';

import {
  AvisosTallaService,
  type AvisoTalla,
  type ErrorAvisoTalla,
} from '../../../core/services/avisos-talla.service';
import { NavegacionCliente } from '../../../shared/navegacion-cliente/navegacion-cliente';

/**
 * Aporte propio · «Mis avisos»: las tallas que el cliente está esperando y las
 * que ya llegaron en los últimos 30 días. Desde acá se cancela un aviso.
 */
@Component({
  selector: 'app-mis-avisos',
  imports: [
    DatePipe,
    NavegacionCliente,
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatProgressBarModule,
  ],
  templateUrl: './avisos.html',
  styleUrl: './avisos.scss',
})
export class MisAvisos implements OnInit {
  private readonly api = inject(AvisosTallaService);
  private readonly snack = inject(MatSnackBar);

  protected readonly cargando = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly avisos = signal<AvisoTalla[]>([]);
  protected readonly cancelando = signal<number | null>(null);

  ngOnInit(): void {
    this.cargar();
  }

  protected foto(a: AvisoTalla): string | null {
    return this.api.urlDeImagen(a.imagen_url);
  }

  protected cancelar(a: AvisoTalla): void {
    if (this.cancelando() !== null) return;
    this.cancelando.set(a.id);
    this.api.cancelar(a.id).subscribe({
      next: () => {
        this.cancelando.set(null);
        this.avisos.set(this.avisos().filter((x) => x.id !== a.id));
        this.snack.open('Aviso cancelado.', 'Cerrar', { duration: 4000 });
      },
      error: (e: ErrorAvisoTalla) => {
        this.cancelando.set(null);
        this.snack.open(e.mensaje, 'Cerrar', { duration: 6000 });
        this.cargar();
      },
    });
  }

  private cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.api.misAvisos().subscribe({
      next: (lista) => {
        this.avisos.set(lista);
        this.cargando.set(false);
      },
      error: (e: ErrorAvisoTalla) => {
        this.error.set(e.mensaje);
        this.cargando.set(false);
      },
    });
  }
}
