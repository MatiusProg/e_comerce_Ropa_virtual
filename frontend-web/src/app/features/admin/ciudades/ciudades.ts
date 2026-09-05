import { Component, OnInit, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';

import {
  OrganizacionService,
  type ErrorOrganizacion,
} from '../../../core/services/organizacion.service';
import type { Ciudad } from '../../../core/models/organizacion.models';
import { Confirmacion, type DatosConfirmacion } from '../../../shared/confirmacion/confirmacion';
import { CiudadFormulario } from './ciudad-formulario';

/**
 * CU-05 · flujo alternativo 3a — «boundary» PantallaCiudades.
 *
 * Pantalla propia y no un diálogo dentro de sucursales: las ciudades son la
 * precondición de una sucursal —sin ciudad no hay dónde ponerla— y tenerlas
 * a un clic hace evidente ese orden.
 *
 * Sin paginación, por el mismo motivo que en sucursales: la cadena opera en un
 * puñado de ciudades.
 */
@Component({
  selector: 'app-ciudades',
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatMenuModule,
    MatProgressBarModule,
    MatTableModule,
    MatTooltipModule,
  ],
  templateUrl: './ciudades.html',
  styleUrl: './ciudades.scss',
})
export class Ciudades implements OnInit {
  private readonly api = inject(OrganizacionService);
  private readonly dialogo = inject(MatDialog);
  private readonly aviso = inject(MatSnackBar);

  protected readonly columnas = ['ciudad', 'departamento', 'sucursales', 'acciones'];

  protected readonly cargando = signal(false);
  /** Mensaje del ultimo fallo al listar, o null. Distingue «no se pudo
   *  consultar» de «no hay nada», que en pantalla se confundian. */
  protected readonly error = signal<string | null>(null);
  protected readonly ciudades = signal<Ciudad[]>([]);

  protected readonly busqueda = new FormControl('', { nonNullable: true });

  ngOnInit(): void {
    this.busqueda.valueChanges
      .pipe(debounceTime(350), distinctUntilChanged())
      .subscribe(() => this.cargar());
    this.cargar();
  }

  protected cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.api.listarCiudades(this.busqueda.value || undefined).subscribe({
      next: (c) => {
        this.ciudades.set(c);
        this.cargando.set(false);
      },
      error: (e: ErrorOrganizacion) => {
        this.cargando.set(false);
        this.error.set(e.mensaje);
        this.mostrar(e.mensaje);
      },
    });
  }

  protected limpiarBusqueda(): void {
    this.busqueda.setValue('', { emitEvent: false });
    this.cargar();
  }

  // --- Acciones ----------------------------------------------------------

  protected nueva(): void {
    this.abrirFormulario(null);
  }

  protected editar(ciudad: Ciudad): void {
    this.abrirFormulario(ciudad);
  }

  private abrirFormulario(ciudad: Ciudad | null): void {
    this.dialogo
      .open(CiudadFormulario, { data: ciudad, width: '480px', maxWidth: '95vw' })
      .afterClosed()
      .subscribe((guardado) => {
        if (guardado) {
          this.mostrar(ciudad ? 'Ciudad actualizada.' : 'Ciudad registrada correctamente.');
          this.cargar();
        }
      });
  }

  /**
   * Baja de una ciudad.
   *
   * `ciudad` no tiene indicador de estado: darla de baja es eliminarla. Con
   * sucursales encima no se puede, y el motivo es distinto según en qué estado
   * estén, así que se dice antes de intentarlo (excepción E2).
   */
  protected eliminar(ciudad: Ciudad): void {
    if (ciudad.sucursales_activas > 0) {
      this.mostrar(
        `${ciudad.nombre} tiene ${ciudad.sucursales_activas} sucursal(es) activa(s). Dé de baja sus sucursales antes de eliminarla.`,
      );
      return;
    }
    if (ciudad.sucursales > 0) {
      this.mostrar(
        `${ciudad.nombre} conserva sucursales dadas de baja por trazabilidad y no puede eliminarse.`,
      );
      return;
    }

    const datos: DatosConfirmacion = {
      titulo: 'Eliminar ciudad',
      mensaje: `Se eliminará ${ciudad.nombre}. Esta acción no se puede deshacer.`,
      confirmar: 'Eliminar',
      peligrosa: true,
    };

    this.dialogo
      .open(Confirmacion, { data: datos, width: '460px', maxWidth: '95vw' })
      .afterClosed()
      .subscribe((si) => {
        if (!si) return;
        this.api.eliminarCiudad(ciudad.id).subscribe({
          next: () => {
            this.mostrar('Ciudad eliminada.');
            this.cargar();
          },
          // El servidor vuelve a comprobarlo: entre que se pintó la fila y
          // este clic pudo crearse una sucursal.
          error: (e: ErrorOrganizacion) => this.mostrar(e.mensaje),
        });
      });
  }

  private mostrar(mensaje: string): void {
    this.aviso.open(mensaje, 'Cerrar', { duration: 6000 });
  }
}
