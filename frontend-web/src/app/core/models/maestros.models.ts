/**
 * CU-08 · Gestionar categorías, tallas y colores — modelos del contrato.
 *
 * Espejo de `backend/app/modules/catalogo/maestros/schemas.py`. Si cambia uno,
 * cambia el otro: son las dos caras del mismo contrato (RNF07).
 *
 * Archivo propio, y no un bloque más en un `catalogo.models.ts` compartido, por
 * lo decidido en la §6.11.5: el CU-09 se desarrolla en paralelo sobre el mismo
 * paquete P3.
 */

/** Un nodo del árbol de categorías. La jerarquía llega armada del servidor. */
export interface Categoria {
  id: number;
  categoria_padre_id: number | null;
  nombre: string;
  orden: number;
  activa: boolean;
  subcategorias: Categoria[];
}

/**
 * Una categoría aplanada, con su profundidad, para mostrarla en una lista o en
 * un selector sin perder de vista dónde está.
 */
export interface CategoriaPlana {
  categoria: Categoria;
  nivel: number;
}

export interface CategoriaCrear {
  nombre: string;
  categoria_padre_id: number | null;
  orden: number;
  activa: boolean;
}

/**
 * Edición. `categoria_padre_id` presente y en `null` significa convertirla en
 * raíz; ausente significa dejarla donde está. No son lo mismo.
 */
export interface CategoriaEditar {
  nombre?: string;
  categoria_padre_id?: number | null;
  orden?: number;
}

export interface Talla {
  id: number;
  tipo_prenda: string;
  codigo: string;
  orden: number;
  activa: boolean;
}

export interface TallaCrear {
  tipo_prenda: string;
  codigo: string;
  orden: number;
  activa: boolean;
}

export interface TallaEditar {
  tipo_prenda?: string;
  codigo?: string;
  orden?: number;
}

export interface Color {
  id: number;
  nombre: string;
  hexadecimal: string;
  activo: boolean;
}

export interface ColorCrear {
  nombre: string;
  hexadecimal: string;
  activo: boolean;
}

export interface ColorEditar {
  nombre?: string;
  hexadecimal?: string;
}

/**
 * Formato del color, idéntico al `CHECK ck_color_hex` de la base y al
 * validador del backend.
 */
export const HEXADECIMAL_PATRON = /^#[0-9A-Fa-f]{6}$/;

/**
 * Aplana el árbol en el orden en que se ve, anotando la profundidad.
 *
 * Sirve para la tabla y para el selector de categoría padre, que necesitan una
 * lista pero tienen que seguir mostrando la jerarquía.
 */
export function aplanarCategorias(arbol: Categoria[], nivel = 0): CategoriaPlana[] {
  return arbol.flatMap((categoria) => [
    { categoria, nivel },
    ...aplanarCategorias(categoria.subcategorias, nivel + 1),
  ]);
}

/**
 * Identificadores que no pueden ser padre de `id`: ella misma y su descendencia.
 *
 * Es la excepción E2 resuelta en la interfaz: en vez de dejar elegir un padre
 * inválido y mostrar el error del servidor, esas opciones no se ofrecen. El
 * servidor la valida igual — la interfaz no es la que decide.
 */
export function idsProhibidosComoPadre(arbol: Categoria[], id: number): Set<number> {
  const prohibidos = new Set<number>([id]);

  const marcarDescendencia = (nodo: Categoria): void => {
    prohibidos.add(nodo.id);
    nodo.subcategorias.forEach(marcarDescendencia);
  };

  const buscar = (nodos: Categoria[]): boolean =>
    nodos.some((nodo) => {
      if (nodo.id === id) {
        nodo.subcategorias.forEach(marcarDescendencia);
        return true;
      }
      return buscar(nodo.subcategorias);
    });

  buscar(arbol);
  return prohibidos;
}
