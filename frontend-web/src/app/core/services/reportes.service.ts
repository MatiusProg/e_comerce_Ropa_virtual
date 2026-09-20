import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';

import { environment } from '../../../environments/environment';

export interface OpcionDeFiltro {
  valor: string;
  etiqueta: string;
}

/**
 * Un filtro que ESTE reporte admite, con sus opciones ya resueltas.
 *
 * Vienen del servidor y no están escritas acá: las sucursales, los
 * proveedores y las temporadas salen de la base, y si un reporte acepta un
 * filtro más aparece en la pantalla sin tocar el front.
 */
export interface FiltroDeReporte {
  campo: string;
  etiqueta: string;
  opciones: OpcionDeFiltro[];
}

/** Un reporte que el servidor sabe generar. Sale de `/reportes/catalogo`. */
export interface ReporteDisponible {
  tipo: string;
  titulo: string;
  columnas: string[];

  /** `false` para el inventario: es una foto de ahora, no un acumulado. */
  usa_periodo: boolean;

  filtros: FiltroDeReporte[];
}

/** Lo que viaja en la URL. Las claves extra son los filtros propios. */
export type FiltrosDeReporte = Record<string, string | number | null | undefined>;

export interface ErrorReportes {
  mensaje: string;
  codigo: number;
}

/**
 * CU-37 · Generar reportes de gestión (RF36).
 *
 * LA LISTA DE REPORTES NO ESTÁ ESCRITA ACÁ
 * -----------------------------------------
 * Viene de `/reportes/catalogo`. Si el backend agrega el séptimo, aparece
 * solo en la pantalla. Escrita a mano, agregar un reporte obligaría a tocar
 * los dos lados y alguien se olvidaría de la segunda mitad.
 */
@Injectable({ providedIn: 'root' })
export class ReportesService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/reportes`;

  catalogo(): Observable<ReporteDisponible[]> {
    return this.http
      .get<ReporteDisponible[]>(`${this.base}/catalogo`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /**
   * Descarga el archivo.
   *
   * POR QUÉ `responseType: 'blob'` Y NO EL JSON DE SIEMPRE
   * -------------------------------------------------------
   * Un PDF y un XLSX son binarios. Con el tipo por omisión, Angular intenta
   * interpretarlos como JSON, falla al analizarlos y el error que llega no
   * dice nada sobre lo que pasó: el archivo estaba bien, lo que estaba mal
   * era cómo se lo pidió.
   *
   * **No se usa un `<a href>` directo** aunque sería más corto: el endpoint
   * exige la cabecera `Authorization`, y un enlace del navegador no la manda.
   * Pasar el token por la URL lo dejaría en el historial y en los registros de
   * cualquier intermediario.
   */
  descargar(
    tipo: string,
    formato: 'pdf' | 'xlsx',
    filtros: FiltrosDeReporte = {},
  ): Observable<{ archivo: Blob; nombre: string }> {
    let params = new HttpParams();
    for (const [clave, valor] of Object.entries(filtros)) {
      // Se omiten los vacíos: un parámetro sin valor significaría «filtrar
      // por nada» y el servidor lo descartaría igual, pero deja la URL sucia
      // y difícil de leer cuando hay que depurar una descarga.
      if (valor !== null && valor !== undefined && valor !== '') {
        params = params.set(clave, valor);
      }
    }

    return this.http
      .get(`${this.base}/${tipo}.${formato}`, {
        params,
        responseType: 'blob',
        observe: 'response',
      })
      .pipe(
        map((respuesta) => ({
          archivo: respuesta.body as Blob,
          // El servidor ya decidió cómo se llama el archivo; se respeta en vez
          // de rearmarlo acá, para que el nombre sea el mismo si alguien lo
          // baja por otro camino.
          nombre: this.nombreDe(respuesta.headers.get('content-disposition'), tipo, formato),
        })),
        catchError((e) => throwError(() => this.traducir(e))),
      );
  }

  private nombreDe(disposicion: string | null, tipo: string, formato: string): string {
    const coincidencia = disposicion?.match(/filename="([^"]+)"/);
    return coincidencia?.[1] ?? `${tipo}.${formato}`;
  }

  private traducir(error: HttpErrorResponse): ErrorReportes {
    if (error.status === 0) {
      return { mensaje: 'No se pudo conectar con el servidor.', codigo: 0 };
    }
    if (error.status === 403) {
      return { mensaje: 'No tiene permiso para descargar reportes.', codigo: 403 };
    }
    // El cuerpo de un error viene como Blob por el `responseType`, así que no
    // se puede leer el `detail` sin desenvolverlo. Para 4xx conocidos alcanza
    // con un mensaje propio; el resto cae en el genérico.
    if (error.status === 404) {
      return { mensaje: 'Ese reporte no existe.', codigo: 404 };
    }
    if (error.status === 422) {
      return {
        mensaje: 'Revise las fechas: la inicial no puede ser posterior a la final.',
        codigo: 422,
      };
    }
    return { mensaje: 'No se pudo generar el reporte.', codigo: error.status };
  }
}
