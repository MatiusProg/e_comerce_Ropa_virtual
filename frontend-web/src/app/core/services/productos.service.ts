import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import {
  FiltrosProductos,
  GenerarVariantes,
  Imagen,
  ImagenEditar,
  PaginaProductos,
  Producto,
  ProductoCrear,
  ProductoEditar,
  ReordenarImagenes,
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
  | { tipo: 'archivo-invalido'; mensaje: string }
  | { tipo: 'sin-transparencia'; mensaje: string }
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

  // --- Imágenes (CU-11) --------------------------------------------------

  /**
   * La URL absoluta con la que se pinta una imagen.
   *
   * El servidor devuelve una ruta que cuelga del **origen** de la API
   * (`/media/...`), no de `apiUrl`, que además lleva `/api/v1`. Y en desarrollo
   * el origen de la API no es el de Angular: dejar la ruta relativa haría que
   * el navegador pidiera la foto al servidor de desarrollo del :4200 y todas
   * las miniaturas saldrían rotas.
   */
  urlDeImagen(imagen: Imagen): string {
    return `${new URL(environment.apiUrl).origin}${imagen.url}`;
  }

  listarImagenes(productoId: number): Observable<Imagen[]> {
    return this.http
      .get<Imagen[]>(`${this.base}/productos/${productoId}/imagenes`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /**
   * Pasos 3 y 4: sube el archivo.
   *
   * Va como `FormData` y NO se le pone `Content-Type` a mano: el navegador
   * tiene que generarlo él para incluir el `boundary` del multipart. Fijarlo
   * produce un cuerpo que el servidor no puede separar.
   */
  subirImagen(
    productoId: number,
    archivo: File,
    varianteId?: number | null,
  ): Observable<Imagen> {
    const cuerpo = new FormData();
    cuerpo.append('archivo', archivo);
    let params = new HttpParams();
    if (varianteId != null) params = params.set('variante_id', varianteId);
    return this.http
      .post<Imagen>(`${this.base}/productos/${productoId}/imagenes`, cuerpo, { params })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** Flujos 3a y 3d sobre una imagen. */
  editarImagen(id: number, datos: ImagenEditar): Observable<Imagen> {
    return this.http
      .patch<Imagen>(`${this.base}/imagenes/${id}`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** Flujo 3b. Devuelve la galería entera: marcar una desmarca la anterior. */
  marcarPrincipal(id: number, esPrincipal: boolean): Observable<Imagen[]> {
    return this.http
      .patch<Imagen[]>(`${this.base}/imagenes/${id}/principal`, { es_principal: esPrincipal })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** Flujo 3c: el PNG del vestidor virtual. El servidor verifica el alfa. */
  marcarTransparente(id: number, esTransparente: boolean): Observable<Imagen[]> {
    return this.http
      .patch<Imagen[]>(`${this.base}/imagenes/${id}/transparente`, {
        es_transparente: esTransparente,
      })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** Flujo 3d: el orden completo de una sola vez. */
  reordenarImagenes(productoId: number, datos: ReordenarImagenes): Observable<Imagen[]> {
    return this.http
      .put<Imagen[]>(`${this.base}/productos/${productoId}/imagenes/orden`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  eliminarImagen(id: number): Observable<void> {
    return this.http
      .delete<void>(`${this.base}/imagenes/${id}`)
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
      // CU-11. Se separan porque llevan a acciones distintas: «sin
      // transparencia» manda a conseguir otro archivo, y el resto son
      // problemas del archivo que se acaba de elegir.
      if (detalle.includes('transparente') || detalle.includes('vestidor')) {
        return { tipo: 'sin-transparencia', mensaje: detalle };
      }
      if (
        detalle.includes('imagen') ||
        detalle.includes('MB') ||
        detalle.includes('píxeles')
      ) {
        return { tipo: 'archivo-invalido', mensaje: detalle };
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
