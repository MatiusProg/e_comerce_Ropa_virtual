/**
 * CU-10 · Gestionar productos y variantes — modelos del contrato.
 *
 * Espejo de `backend/app/modules/catalogo/schemas.py`.
 *
 * Archivo propio y no dentro de un `catalogo.models.ts` compartido, por el
 * mismo motivo que en el Ciclo 1: los maestros (CU-08) y las temporadas (CU-09)
 * ya tienen el suyo, y así ninguna rama comparte líneas con otra.
 *
 * Los importes viajan como **texto**, no como `number`. El backend los declara
 * `NUMERIC(10,2)` y los serializa en decimal; convertirlos a coma flotante en
 * el camino introduce el redondeo binario justo en el precio de una prenda.
 */

/** Una combinación talla × color. Es el SKU y la unidad de negocio (D1). */
export interface Variante {
  id: number;
  producto_id: number;
  talla_id: number;
  color_id: number;
  sku: string;
  precio: string;
  activa: boolean;
  /** Resueltos por el servidor para dibujar la tabla sin cruzar los maestros. */
  talla_codigo: string | null;
  color_nombre: string | null;
  color_hexadecimal: string | null;
}

/** Fila del listado del paso 2. No trae las variantes, solo cuántas hay. */
export interface ProductoResumen {
  id: number;
  codigo: string;
  nombre: string;
  categoria_id: number;
  proveedor_id: number | null;
  temporada_id: number | null;
  coleccion_id: number | null;
  precio_base: string;
  activo: boolean;
  categoria_nombre: string | null;
  variantes_totales: number;
  variantes_activas: number;
}

/** Detalle del producto, con sus variantes ya ordenadas por talla. */
export interface Producto extends ProductoResumen {
  descripcion: string | null;
  variantes: Variante[];
}

/** Página del listado. El total viaja aparte para poder dibujar el paginador. */
export interface PaginaProductos {
  total: number;
  pagina: number;
  tamano: number;
  items: ProductoResumen[];
}

export interface FiltrosProductos {
  busqueda?: string;
  categoria_id?: number;
  temporada_id?: number;
  coleccion_id?: number;
  proveedor_id?: number;
  activo?: boolean;
  pagina?: number;
  tamano?: number;
}

/** Alta de producto (pasos 4 a 6). */
export interface ProductoCrear {
  codigo: string;
  nombre: string;
  descripcion?: string | null;
  categoria_id: number;
  proveedor_id?: number | null;
  temporada_id?: number | null;
  coleccion_id?: number | null;
  precio_base: string;
  activo?: boolean;
}

/**
 * Edición (flujo alternativo 3a). Solo viaja lo que cambió.
 *
 * Para `temporada_id` y `coleccion_id`, **no enviar el campo** es distinto de
 * enviarlo en `null`: lo primero lo deja como está, lo segundo saca al producto
 * de la temporada o de la colección. Por eso el formulario arma el cuerpo campo
 * por campo en vez de mandar el objeto entero.
 */
export interface ProductoEditar {
  codigo?: string;
  nombre?: string;
  descripcion?: string | null;
  categoria_id?: number;
  proveedor_id?: number | null;
  temporada_id?: number | null;
  coleccion_id?: number | null;
  precio_base?: string;
}

/** Paso 7: generación masiva del producto cartesiano talla × color. */
export interface GenerarVariantes {
  tallas: number[];
  colores: number[];
  /** Si no viene, cada variante nace con el precio base del producto. */
  precio?: string | null;
}

/**
 * Resultado de la generación.
 *
 * `omitidas` no es un error: son las combinaciones que ya existían. Viaja para
 * que la interfaz lo pueda decir, en vez de dejar al Administrador comparando
 * la tabla antes y después.
 */
export interface ResultadoGeneracion {
  creadas: number;
  omitidas: number;
  variantes: Variante[];
}

/** Alta suelta de una variante (flujo alternativo 7a). */
export interface VarianteCrear {
  talla_id: number;
  color_id: number;
  precio?: string | null;
  activa?: boolean;
}

/** Edición de una variante (7b y 7c). La talla y el color no se editan. */
export interface VarianteEditar {
  precio?: string;
  activa?: boolean;
}

// --- CU-11 · Imágenes de producto ----------------------------------------
// Van en este archivo y no en uno propio porque CU-10 y CU-11 son de la misma
// persona y se consumen desde la misma pantalla: separarlos solo agregaría un
// segundo servicio HTTP contra el mismo árbol de recursos.

/** Una imagen del producto o de una de sus variantes. */
export interface Imagen {
  id: number;
  producto_id: number;
  variante_id: number | null;
  /** Ruta relativa dentro del volumen, tal como la guarda la base (§6.8). */
  ruta: string;
  /** La misma ruta ya prefijada con MEDIA_URL. Es la que se usa en el `src`. */
  url: string;
  es_principal: boolean;
  /** PNG con fondo transparente: el activo del vestidor virtual (S5). */
  es_transparente: boolean;
  orden: number;
  variante_sku: string | null;
  /** «M · Negro», resuelto por el servidor para rotular la miniatura. */
  variante_etiqueta: string | null;
}

/**
 * Asociar a una variante o cambiar el orden (3a, 3d).
 *
 * `variante_id` en `null` **desasocia**; no enviarlo lo deja como está. El
 * componente arma el cuerpo campo por campo por eso mismo.
 */
export interface ImagenEditar {
  variante_id?: number | null;
  orden?: number;
}

/** Reordenar: la lista completa de una sola vez, no un movimiento por vez. */
export interface ReordenarImagenes {
  imagenes: number[];
}
