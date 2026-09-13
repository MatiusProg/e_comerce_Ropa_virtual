/**
 * CU-17 · Consultar catálogo · y CU-18 · Consultar ficha de producto — modelos
 * del contrato.
 *
 * Espejo de `backend/app/modules/catalogo_publico/schemas.py`.
 *
 * Archivo propio y no dentro de `productos.models.ts`, aunque hablen de las
 * mismas tablas. La cara pública **no es** la de CU-10: no trae proveedor, ni
 * precio base, ni estado activo, ni los conteos de gestión. Compartir la
 * interfaz obligaría a marcar media docena de campos como opcionales y a que
 * cada pantalla adivinara cuáles llegan.
 *
 * Los importes viajan como **texto**, por lo mismo que en CU-10: el backend los
 * declara `NUMERIC(10,2)` y convertirlos a coma flotante en el camino mete el
 * redondeo binario justo en el precio de una prenda.
 */

export interface ColorTienda {
  id: number;
  nombre: string;
  hexadecimal: string;
}

export interface TallaTienda {
  id: number;
  tipo_prenda: string;
  codigo: string;
  orden: number;
}

export interface CategoriaTienda {
  id: number;
  categoria_padre_id: number | null;
  nombre: string;
}

export interface TemporadaTienda {
  id: number;
  nombre: string;
}

export interface ColeccionTienda {
  id: number;
  temporada_id: number;
  nombre: string;
}

/** Una tarjeta de la vitrina. Sin variantes: solo el rango de precios. */
export interface ProductoVitrina {
  id: number;
  codigo: string;
  nombre: string;
  categoria_id: number;
  categoria_nombre: string | null;
  temporada_id: number | null;
  coleccion_id: number | null;
  precio_desde: string | null;
  precio_hasta: string | null;
  /** Ruta servida por la API (`/media/...`), no URL absoluta. Ver `urlDeImagen`. */
  imagen_url: string | null;
  colores: ColorTienda[];
  /** Si alguna variante tiene el PNG del vestidor virtual. */
  tiene_vestidor: boolean;
}

export interface PaginaVitrina {
  total: number;
  pagina: number;
  tamano: number;
  items: ProductoVitrina[];
}

export interface ImagenVitrina {
  id: number;
  url: string;
  variante_id: number | null;
  es_principal: boolean;
  orden: number;
}

/**
 * Una combinación talla × color ofrecible.
 *
 * `imagen_vestidor_url` es la mitad de la costura **C5**: el PNG con fondo
 * transparente de esta variante, que es lo que consume el vestidor virtual de
 * la app móvil. En la web viaja igual —el contrato es uno solo— y sirve para
 * saber si la prenda se puede probar, aunque la cámara sea del teléfono.
 */
export interface VarianteVitrina {
  id: number;
  sku: string;
  precio: string;
  talla_id: number;
  talla_codigo: string | null;
  color_id: number;
  color_nombre: string | null;
  color_hexadecimal: string | null;
  imagen_vestidor_url: string | null;
}

export interface FichaProducto {
  id: number;
  codigo: string;
  nombre: string;
  descripcion: string | null;
  categoria_id: number;
  categoria_nombre: string | null;
  temporada_id: number | null;
  coleccion_id: number | null;
  precio_desde: string | null;
  precio_hasta: string | null;
  imagenes: ImagenVitrina[];
  /** Ya vienen ordenadas por el orden del maestro de tallas, no alfabético. */
  variantes: VarianteVitrina[];
  tallas: TallaTienda[];
  colores: ColorTienda[];
  tiene_vestidor: boolean;
}

/**
 * CU-19 · cuánto hay de una variante en una sucursal.
 *
 * La forma la fija el contrato de la costura **C1**. `cantidad_reservada` no
 * viaja a propósito: al cliente le sirve saber cuánto puede llevarse, y
 * publicar lo apartado dejaría deducir el movimiento comercial de cada tienda.
 */
export interface DisponibilidadSucursal {
  sucursal_id: number;
  sucursal_nombre: string;
  ciudad_nombre: string;
  cantidad_disponible: number;
}

export interface Disponibilidad {
  variante_id: number;
  sku: string;
  talla_codigo: string | null;
  color_nombre: string | null;
  /** Suma de toda la red. Viene calculado para poder decir «sin stock» de una
   *  sola lectura. */
  total_disponible: number;
  /** Solo las sucursales donde hay algo. */
  sucursales: DisponibilidadSucursal[];
}

/** Las opciones del panel de filtros, con lo que el catálogo realmente ofrece. */
export interface FiltrosDisponibles {
  categorias: CategoriaTienda[];
  tallas: TallaTienda[];
  colores: ColorTienda[];
  temporadas: TemporadaTienda[];
  colecciones: ColeccionTienda[];
  precio_min: string | null;
  precio_max: string | null;
}

/**
 * CU-20 · la lista de favoritos.
 *
 * Los items son `ProductoVitrina`, **la misma tarjeta que el catálogo**: la
 * pantalla de favoritos muestra exactamente lo mismo, y duplicar el tipo
 * obligaría a agregar dos veces cada campo nuevo.
 */
export interface PaginaFavoritos {
  total: number;
  pagina: number;
  tamano: number;
  items: ProductoVitrina[];
}

export type OrdenVitrina = 'novedades' | 'precio_asc' | 'precio_desc' | 'nombre';

export interface ConsultaVitrina {
  busqueda?: string;
  categoria_id?: number;
  talla_id?: number;
  color_id?: number;
  temporada_id?: number;
  coleccion_id?: number;
  precio_min?: string;
  precio_max?: string;
  orden?: OrdenVitrina;
  pagina?: number;
  tamano?: number;
}
