import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, throwError } from 'rxjs';

import { environment } from '../../../environments/environment';

/** Una combinación de las prendas del proveedor, para el formulario. */
export interface VarianteAnunciable {
  variante_id: number;
  sku: string;
  prenda: string;
  talla: string;
  color: string;
}

export interface Anuncio {
  id: number;
  variante_id: number;
  sku: string;
  prenda: string;
  talla: string;
  color: string;
  cantidad: number;
  dias_plazo: number;
  observacion: string | null;
  estado: string;
  creado_en: string;
}

export interface AnunciarIn {
  variante_id: number;
  cantidad: number;
  dias_plazo: number;
  observacion?: string | null;
}

export interface ErrorAbastecimiento {
  mensaje: string;
  codigo: number;
}

/**
 * CU-39 · Informar disponibilidad y plazo de abastecimiento (RF38).
 *
 * Es lo único que produce el estado «próxima a ingresar» del inventario
 * consolidado: hasta el 20/09/2026 ese estado estaba declarado y ninguna fila
 * lo devolvía.
 */
@Injectable({ providedIn: 'root' })
export class AbastecimientoService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/proveedor/abastecimiento`;

  /** Las combinaciones de MIS productos. El servidor ya filtra por dueño. */
  variantes(): Observable<VarianteAnunciable[]> {
    return this.http
      .get<VarianteAnunciable[]>(`${this.base}/variantes`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  mios(incluirCancelados = false): Observable<Anuncio[]> {
    const params = incluirCancelados
      ? new HttpParams().set('incluir_cancelados', true)
      : undefined;
    return this.http
      .get<Anuncio[]>(this.base, { params })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  informar(datos: AnunciarIn): Observable<Anuncio> {
    return this.http
      .post<Anuncio>(this.base, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  cancelar(id: number): Observable<void> {
    return this.http
      .delete<void>(`${this.base}/${id}`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  private traducir(error: HttpErrorResponse): ErrorAbastecimiento {
    if (error.status === 0) {
      return { mensaje: 'No se pudo conectar con el servidor.', codigo: 0 };
    }
    // El backend manda un `detail` con un mensaje pensado para el proveedor
    // ---«ya informó esa prenda, cancélelo antes»---; se muestra ese y no uno
    // genérico, que es lo que le dice qué hacer.
    const detalle = (error.error as { detail?: string } | null)?.detail;
    return {
      mensaje: detalle ?? 'No se pudo completar la operación.',
      codigo: error.status,
    };
  }
}
