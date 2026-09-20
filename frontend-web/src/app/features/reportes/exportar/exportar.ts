import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';

import { DictadoService } from '../../../core/services/dictado.service';
import {
  ReportesService,
  type ErrorReportes,
  type PedidoEntendido,
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
    MatSelectModule,
    MatTooltipModule,
  ],
  templateUrl: './exportar.html',
  styleUrl: './exportar.scss',
})
export class Exportar implements OnInit {
  private readonly api = inject(ReportesService);
  private readonly aviso = inject(MatSnackBar);
  protected readonly dictado = inject(DictadoService);

  // --- CU-35 · pedir hablando ----------------------------------------------

  /** Si el servidor puede interpretar. El navegador es lo otro que hace falta. */
  protected readonly hayVoz = signal(false);

  /** Lo que el servidor entendió, para mostrarlo ANTES de descargar. */
  protected readonly entendido = signal<PedidoEntendido | null>(null);
  protected readonly interpretando = signal(false);

  /** El micrófono se ofrece solo si el navegador Y el servidor pueden. */
  protected readonly sePuedeHablar = computed(
    () => this.hayVoz() && this.dictado.soportado(),
  );

  protected readonly cargando = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly reportes = signal<ReporteDisponible[]>([]);

  /**
   * Lo elegido en cada filtro, por reporte: `{ventas: {canal: 'DIGITAL'}}`.
   *
   * POR QUE POR REPORTE Y NO UNO SOLO COMPARTIDO
   * ---------------------------------------------
   * Los filtros no significan lo mismo en cada uno: `estado` en ventas es
   * PAGADA y en reservas es ATENDIDA. Con un diccionario compartido, elegir
   * un estado en ventas dejaría el de reservas en un valor que no existe, y
   * el reporte saldría vacío sin que nada lo explique.
   */
  protected readonly elegido = signal<Record<string, Record<string, string>>>({});

  /** Cuál se está bajando, y en qué formato. `null` si ninguno. */
  protected readonly bajando = signal<string | null>(null);

  protected readonly rango = new FormGroup({
    desde: new FormControl<Date | null>(this.haceUnMes()),
    hasta: new FormControl<Date | null>(new Date()),
  });

  /** Hasta hoy: un reporte del futuro no tiene datos y confunde. */
  protected readonly maximo = new Date();

  ngOnInit(): void {
    this.api.hayVoz().subscribe((hay) => this.hayVoz.set(hay));
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

  protected hablar(): void {
    if (this.dictado.escuchando()) {
      this.dictado.detener();
      return;
    }
    this.entendido.set(null);
    this.dictado.escuchar((frase) => this.interpretar(frase));
  }

  private interpretar(frase: string): void {
    this.interpretando.set(true);
    this.api.interpretarVoz(frase).subscribe({
      next: (pedido) => {
        this.interpretando.set(false);
        this.entendido.set(pedido);
      },
      error: (e: ErrorReportes) => {
        this.interpretando.set(false);
        this.aviso.open(e.mensaje, 'Cerrar', { duration: 7000 });
      },
    });
  }

  /**
   * Descarga lo que el servidor entendió.
   *
   * La URL la armó el servidor con todos los parámetros; acá no se rearma
   * nada, para no arriesgarse a perder un filtro por el camino.
   */
  protected descargarLoEntendido(): void {
    const pedido = this.entendido();
    if (!pedido?.tipo || !pedido.formato) return;

    const url = new URL(pedido.url ?? '', 'http://x');
    const filtros: Record<string, string> = {};
    url.searchParams.forEach((valor, clave) => (filtros[clave] = valor));

    this.bajando.set(`${pedido.tipo}:${pedido.formato}`);
    this.api
      .descargar(pedido.tipo, pedido.formato as 'pdf' | 'xlsx', filtros)
      .subscribe({
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

  protected valorDe(tipo: string, campo: string): string {
    return this.elegido()[tipo]?.[campo] ?? '';
  }

  protected elegir(tipo: string, campo: string, valor: string): void {
    this.elegido.update((todo) => ({
      ...todo,
      [tipo]: { ...(todo[tipo] ?? {}), [campo]: valor },
    }));
  }

  protected limpiar(tipo: string): void {
    this.elegido.update((todo) => ({ ...todo, [tipo]: {} }));
  }

  /** Cuántos filtros tiene puestos, para avisarlo sin abrir el panel. */
  protected cuantosFiltros(tipo: string): number {
    return Object.values(this.elegido()[tipo] ?? {}).filter((v) => v !== '')
      .length;
  }

  protected descargar(reporte: ReporteDisponible, formato: 'pdf' | 'xlsx'): void {
    const clave = `${reporte.tipo}:${formato}`;
    if (this.bajando()) return;
    this.bajando.set(clave);

    const filtros: Record<string, string | null> = {
      ...(this.elegido()[reporte.tipo] ?? {}),
    };
    if (reporte.usa_periodo) {
      filtros['desde'] = this.aIso(this.rango.value.desde);
      filtros['hasta'] = this.aIso(this.rango.value.hasta);
    }

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
