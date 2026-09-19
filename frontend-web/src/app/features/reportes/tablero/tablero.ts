import { CurrencyPipe, DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';
import type { ChartConfiguration } from 'chart.js';
import { BaseChartDirective, provideCharts, withDefaultRegisterables } from 'ng2-charts';

import { OrganizacionService } from '../../../core/services/organizacion.service';
import { TableroService, type ErrorTablero } from '../../../core/services/tablero.service';
import type { SucursalBreve } from '../../../core/models/organizacion.models';
import type { Tablero as DatosTablero } from '../../../core/models/tablero.models';

/** Cuántos días atrás mira cada atajo del selector de período. */
const ATAJOS = [
  { etiqueta: 'Últimos 7 días', dias: 7 },
  { etiqueta: 'Últimos 30 días', dias: 30 },
  { etiqueta: 'Últimos 90 días', dias: 90 },
] as const;

/**
 * La paleta de los gráficos, tomada de las variables de marca de `styles.scss`.
 *
 * Se escriben los valores y no `var(--vb-malva)`: Chart.js pinta sobre un
 * `<canvas>` y no resuelve variables CSS —recibiría la cadena literal y
 * dibujaría en negro—. Quedan acá, juntos y rotulados, para que se vea que son
 * los mismos colores de la hoja de estilos y no una segunda paleta inventada.
 */
const COLORES = {
  malva: '#8e4a67',
  malvaClaro: '#b57f9a',
  rosaPalido: '#e7bfa8',
  oro: '#c9a227',
  humo: '#cbbcc4',
} as const;

/**
 * CU-36 · Consultar tablero de indicadores — «boundary» PantallaTablero.
 *
 * Los KPIs del negocio en tiempo real (RF24), para el Administrador.
 *
 * **Los siete indicadores del enunciado están completos.** Cuatro —ventas del
 * día y del mes, ticket promedio y prendas más vendidas— estuvieron apagados
 * hasta el 19/09 porque `venta` y `detalle_venta` no existían; el contrato los
 * declaraba igual y esta pantalla dibujaba un aviso en su lugar.
 *
 * Cuando las tablas llegaron, **acá no hubo nada que cambiar**: la rama de
 * `disponible: true` ya estaba escrita desde el primer día. Es la razón por la
 * que valió la pena declarar el contrato entero antes de tener los datos.
 *
 * **Por qué el inventario se rotula «ahora» y no con el período.** Un saldo es
 * una foto del instante: `existencia` guarda cuánto hay, no cuánto hubo, y no
 * tiene fecha contra la que filtrar. Es contraintuitivo leerlo en una pantalla
 * que arriba tiene dos fechas, así que se dice en la tarjeta en vez de esperar
 * que se deduzca.
 */
@Component({
  selector: 'app-tablero',
  imports: [
    CurrencyPipe,
    DatePipe,
    ReactiveFormsModule,
    BaseChartDirective,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatSelectModule,
    MatTooltipModule,
  ],
  // Chart.js se registra ACÁ, en el componente, y no en `app.config.ts` ni en
  // la ruta. Los dos viajan en el bundle inicial, así que importar `ng2-charts`
  // desde cualquiera de los dos mete la librería en el arranque de TODAS las
  // pantallas: medido, 678 kB a 890 kB: la vitrina pública descargaría el
  // motor de gráficos en un teléfono para no dibujar ninguno. Desde acá viaja
  // en el trozo diferido del tablero, que es el único que lo usa.
  //
  // `withDefaultRegisterables` registra todos los tipos de gráfico de una vez.
  // La alternativa —enumerar solo los que se usan— ahorra unos kilobytes y hace
  // que agregar un gráfico en CU-37 falle en tiempo de ejecución, sin error de
  // compilación, con el lienzo en blanco y nada en la consola.
  providers: [provideCharts(withDefaultRegisterables())],
  templateUrl: './tablero.html',
  styleUrl: './tablero.scss',
})
export class Tablero implements OnInit {
  private readonly api = inject(TableroService);
  private readonly organizacion = inject(OrganizacionService);

  protected readonly atajos = ATAJOS;

  protected readonly cargando = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly datos = signal<DatosTablero | null>(null);
  protected readonly sucursales = signal<SucursalBreve[]>([]);

  /**
   * Las dos fechas, como `YYYY-MM-DD` y no como `Date`.
   *
   * Se usa `<input type="date">` nativo en vez de `<mat-datepicker>`, y hay dos
   * razones. La primera es que el valor nativo YA ES la cadena que el contrato
   * espera: con `Date` habría que convertirla, y `toISOString()` —que es lo que
   * uno escribe sin pensar— pasa por UTC, así que en Bolivia (−4) devuelve el
   * día anterior para cualquier hora antes de las 20:00. Elegir «hoy» en el
   * calendario y recibir el tablero de ayer es un error que acá no puede pasar.
   *
   * La segunda es que `MatDatepicker` exige un `DateAdapter` provisto en la
   * configuración de la aplicación —`provideNativeDateAdapter` o similar— y
   * este proyecto no provee ninguno. Ver la nota al pie de este archivo.
   */
  protected readonly desde = new FormControl<string>('', { nonNullable: true });
  protected readonly hasta = new FormControl<string>('', { nonNullable: true });
  protected readonly filtroSucursal = new FormControl<number | ''>('', {
    nonNullable: true,
  });

  ngOnInit(): void {
    this.organizacion.sucursales().subscribe({
      next: (filas) => this.sucursales.set(filas),
      // Que falle el selector de sucursales no puede dejar sin tablero: el
      // filtro es opcional y sin él se ve la red entera, que es lo que el
      // Administrador quiere ver la mayoría de las veces.
      error: () => this.sucursales.set([]),
    });
    this.consultar();
  }

  protected consultar(): void {
    this.cargando.set(true);
    this.error.set(null);

    const sucursal = this.filtroSucursal.value;
    this.hayFiltros.set(
      this.desde.value !== '' || this.hasta.value !== '' || sucursal !== '',
    );
    this.api
      .consultar({
        desde: this.desde.value || undefined,
        hasta: this.hasta.value || undefined,
        sucursal_id: sucursal === '' ? undefined : sucursal,
      })
      .subscribe({
        next: (cuerpo) => {
          this.datos.set(cuerpo);
          this.cargando.set(false);
        },
        error: (e: ErrorTablero) => {
          this.error.set(e.mensaje);
          this.cargando.set(false);
        },
      });
  }

  /** Un atajo fija las dos fechas y consulta de una vez. */
  protected aplicarAtajo(dias: number): void {
    const hasta = new Date();
    const desde = new Date();
    desde.setDate(desde.getDate() - (dias - 1));
    this.desde.setValue(this.comoFecha(desde));
    this.hasta.setValue(this.comoFecha(hasta));
    this.consultar();
  }

  protected limpiar(): void {
    this.desde.setValue('');
    this.hasta.setValue('');
    this.filtroSucursal.setValue('');
    this.consultar();
  }

  /**
   * Si el usuario acotó algo, para decidir si se ofrece «Limpiar».
   *
   * Es una señal que se fija en `consultar()` y **no** un `computed` sobre los
   * `FormControl`: el valor de un control no es una señal, así que un
   * `computed` que lo leyera no se recalcularía al cambiarlo —quedaría
   * congelado hasta que otra señal lo despertara, que es la clase de error que
   * se ve como «el botón a veces aparece»—.
   */
  protected readonly hayFiltros = signal(false);

  /**
   * Una fecha en `YYYY-MM-DD` **local**, que es lo que el input nativo espera.
   *
   * Se arma componente por componente y no con `toISOString()`, que convierte a
   * UTC y en Bolivia adelanta el día. Ver la nota de `desde`.
   */
  private comoFecha(valor: Date): string {
    const mes = `${valor.getMonth() + 1}`.padStart(2, '0');
    const dia = `${valor.getDate()}`.padStart(2, '0');
    return `${valor.getFullYear()}-${mes}-${dia}`;
  }

  /** Una tasa para mostrar, o una raya cuando no hay denominador. */
  protected tasa(valor: number | null): string {
    return valor === null ? '—' : `${valor} %`;
  }

  /**
   * Si hay un importe que mostrar.
   *
   * El ticket promedio es nulo cuando no hubo ninguna venta ---no cero: son
   * cosas distintas---. El pipe de moneda sobre un nulo no dibuja nada, y una
   * tarjeta vacia se lee como un error de la pantalla; la raya dice «no hay
   * dato», que es lo que pasa.
   */
  protected hayImporte(valor: string | null): boolean {
    return valor !== null && valor !== undefined;
  }

  // --- Gráficos ----------------------------------------------------------

  /**
   * Las reservas del período, por estado.
   *
   * Es una dona y no un gráfico de barras porque lo que se lee acá es un
   * **reparto de un total**: qué proporción de las reservas terminó bien. Las
   * barras invitan a comparar magnitudes entre categorías, que no es la
   * pregunta.
   */
  protected readonly datosReservas = computed<ChartConfiguration<'doughnut'>['data']>(() => {
    const r = this.datos()?.reservas;
    return {
      labels: ['Pendientes', 'Preparadas', 'Atendidas', 'Canceladas', 'Expiradas'],
      datasets: [
        {
          data: r
            ? [r.pendientes, r.preparadas, r.atendidas, r.canceladas, r.expiradas]
            : [],
          backgroundColor: [
            COLORES.malvaClaro,
            COLORES.rosaPalido,
            COLORES.malva,
            COLORES.humo,
            COLORES.oro,
          ],
          borderWidth: 0,
        },
      ],
    };
  });

  protected readonly opcionesReservas: ChartConfiguration<'doughnut'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '62%',
    plugins: {
      legend: { position: 'right', labels: { boxWidth: 12, padding: 14 } },
    },
  };

  /**
   * Las prendas más reservadas, en barras horizontales.
   *
   * Horizontales y no verticales porque las etiquetas son nombres largos
   * —«Blusa de seda · M · Marfil»—: en vertical se giran y dejan de leerse.
   */
  protected readonly datosRanking = computed<ChartConfiguration<'bar'>['data']>(() => {
    const filas = this.datos()?.mas_reservadas ?? [];
    return {
      labels: filas.map((f) => `${f.producto} · ${f.talla} · ${f.color}`),
      datasets: [
        {
          label: 'Unidades reservadas',
          data: filas.map((f) => f.unidades),
          backgroundColor: COLORES.malva,
          borderRadius: 6,
        },
      ],
    };
  });

  /**
   * Las prendas más vendidas del período.
   *
   * Mismo tipo de gráfico que el de reservadas —barras horizontales, por las
   * etiquetas largas— y **las mismas opciones**, a propósito: las dos responden
   * la misma forma de pregunta y ponerlas lado a lado con escalas distintas
   * invitaría a compararlas como si fueran lo mismo.
   */
  protected readonly datosVendidas = computed<ChartConfiguration<'bar'>['data']>(() => {
    const filas = this.datos()?.ventas.mas_vendidas ?? [];
    return {
      labels: filas.map((f) => `${f.producto} · ${f.talla} · ${f.color}`),
      datasets: [
        {
          label: 'Unidades vendidas',
          data: filas.map((f) => f.unidades),
          backgroundColor: COLORES.oro,
          borderRadius: 6,
        },
      ],
    };
  });

  protected readonly opcionesRanking: ChartConfiguration<'bar'>['options'] = {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      // Sin esto, un ranking de 3 unidades dibuja medias unidades en el eje.
      x: { beginAtZero: true, ticks: { precision: 0 } },
    },
  };
}

// ---------------------------------------------------------------------------
// NOTA AL PIE — el `DateAdapter` que no está provisto, y a quién le importa
// ---------------------------------------------------------------------------
//
// `MatDatepickerModule` NO trae su propio `DateAdapter`: hay que proveer uno en
// la configuración de la aplicación (`provideNativeDateAdapter()` es el que
// corresponde acá). Sin él, `MatDatepicker` lanza en tiempo de ejecución al
// abrirse — no falla la compilación, así que no se nota construyendo.
//
// En todo `frontend-web/src` no hay ni un `provideNativeDateAdapter` ni un
// `DateAdapter`, y `features/cliente/reservas/reserva-formulario.html` sí
// declara un `<mat-datepicker>` (CU-22). **Conviene abrir esa pantalla antes de
// la defensa**: si lanza, es una línea en `app.config.ts`. No se toca desde
// acá porque es de otro caso de uso y `app.config.ts` es archivo compartido.
//
// Esta pantalla no lo necesita: usa el input de fecha nativo, por las dos
// razones que están arriba en `desde`.
