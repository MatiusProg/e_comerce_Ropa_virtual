import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import {
  ConsultaConsolidado,
  InventarioConsolidado,
} from '../models/consolidado.models';

export type ErrorConsolidado =
  | { tipo: 'sin-permiso'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

/**
 * CU-14 — el cliente HTTP del inventario consolidado.
 *
 * Servicio propio y no un método más en `InventarioService`, que es de CU-13 y
 * CU-15: son casos de uso de personas distintas y con contratos distintos, y
 * compartir el archivo significaría que las dos ramas tocan las mismas líneas.
 */
@Injectable({ providedIn: 'root' })
export class ConsolidadoService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/inventario`;

  consultar(consulta: ConsultaConsolidado = {}): Observable<InventarioConsolidado> {
    let params = new HttpParams();
    if (consulta.busqueda) params = params.set('busqueda', consulta.busqueda);
    if (consulta.sucursal_id) params = params.set('sucursal_id', consulta.sucursal_id);
    if (consulta.producto_id) params = params.set('producto_id', consulta.producto_id);
    if (consulta.estado) params = params.set('estado', consulta.estado);
    if (consulta.orden) params = params.set('orden', consulta.orden);
    if (consulta.pagina) params = params.set('pagina', consulta.pagina);
    if (consulta.tamano) params = params.set('tamano', consulta.tamano);
    return this.http
      .get<InventarioConsolidado>(`${this.base}/consolidado`, { params })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  private traducir(error: HttpErrorResponse): ErrorConsolidado {
    const detalle: string =
      typeof error.error?.detail === 'string' ? error.error.detail : '';

    if (error.status === 403) {
      return {
        tipo: 'sin-permiso',
        mensaje: 'El inventario consolidado es del Administrador.',
      };
    }
    if (error.status === 0) {
      return {
        tipo: 'sistema',
        mensaje: 'No se pudo contactar al servidor. Verifique su conexión.',
      };
    }
    return {
      tipo: 'sistema',
      mensaje: detalle || 'No se pudo consultar el inventario.',
    };
  }
}
