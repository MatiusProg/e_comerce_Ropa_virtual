import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import {
  FiltrosProductos,
  GenerarVariantes,
  PaginaProductos,
  Producto,
  ProductoCrear,
  ProductoEditar,
  ResultadoGeneracion,
  Variante,
  VarianteCrear,
  VarianteEditar,
} from '../models/productos.models';

/**
 * Errores previstos de CU-10, traducidos desde el código HTTP.
 *
 * Se distinguen y no se colapsan en «error» porque cada uno lleva a una acción
 * distinta en la pantalla: `codigo-duplicado` señala el campo sin cerrar el
 * diálogo (E1); `coleccion-ajena` señala dos campos a la vez (E2);
 * `con-dependencias` ofrece desactivar en lugar de eliminar (E3); y
 * `sku-largo` no es culpa del formulario de variantes sino del código del
 * producto, así que el mensaje tiene que mandar a otra pantalla.
 */
export type ErrorProductos =
  | { tipo: 'codigo-duplicado'; mensaje: string }
  | { tipo: 'coleccion-ajena'; mensaje: string }
  | { tipo: 'sku-largo'; mensaje: string }
  | { tipo: 'con-dependencias'; mensaje: string }
  | { tipo: 'no-encontrado'; mensaje: string }
  | { tipo: 'validacion'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

@Injectable({ providedIn: 'root' })
export class ProductosService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/catalogo`;

  // --- Productos ---------------------------------------------------------

  listar(filtros: FiltrosProductos = {}): Observable<PaginaProductos> {
    let params = new HttpParams();
    if (filtros.busqueda) params = params.set('busqueda', filtros.busqueda);
    if (filtros.categoria_id) params = params.set('categoria_id', filtros.categoria_id);
    if (filtros.temporada_id) params = params.set('temporada_id', filtros.temporada_id);
    if (filtros.coleccion_id) params = params.set('coleccion_id', filtros.coleccion_id);
    if (filtros.proveedor_id) params = params.set('proveedor_id', filtros.proveedor_id);
    if (filtros.activo !== undefined) params = params.set('activo', filtros.activo);
    if (filtros.pagina) params = params.set('pagina', filtros.pagina);
    if (filtros.tamano) params = params.set('tamano', filtros.tamano);
    return this.http
      .get<PaginaProductos>(`${this.base}/productos`, { params })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  obtener(id: number): Observable<Producto> {
    return this.http
      .get<Producto>(`${this.base}/productos/${id}`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  crear(datos: ProductoCrear): Observable<Producto> {
    return this.http
      .post<Producto>(`${this.base}/productos`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** Flujo alternativo 3a. Solo viaja lo que cambió. */
  editar(id: number, datos: ProductoEditar): Observable<Producto> {
    return this.http
      .patch<Producto>(`${this.base}/productos/${id}`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** Flujo alternativo 3b. Desactivar arrastra las variantes. */
  cambiarEstado(id: number, activo: boolean): Observable<Producto> {
    return this.http
      .patch<Producto>(`${this.base}/productos/${id}/estado`, { activo })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** Excepción E3: falla si el producto ya tiene existencias o reservas. */
  eliminar(id: number): Observable<void> {
    return this.http
      .delete<void>(`${this.base}/productos/${id}`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  // --- Variantes ---------------------------------------------------------

  /** Paso 7: el producto cartesiano de las tallas por los colores elegidos. */
  generarVariantes(
    productoId: number,
    datos: GenerarVariantes,
  ): Observable<ResultadoGeneracion> {
    return this.http
      .post<ResultadoGeneracion>(`${this.base}/productos/${productoId}/variantes/generar`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** Flujo alternativo 7a. */
  crearVariante(productoId: number, datos: VarianteCrear): Observable<Variante> {
    return this.http
      .post<Variante>(`${this.base}/productos/${productoId}/variantes`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** Flujos alternativos 7b y 7c: precio y estado. */
  editarVariante(id: number, datos: VarianteEditar): Observable<Variante> {
    return this.http
      .patch<Variante>(`${this.base}/variantes/${id}`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  eliminarVariante(id: number): Observable<void> {
    return this.http
      .delete<void>(`${this.base}/variantes/${id}`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  // --- Traducción de errores ---------------------------------------------

  private traducir(error: HttpErrorResponse): ErrorProductos {
    const detalle: string =
      typeof error.error?.detail === 'string' ? error.error.detail : '';

    if (error.status === 404) {
      return { tipo: 'no-encontrado', mensaje: detalle || 'El registro ya no existe.' };
    }

    if (error.status === 409) {
      // El backend usa el mismo 409 para E1 y E3, y se distinguen por el texto
      // que el propio caso de uso redacta. Se busca «eliminarse», que es la
      // palabra de la E3 y no aparece en la de código duplicado.
      if (detalle.includes('eliminarse')) {
        return { tipo: 'con-dependencias', mensaje: detalle };
      }
      return {
        tipo: 'codigo-duplicado',
        mensaje: detalle || 'Ya existe un registro con ese código.',
      };
    }

    if (error.status === 422) {
      if (detalle.includes('colección')) {
        return { tipo: 'coleccion-ajena', mensaje: detalle };
      }
      if (detalle.includes('SKU')) {
        return { tipo: 'sku-largo', mensaje: detalle };
      }
      // FastAPI manda `detail` como lista en los errores de validación de
      // esquema, así que `detalle` queda vacío y se usa el genérico.
      return {
        tipo: 'validacion',
        mensaje: detalle || 'Revise los datos del formulario.',
      };
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
