import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import {
  ConsultaVitrina,
  Disponibilidad,
  FichaProducto,
  FiltrosDisponibles,
  PaginaVitrina,
} from '../models/tienda.models';

/**
 * Errores previstos de la vitrina.
 *
 * Son muchos menos que los de CU-10 porque los dos casos de uso son de solo
 * lectura: no hay código duplicado, ni colección ajena, ni dependencias que
 * impidan borrar. Lo único que el cliente puede encontrarse es una prenda que
 * dejó de ofrecerse mientras la miraba.
 */
export type ErrorTienda =
  | { tipo: 'no-disponible'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

/**
 * CU-17 y CU-18 — el cliente HTTP de la vitrina pública.
 *
 * **No usa `ProductosService`**, aunque hablen de las mismas tablas: aquel pega
 * contra `/catalogo`, que exige rol Administrador, y esta vitrina se consulta
 * sin sesión. Reutilizarlo haría que cualquier visita anónima recibiera un 401.
 */
@Injectable({ providedIn: 'root' })
export class TiendaService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/tienda`;

  /**
   * La URL absoluta con la que se pinta una imagen.
   *
   * Mismo motivo que en `ProductosService`: el servidor devuelve una ruta que
   * cuelga del **origen** de la API (`/media/...`), no de `apiUrl`, que además
   * lleva `/api/v1`. En desarrollo el origen de la API no es el de Angular, así
   * que dejar la ruta relativa haría que el navegador pidiera la foto al
   * servidor del :4200 y todas las imágenes salieran rotas.
   */
  urlDeImagen(url: string | null): string | null {
    if (!url) return null;
    return `${new URL(environment.apiUrl).origin}${url}`;
  }

  /** Paso 2 de CU-17: la vitrina con sus filtros, su orden y su paginación. */
  listar(consulta: ConsultaVitrina = {}): Observable<PaginaVitrina> {
    let params = new HttpParams();
    if (consulta.busqueda) params = params.set('busqueda', consulta.busqueda);
    if (consulta.categoria_id) params = params.set('categoria_id', consulta.categoria_id);
    if (consulta.talla_id) params = params.set('talla_id', consulta.talla_id);
    if (consulta.color_id) params = params.set('color_id', consulta.color_id);
    if (consulta.temporada_id) params = params.set('temporada_id', consulta.temporada_id);
    if (consulta.coleccion_id) params = params.set('coleccion_id', consulta.coleccion_id);
    if (consulta.precio_min) params = params.set('precio_min', consulta.precio_min);
    if (consulta.precio_max) params = params.set('precio_max', consulta.precio_max);
    if (consulta.orden) params = params.set('orden', consulta.orden);
    if (consulta.pagina) params = params.set('pagina', consulta.pagina);
    if (consulta.tamano) params = params.set('tamano', consulta.tamano);
    return this.http
      .get<PaginaVitrina>(`${this.base}/productos`, { params })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** Paso 3 de CU-18: la ficha con su galería y sus variantes. */
  obtenerFicha(productoId: number): Observable<FichaProducto> {
    return this.http
      .get<FichaProducto>(`${this.base}/productos/${productoId}`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /**
   * CU-19 · en qué sucursales hay stock de la variante elegida.
   *
   * Cuelga de la **variante** y no del producto porque la existencia es por
   * variante: «dónde hay esta blusa» no tiene respuesta útil sin decir en qué
   * talla y en qué color.
   */
  obtenerDisponibilidad(varianteId: number): Observable<Disponibilidad> {
    return this.http
      .get<Disponibilidad>(`${this.base}/variantes/${varianteId}/disponibilidad`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** Las opciones del panel de filtros. Se piden una vez al abrir la vitrina. */
  obtenerFiltros(): Observable<FiltrosDisponibles> {
    return this.http
      .get<FiltrosDisponibles>(`${this.base}/filtros`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  private traducir(error: HttpErrorResponse): ErrorTienda {
    const detalle: string =
      typeof error.error?.detail === 'string' ? error.error.detail : '';

    if (error.status === 404) {
      // El backend responde 404 tanto si la prenda no existe como si dejó de
      // ofrecerse, a propósito. La pantalla dice lo mismo para las dos.
      return {
        tipo: 'no-disponible',
        mensaje: detalle || 'La prenda que busca ya no está disponible.',
      };
    }

    if (error.status === 0) {
      return {
        tipo: 'sistema',
        mensaje: 'No se pudo contactar al servidor. Verifique su conexión.',
      };
    }

    return { tipo: 'sistema', mensaje: detalle || 'No se pudo consultar el catálogo.' };
  }
}
