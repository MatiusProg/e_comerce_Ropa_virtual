import { DatePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';

import { OfflineService } from '../../../core/services/offline.service';
import type { EstadoLocal } from '../../../core/models/offline.models';
import { BsPipe } from '../../../shared/bs.pipe';
import { sinRespuesta } from '../../../core/sin-respuesta';

/**
 * CU-13 Preparar el dispositivo · CU-18 Consultar operaciones pendientes.
 * «boundary» PantallaPendientes.
 *
 * La cola que se muestra es la del NAVEGADOR, no la del servidor: lo que el
 * cajero necesita saber es qué cobró que todavía no llegó. Lo que el servidor
 * ya decidió se ve acá también, con su motivo, hasta que el cajero lo limpia.
 */
@Component({
  selector: 'app-pendientes',
  imports: [BsPipe, DatePipe, MatButtonModule, MatCardModule, MatIconModule, MatProgressBarModule],
  templateUrl: './pendientes.html',
  styleUrl: './pendientes.scss',
})
export class Pendientes {
  protected readonly offline = inject(OfflineService);
  private readonly aviso = inject(MatSnackBar);

  protected readonly preparando = signal(false);
  protected readonly operaciones = this.offline.operaciones;
  protected readonly hayConfirmadas = computed(() =>
    this.operaciones().some((o) => o.estado === 'confirmada'),
  );

  protected async preparar(): Promise<void> {
    this.preparando.set(true);
    try {
      const p = await this.offline.preparar();
      this.aviso.open(
        `Listo: ${p.prendas.length} prendas y ${p.clientes.length} clientes guardados en este dispositivo.`,
        'Entendido',
        { duration: 6000 },
      );
    } catch (e) {
      const error = e as HttpErrorResponse;
      const texto =
        sinRespuesta(error)
          ? 'Sin conexión: el dispositivo se prepara con red, antes de quedarse sin ella.'
          : typeof error.error?.detail === 'string'
            ? error.error.detail
            : 'No se pudo preparar el dispositivo.';
      this.aviso.open(texto, 'Entendido', { duration: 8000 });
    } finally {
      this.preparando.set(false);
    }
  }

  protected async sincronizar(): Promise<void> {
    const r = await this.offline.sincronizar();
    if (!r) return;
    if (!this.offline.enLinea()) {
      this.aviso.open('Sigue sin conexión. Las operaciones quedan guardadas.', 'Entendido', {
        duration: 5000,
      });
      return;
    }
    this.aviso.open(
      `${r.confirmadas} confirmada(s) y ${r.rechazadas} rechazada(s).`,
      'Entendido',
      { duration: 5000 },
    );
  }

  protected limpiar(): void {
    void this.offline.limpiarConfirmadas();
  }

  protected etiqueta(estado: EstadoLocal): string {
    return {
      local: 'Guardada',
      enviada: 'Enviada',
      confirmada: 'Confirmada',
      rechazada: 'Rechazada',
      en_conflicto: 'En conflicto',
    }[estado];
  }

  protected icono(estado: EstadoLocal): string {
    return {
      local: 'save',
      enviada: 'cloud_upload',
      confirmada: 'check_circle',
      rechazada: 'block',
      en_conflicto: 'warning',
    }[estado];
  }
}
