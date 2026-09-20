import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, of } from 'rxjs';

import { environment } from '../../../environments/environment';

/**
 * CU-34 · Conversar con el asistente virtual.
 *
 * Espejo de `backend/app/modules/ia/asistente_schemas.py`.
 *
 * **El historial lo manda la pantalla.** No hay tabla de conversaciones en el
 * servidor —ver `asistente_service.py`— así que los turnos viven mientras la
 * pantalla está abierta y se reenvían con cada pregunta. Es lo que permite
 * entender «¿y en talla M?».
 */

export interface Turno {
  pregunta: string;
  respuesta: string;

  /**
   * Los productos que la respuesta menciona.
   *
   * **Ya validados contra el catálogo por el servidor**: un código que el
   * modelo invente no llega hasta acá, así que un enlace nunca lleva a una
   * ficha vacía.
   */
  productos: number[];
}

export interface RespuestaAsistente {
  texto: string;
  productos: number[];
}

export interface EstadoAsistente {
  disponible: boolean;
  ejemplos: string[];
}

@Injectable({ providedIn: 'root' })
export class AsistenteService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/asistente`;

  /**
   * Si se puede conversar, y con qué empezar.
   *
   * Ante cualquier fallo devuelve no disponible en vez de propagar: lo peor
   * que pasa es que no se ofrezca el asistente, y eso no puede romper la
   * pantalla que lo contiene.
   */
  disponible(): Observable<EstadoAsistente> {
    return this.http
      .get<EstadoAsistente>(`${this.base}/disponible`)
      .pipe(catchError(() => of({ disponible: false, ejemplos: [] })));
  }

  preguntar(pregunta: string, historial: Turno[]): Observable<RespuestaAsistente> {
    return this.http.post<RespuestaAsistente>(this.base, {
      pregunta,
      // Solo los últimos diez: es el tope del servidor y evita que el cuerpo
      // crezca sin límite con la conversación.
      historial: historial.slice(-10).map((t) => ({
        pregunta: t.pregunta,
        respuesta: t.respuesta,
      })),
    });
  }
}
