/**
 * P3 · Catálogo — CU-38 Registrar productos del proveedor.
 *
 * Espejo exacto de `backend/app/modules/catalogo/proveedor_schemas.py`. Si
 * cambia uno, cambia el otro: son las dos caras del mismo contrato (RNF07).
 *
 * Los tipos de salida —producto, variante, página— NO se redeclaran acá: son
 * los mismos de CU-10 y viven en `productos.models.ts`. El Proveedor ve el
 * mismo producto que el Administrador; lo que cambia es cuál puede ver.
 */

import { Categoria, Color, Talla } from './maestros.models';
import { Coleccion, Temporada } from './temporadas.models';

/**
 * Cuerpo de POST /catalogo/mis-productos.
 *
 * **No lleva `proveedor_id` ni `activo`, y ahí está todo el caso de uso.** El
 * ámbito sale del token, y lo que registra el Proveedor nace inactivo: publicar
 * en la vitrina es del Administrador, por CU-10.
 */
export interface MiProductoCrearIn {
  codigo: string;
  nombre: string;
  descripcion: string | null;
  categoria_id: number;
  temporada_id: number | null;
  coleccion_id: number | null;
  precio_base: string;
}

/** Cuerpo de PATCH /catalogo/mis-productos/{id}. Sólo lo que cambia. */
export interface MiProductoEditarIn {
  codigo?: string;
  nombre?: string;
  descripcion?: string | null;
  categoria_id?: number;
  temporada_id?: number | null;
  coleccion_id?: number | null;
  precio_base?: string;
}

/**
 * Respuesta de GET /catalogo/mis-productos/listas.
 *
 * Existe porque los routers de CU-08 y de temporadas exigen rol Administrador
 * a nivel de router y, además de leer, permiten crear y borrar: aflojar esa
 * guarda para llenar un selector le daría al Proveedor permiso para crear
 * categorías.
 */
export interface ListasDelFormulario {
  categorias: Categoria[];
  tallas: Talla[];
  colores: Color[];
  temporadas: Temporada[];
  colecciones: Coleccion[];
}

/** Filtros del listado. `proveedor_id` no está: no es del cliente. */
export interface FiltrosMisProductos {
  pagina?: number;
  tamano?: number;
  busqueda?: string | null;
  categoria_id?: number | null;
  temporada_id?: number | null;
  coleccion_id?: number | null;
  activo?: boolean | null;
}
