import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';

/** Aporte propio · un pedido de «avísenme cuando llegue esta talla». */
export interface AvisoTalla {
  id: number;
  variante_id: number;
  producto_id: number | null;
  producto: string;
  talla: string;
  color: string;
  sku: string;
  imagen_url: string | null;
  ofrecible: boolean;
  estado: 'ESPERANDO' | 'AVISADO';
  creado_en: string;
  notificado_en: string | null;
}

/** Una talla agotada con los clientes que la esperan (para el personal). */
export interface DemandaTalla {
  variante_id: number;
  producto_id: number;
  producto: string;
  talla: string;
  color: string;
  sku: string;
  clientes: number;
  esperando_desde: string;
}

export interface ErrorAvisoTalla {
  estado: number;
  mensaje: string;
}

/**
 * Aporte propio · «Avísame cuando llegue mi talla».
 *
 * El cliente lo pide desde la ficha cuando la talla y el color elegidos no
 * tienen unidades en ninguna sucursal; el aviso le llega por la campanita, el
 * correo y el push cuando el inventario la repone. El personal ve cuántos
 * clientes esperan cada talla.
 */
@Injectable({ providedIn: 'root' })
export class AvisosTallaService {
  private readonly http = inject(HttpClient);
  private readonly cliente = `${environment.apiUrl}/tienda/avisos-talla`;
  private readonly personal = `${environment.apiUrl}/inventario/avisos-talla`;

  misAvisos(): Observable<AvisoTalla[]> {
    return this.http.get<AvisoTalla[]>(this.cliente).pipe(catchError((e) => this.fallo(e)));
  }

  variantesEsperadas(): Observable<number[]> {
    return this.http
      .get<number[]>(`${this.cliente}/variantes`)
      .pipe(catchError((e) => this.fallo(e)));
  }

  pedir(varianteId: number): Observable<AvisoTalla> {
    return this.http
      .post<AvisoTalla>(this.cliente, { variante_id: varianteId })
      .pipe(catchError((e) => this.fallo(e)));
  }

  cancelar(avisoId: number): Observable<void> {
    return this.http
      .delete<void>(`${this.cliente}/${avisoId}`)
      .pipe(catchError((e) => this.fallo(e)));
  }

  demanda(): Observable<DemandaTalla[]> {
    return this.http.get<DemandaTalla[]>(this.personal).pipe(catchError((e) => this.fallo(e)));
  }

  urlDeImagen(url: string | null): string | null {
    if (!url) return null;
    return `${new URL(environment.apiUrl).origin}${url}`;
  }

  private fallo(error: HttpErrorResponse): Observable<never> {
    const detalle = typeof error.error?.detail === 'string' ? error.error.detail : '';
    const mensaje =
      error.status === 0
        ? 'No se pudo contactar al servidor. Verifique su conexión.'
        : detalle || 'No se pudo completar la operación.';
    return throwError(() => ({ estado: error.status, mensaje }) as ErrorAvisoTalla);
  }
}
