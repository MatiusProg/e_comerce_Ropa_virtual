import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import {
  FiltrosMisProductos,
  ListasDelFormulario,
  MiProductoCrearIn,
  MiProductoEditarIn,
} from '../models/proveedor.models';
import {
  GenerarVariantes,
  PaginaProductos,
  Producto,
  ResultadoGeneracion,
} from '../models/productos.models';

/**
 * Errores previstos de CU-38, traducidos desde el código HTTP.
 *
 * `no-encontrado` cubre a la vez «no existe» y «es de otro proveedor», y no es
 * una imprecisión de esta traducción: es lo que responde el servidor. Un 403
 * confirmaría que ese identificador es un producto real de la competencia, y
 * recorrer los números sería un censo del catálogo ajeno.
 */
export type ErrorMisProductos =
  | { tipo: 'codigo-duplicado'; mensaje: string }
  | { tipo: 'coleccion-ajena'; mensaje: string }
  | { tipo: 'sku-largo'; mensaje: string }
  | { tipo: 'no-encontrado'; mensaje: string }
  | { tipo: 'sin-ficha'; mensaje: string }
  | { tipo: 'sin-permiso'; mensaje: string }
  | { tipo: 'validacion'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

/**
 * P3 · Catálogo — CU-38 Registrar productos del proveedor (RF37).
 *
 * Servicio aparte de `ProductosService` aunque hablen de la misma entidad. No
 * es duplicación: son **dos contratos distintos** —otras rutas, otro rol, otro
 * alcance— y fundirlos obligaría a que cada llamada supiera con qué rol se está
 * ejecutando. La pantalla del Proveedor no tiene que poder pedir, ni por
 * accidente, un endpoint del Administrador.
 */
@Injectable({ providedIn: 'root' })
export class ProveedorService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/catalogo/mis-productos`;

  /**
   * Los maestros activos para los selectores del formulario.
   *
   * Es un endpoint propio del Proveedor: los de CU-08 exigen Administrador.
   */
  listas(): Observable<ListasDelFormulario> {
    return this.http
      .get<ListasDelFormulario>(`${this.base}/listas`)
      .pipe(catchError((e: HttpErrorResponse) => throwError(() => this.traducir(e))));
  }

  /**
   * Lo que abastece este proveedor.
   *
   * No hay parámetro `proveedor_id` y no es un olvido: el ámbito lo resuelve el
   * servidor con el token. Si fuera un filtro más, bastaría con cambiarlo.
   */
  listar(filtros: FiltrosMisProductos = {}): Observable<PaginaProductos> {
    let params = new HttpParams();
    if (filtros.busqueda) params = params.set('busqueda', filtros.busqueda);
    if (filtros.categoria_id) params = params.set('categoria_id', filtros.categoria_id);
    if (filtros.temporada_id) params = params.set('temporada_id', filtros.temporada_id);
    if (filtros.coleccion_id) params = params.set('coleccion_id', filtros.coleccion_id);
    if (filtros.activo !== undefined && filtros.activo !== null) {
      params = params.set('activo', filtros.activo);
    }
    if (filtros.pagina) params = params.set('pagina', filtros.pagina);
    if (filtros.tamano) params = params.set('tamano', filtros.tamano);

    return this.http
      .get<PaginaProductos>(this.base, { params })
      .pipe(catchError((e: HttpErrorResponse) => throwError(() => this.traducir(e))));
  }

  obtener(id: number): Observable<Producto> {
    return this.http
      .get<Producto>(`${this.base}/${id}`)
      .pipe(catchError((e: HttpErrorResponse) => throwError(() => this.traducir(e))));
  }

  /** Registra una prenda. Nace inactiva: publicarla es del Administrador. */
  registrar(datos: MiProductoCrearIn): Observable<Producto> {
    return this.http
      .post<Producto>(this.base, datos)
      .pipe(catchError((e: HttpErrorResponse) => throwError(() => this.traducir(e))));
  }

  editar(id: number, datos: MiProductoEditarIn): Observable<Producto> {
    return this.http
      .patch<Producto>(`${this.base}/${id}`, datos)
      .pipe(catchError((e: HttpErrorResponse) => throwError(() => this.traducir(e))));
  }

  /**
   * Retira una prenda que ya no abastece.
   *
   * El método no recibe el estado y es a propósito: **sólo se puede retirar**.
   * Un parámetro booleano invitaría a llamar con `true` desde la pantalla, y el
   * servidor respondería 403 — publicar es del Administrador.
   */
  retirar(id: number): Observable<Producto> {
    return this.http
      .patch<Producto>(`${this.base}/${id}/estado`, { activo: false })
      .pipe(catchError((e: HttpErrorResponse) => throwError(() => this.traducir(e))));
  }

  /** Las combinaciones talla × color en que abastece esa prenda. */
  generarVariantes(id: number, datos: GenerarVariantes): Observable<ResultadoGeneracion> {
    return this.http
      .post<ResultadoGeneracion>(`${this.base}/${id}/variantes`, datos)
      .pipe(catchError((e: HttpErrorResponse) => throwError(() => this.traducir(e))));
  }

  // --- Traducción de errores ---------------------------------------------

  private traducir(error: HttpErrorResponse): ErrorMisProductos {
    const detalle: string = error.error?.detail ?? '';

    if (error.status === 409) {
      return {
        tipo: 'codigo-duplicado',
        mensaje: detalle || 'Ya existe un producto con ese código.',
      };
    }
    if (error.status === 404) {
      // El servidor usa el mismo 404 para «no existe» y «no es tuyo». Se
      // distingue la falta de ficha porque ésa sí lleva a otra acción: hablar
      // con el administrador, no volver al listado.
      if (detalle.toLowerCase().includes('ficha de proveedor')) {
        return { tipo: 'sin-ficha', mensaje: detalle };
      }
      return { tipo: 'no-encontrado', mensaje: detalle || 'El producto ya no existe.' };
    }
    if (error.status === 403) {
      return {
        tipo: 'sin-permiso',
        mensaje: detalle || 'No tiene permisos para realizar esta operación.',
      };
    }
    if (error.status === 422) {
      const texto = detalle.toLowerCase();
      if (texto.includes('colección') || texto.includes('coleccion')) {
        return { tipo: 'coleccion-ajena', mensaje: detalle };
      }
      if (texto.includes('sku')) {
        return { tipo: 'sku-largo', mensaje: detalle };
      }
      return { tipo: 'validacion', mensaje: detalle || 'Revise los datos del formulario.' };
    }
    if (error.status === 0) {
      return {
        tipo: 'sistema',
        mensaje: 'No se pudo contactar al servidor. Verifique su conexión.',
      };
    }
    return { tipo: 'sistema', mensaje: detalle || 'No se pudo completar la operación.' };
  }
}
