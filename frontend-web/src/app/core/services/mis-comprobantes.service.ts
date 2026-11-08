import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';

/** Espejo de `ComprobanteOut` (backend/app/modules/comprobantes/schemas.py). */
export interface ComprobanteCliente {
  tipo: 'COMPRA' | 'DEVOLUCION';
  documento: 'RECIBO' | 'NOTA_DEVOLUCION' | 'NOTA_CAMBIO' | null;
  codigo: string;
  referencia: string;
  fecha: string;
  fecha_texto: string;
  total: string;
  estado: string;
  detalle: string | null;
  token: string | null;
  url_verificacion: string | null;
  descargable: boolean;
}

export interface CriterioComprobantes {
  tipo: 'COMPRAS' | 'DEVOLUCIONES' | 'TODO';
  cantidad: number | null;
  desde: string | null;
  hasta: string | null;
  estado: string | null;
}

export interface ResultadoComprobantes {
  entendido: boolean;
  interprete: 'reglas';
  resumen: string | null;
  motivo: string | null;
  ejemplos: string[];
  criterio: CriterioComprobantes | null;
  avisos: string[];
  encontrados: number;
  items: ComprobanteCliente[];
}

/** Lo que muestra la página pública del QR. Sin datos del cliente. */
export interface VerificacionComprobante {
  valido: boolean;
  tienda: string;
  documento: string;
  codigo: string;
  referencia: string;
  fecha: string;
  fecha_texto: string;
  total: string;
  estado: string;
}

/**
 * CU-46 · Consultar mis comprobantes por voz.
 *
 * La consulta es del Cliente (con token); la verificación y el QR son públicos
 * y se identifican con el token firmado del comprobante.
 */
@Injectable({ providedIn: 'root' })
export class MisComprobantesService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/tienda/mis-comprobantes`;
  private readonly publico = `${environment.apiUrl}/publico/comprobantes`;

  consultar(texto: string): Observable<ResultadoComprobantes> {
    return this.http
      .post<ResultadoComprobantes>(`${this.base}/consulta`, { texto })
      .pipe(catchError((e) => throwError(() => this.mensaje(e, 'No se pudo hacer la consulta.'))));
  }

  verificar(token: string): Observable<VerificacionComprobante> {
    return this.http
      .get<VerificacionComprobante>(`${this.publico}/${encodeURIComponent(token)}`)
      .pipe(catchError((e) => throwError(() => this.mensaje(e, 'No se pudo verificar.'))));
  }

  /** El QR lo dibuja el servidor (SVG): se muestra con un `<img>` y no pide sesión. */
  urlQr(token: string): string {
    return `${this.publico}/${encodeURIComponent(token)}/qr.svg`;
  }

  private mensaje(error: HttpErrorResponse, porOmision: string): string {
    const detalle: unknown = error.error?.detail;
    if (typeof detalle === 'string') return detalle;
    if (error.status === 0) return 'No se pudo contactar al servidor. Verificá tu conexión.';
    if (error.status === 422) return 'Escribí entre 2 y 300 caracteres.';
    return porOmision;
  }
}
