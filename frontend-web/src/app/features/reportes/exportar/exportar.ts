import { Component, OnInit, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';

import {
  ReportesService,
  type ErrorReportes,
  type ReporteDisponible,
} from '../../../core/services/reportes.service';

/**
 * CU-37 · Generar reportes de gestión — «boundary» PantallaExportarReportes.
 *
 * Realiza el **RF36**. Es la mitad visible de lo que ya existía por API: sin
 * esta pantalla, el caso de uso está construido y **no hay forma de llegar**
 * —que es exactamente lo que pasó con CU-33 hasta que se le hizo la suya—.
 *
 * LA LISTA DE REPORTES SE ARMA SOLA
 * ----------------------------------
 * Viene de `/reportes/catalogo`, con sus columnas y con `usa_periodo`. La
 * pantalla no conoce ninguno por nombre: si el backend agrega el séptimo,
 * aparece acá sin tocar este archivo.
 *
 * Ese `usa_periodo` es el que esconde el selector de fechas en el inventario:
 * es una **foto de ahora**, no un acumulado, y ofrecer un rango que se ignora
 * sería mentirle a quien lo elige.
 */
@Component({
  selector: 'app-exportar-reportes',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatDatepickerModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatTooltipModule,
  ],
  templateUrl: './exportar.html',
  styleUrl: './exportar.scss',
})
export class Exportar implements OnInit {
  private readonly api = inject(ReportesService);
  private readonly aviso = inject(MatSnackBar);

  protected readonly cargando = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly reportes = signal<ReporteDisponible[]>([]);

  /** Cuál se está bajando, y en qué formato. `null` si ninguno. */
  protected readonly bajando = signal<string | null>(null);

  protected readonly rango = new FormGroup({
    desde: new FormControl<Date | null>(this.haceUnMes()),
    hasta: new FormControl<Date | null>(new Date()),
  });

  /** Hasta hoy: un reporte del futuro no tiene datos y confunde. */
  protected readonly maximo = new Date();

  ngOnInit(): void {
    this.api.catalogo().subscribe({
      next: (lista) => {
        this.reportes.set(lista);
        this.cargando.set(false);
      },
      error: (e: ErrorReportes) => {
        this.error.set(e.mensaje);
        this.cargando.set(false);
      },
    });
  }

  private haceUnMes(): Date {
    const fecha = new Date();
    fecha.setMonth(fecha.getMonth() - 1);
    return fecha;
  }

  /** `YYYY-MM-DD` en hora LOCAL. */
  private aIso(fecha: Date | null | undefined): string | null {
    if (!fecha) return null;
    // `toISOString()` pasa a UTC y en Bolivia (UTC-4) eso **resta un día** a
    // toda fecha elegida antes de las 4 de la mañana. Se arma a mano con las
    // partes locales, que es lo que el usuario vio en el calendario.
    const mes = `${fecha.getMonth() + 1}`.padStart(2, '0');
    const dia = `${fecha.getDate()}`.padStart(2, '0');
    return `${fecha.getFullYear()}-${mes}-${dia}`;
  }

  protected descargar(reporte: ReporteDisponible, formato: 'pdf' | 'xlsx'): void {
    const clave = `${reporte.tipo}:${formato}`;
    if (this.bajando()) return;
    this.bajando.set(clave);

    const filtros = reporte.usa_periodo
      ? {
          desde: this.aIso(this.rango.value.desde),
          hasta: this.aIso(this.rango.value.hasta),
        }
      : {};

    this.api.descargar(reporte.tipo, formato, filtros).subscribe({
      next: ({ archivo, nombre }) => {
        this.bajando.set(null);
        this.guardar(archivo, nombre);
      },
      error: (e: ErrorReportes) => {
        this.bajando.set(null);
        this.aviso.open(e.mensaje, 'Cerrar', { duration: 7000 });
      },
    });
  }

  /**
   * Dispara la descarga en el navegador.
   *
   * Se crea un enlace temporal y se lo toca por código: es la única forma de
   * guardar un archivo que llegó por `HttpClient` —con su cabecera de
   * autorización— en vez de por una navegación directa.
   *
   * **`revokeObjectURL` no es opcional.** Sin él, cada descarga deja el
   * archivo entero retenido en memoria hasta recargar la página; bajando los
   * seis reportes de inventario eso son varios megabytes que no se sueltan.
   */
  private guardar(archivo: Blob, nombre: string): void {
    const url = URL.createObjectURL(archivo);
    const enlace = document.createElement('a');
    enlace.href = url;
    enlace.download = nombre;
    enlace.click();
    URL.revokeObjectURL(url);
  }

  protected estaBajando(tipo: string, formato: string): boolean {
    return this.bajando() === `${tipo}:${formato}`;
  }
}
