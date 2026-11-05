import { DatePipe, DecimalPipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';

import {
  DatosService,
  type Copia,
  type Descarga,
  type HistorialDeCopias,
} from '../../../core/services/datos.service';

/**
 * 3ra presentación · CU-39 Exportar los datos de la empresa y CU-40 Gestionar
 * copias de seguridad. «boundary» PantallaDatosDeLaEmpresa.
 *
 * Dos cosas distintas en la misma pantalla, y se dice cuál es cuál:
 * - **Exportar** (RF-48) es para LEER los datos: Excel o CSV.
 * - **La copia** (RF-60 a RF-63) es para RESTAURARLOS: JSON firmado.
 *
 * Restaurar reemplaza todo lo de la empresa (RN-19), así que se pide escribir
 * RESTAURAR antes de hacerlo.
 */
@Component({
  selector: 'app-datos',
  imports: [
    DatePipe,
    DecimalPipe,
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatTooltipModule,
  ],
  templateUrl: './datos.html',
  styleUrl: './datos.scss',
})
export class Datos implements OnInit {
  private readonly api = inject(DatosService);
  private readonly aviso = inject(MatSnackBar);

  protected readonly cargando = signal(true);
  protected readonly historial = signal<HistorialDeCopias | null>(null);
  protected readonly trabajando = signal<string | null>(null);
  /** El mensaje del CU-05 si el plan no incluye la exportación. */
  protected readonly exportarBloqueado = signal<string | null>(null);

  // --- Restaurar --------------------------------------------------------
  protected readonly archivo = signal<File | null>(null);
  /** La copia guardada que se va a restaurar, o nulo si es un archivo. */
  protected readonly desdeCopia = signal<Copia | null>(null);
  protected readonly confirmacion = new FormControl('', { nonNullable: true });

  ngOnInit(): void {
    this.cargar();
  }

  protected cargar(): void {
    this.cargando.set(true);
    this.api.historial().subscribe({
      next: (h) => {
        this.historial.set(h);
        this.cargando.set(false);
      },
      error: (e: HttpErrorResponse) => {
        this.cargando.set(false);
        this.mostrar(e, 'No se pudo leer el historial de copias.');
      },
    });
  }

  protected textoIntervalo(horas: number | null): string {
    if (horas === null) return 'a voluntad';
    if (horas % 168 === 0) return horas === 168 ? 'una por semana' : `una cada ${horas / 168} semanas`;
    if (horas % 24 === 0) return horas === 24 ? 'una por día' : `una cada ${horas / 24} días`;
    return `una cada ${horas} horas`;
  }

  protected totalFilas(filas: Record<string, number>): number {
    return Object.values(filas).reduce((a, b) => a + b, 0);
  }

  // --- CU-39 --------------------------------------------------------------
  protected exportar(formato: 'xlsx' | 'zip'): void {
    this.trabajando.set(`exportar-${formato}`);
    this.api.exportar(formato).subscribe({
      next: (d) => {
        this.trabajando.set(null);
        this.guardar(d);
      },
      error: (e: HttpErrorResponse) => {
        this.trabajando.set(null);
        void this.mensajeDeBlob(e).then((texto) => {
          if (e.status === 403) this.exportarBloqueado.set(texto);
          this.aviso.open(texto ?? 'No se pudo exportar.', 'Entendido', { duration: 7000 });
        });
      },
    });
  }

  // --- CU-40 --------------------------------------------------------------
  protected copiaManual(): void {
    this.trabajando.set('manual');
    this.api.copiaManual().subscribe({
      next: (d) => {
        this.trabajando.set(null);
        this.guardar(d);
        this.aviso.open('Copia generada. Guárdela en un lugar seguro: no queda en el servidor.',
          'Entendido', { duration: 7000 });
        this.cargar();
      },
      error: (e: HttpErrorResponse) => {
        this.trabajando.set(null);
        void this.mensajeDeBlob(e).then((texto) =>
          this.aviso.open(texto ?? 'No se pudo generar la copia.', 'Entendido', { duration: 8000 }),
        );
      },
    });
  }

  protected copiaAutomatica(): void {
    this.trabajando.set('automatica');
    this.api.copiaAutomatica().subscribe({
      next: (r) => {
        this.trabajando.set(null);
        this.aviso.open(
          r.creada ? 'Copia automática creada y guardada cifrada.' : (r.motivo ?? 'No tocaba.'),
          'Entendido',
          { duration: 6000 },
        );
        this.cargar();
      },
      error: (e: HttpErrorResponse) => {
        this.trabajando.set(null);
        this.mostrar(e, 'No se pudo generar la copia automática.');
      },
    });
  }

  protected descargar(copia: Copia): void {
    this.trabajando.set(`bajar-${copia.id}`);
    this.api.descargarCopia(copia.id).subscribe({
      next: (d) => {
        this.trabajando.set(null);
        this.guardar(d);
      },
      error: (e: HttpErrorResponse) => {
        this.trabajando.set(null);
        void this.mensajeDeBlob(e).then((t) =>
          this.aviso.open(t ?? 'No se pudo descargar.', 'Entendido', { duration: 6000 }),
        );
      },
    });
  }

  protected elegirArchivo(evento: Event): void {
    const entrada = evento.target as HTMLInputElement;
    this.archivo.set(entrada.files?.[0] ?? null);
    this.desdeCopia.set(null);
    this.confirmacion.setValue('');
  }

  protected prepararRestauracion(copia: Copia): void {
    this.desdeCopia.set(copia);
    this.archivo.set(null);
    this.confirmacion.setValue('');
  }

  protected cancelarRestauracion(): void {
    this.desdeCopia.set(null);
    this.archivo.set(null);
    this.confirmacion.setValue('');
  }

  protected restaurar(): void {
    if (this.confirmacion.value.trim().toUpperCase() !== 'RESTAURAR') {
      this.aviso.open('Escriba RESTAURAR para confirmar.', 'Entendido', { duration: 4000 });
      return;
    }
    const copia = this.desdeCopia();
    const archivo = this.archivo();
    if (!copia && !archivo) return;
    this.trabajando.set('restaurar');
    const peticion = copia ? this.api.restaurarCopia(copia.id) : this.api.restaurarArchivo(archivo!);
    peticion.subscribe({
      next: (r) => {
        this.trabajando.set(null);
        this.cancelarRestauracion();
        this.aviso.open(
          `Datos restaurados: ${this.totalFilas(r.filas)} filas de ${r.archivo}.`,
          'Entendido',
          { duration: 8000 },
        );
        this.cargar();
      },
      error: (e: HttpErrorResponse) => {
        this.trabajando.set(null);
        this.mostrar(e, 'No se pudo restaurar. Los datos no cambiaron.');
      },
    });
  }

  // --- Ayudantes ----------------------------------------------------------
  private guardar(d: Descarga): void {
    const url = URL.createObjectURL(d.archivo);
    const enlace = document.createElement('a');
    enlace.href = url;
    enlace.download = d.nombre;
    enlace.click();
    URL.revokeObjectURL(url);
  }

  /** Con `responseType: 'blob'` el error también llega como blob. */
  private async mensajeDeBlob(e: HttpErrorResponse): Promise<string | null> {
    try {
      const texto = e.error instanceof Blob ? await e.error.text() : null;
      const cuerpo = texto ? JSON.parse(texto) : e.error;
      return typeof cuerpo?.detail === 'string' ? cuerpo.detail : null;
    } catch {
      return null;
    }
  }

  private mostrar(e: HttpErrorResponse, porOmision: string): void {
    const texto = typeof e.error?.detail === 'string' ? e.error.detail : porOmision;
    this.aviso.open(texto, 'Entendido', { duration: 8000 });
  }
}
