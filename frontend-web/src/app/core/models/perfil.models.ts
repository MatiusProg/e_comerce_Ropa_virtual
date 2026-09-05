/**
 * CU-04 · Gestionar perfil del cliente — modelos del contrato.
 *
 * Espejo de los esquemas de `backend/app/modules/seguridad/schemas.py`.
 * Si cambia uno, cambia el otro: son las dos caras del mismo contrato (RNF07).
 */

/** Una dirección de entrega del cliente (paso 2). */
export interface Direccion {
  id: number;
  ciudad_id: number;
  ciudad: string;
  alias: string;
  direccion: string;
  referencia: string | null;
  predeterminada: boolean;
}

/**
 * El perfil completo que muestra el paso 2.
 *
 * Las categorías preferidas que menciona ese paso quedan fuera del Ciclo 1:
 * dependen de CU-08. Ver §6.11.3 de `docs/06-decisiones-tecnicas.md`.
 */
export interface Perfil {
  nombres: string;
  apellidos: string;
  correo: string;
  documento: string | null;
  telefono: string | null;
  talla_superior: string | null;
  talla_inferior: string | null;
  talla_calzado: string | null;
  direcciones: Direccion[];
}

/**
 * Cuerpo de PATCH /perfil — pasos 3 a 5.
 *
 * Es parcial a propósito: el servidor solo toca los campos que llegan. Enviar
 * un campo vacío borra el dato; no enviarlo lo deja como estaba.
 */
export type PerfilEditar = Partial<{
  nombres: string;
  apellidos: string;
  correo: string;
  documento: string | null;
  telefono: string | null;
  talla_superior: string | null;
  talla_inferior: string | null;
  talla_calzado: string | null;
}>;

/** Cuerpo de POST /perfil/direcciones — flujo alternativo 3a. */
export interface DireccionCrear {
  ciudad_id: number;
  alias: string;
  direccion: string;
  referencia: string | null;
  predeterminada: boolean;
}

/** Cuerpo de PUT /perfil/contrasena — flujo alternativo 3c. */
export interface CambioContrasena {
  contrasena_actual: string;
  contrasena_nueva: string;
  contrasena_repetida: string;
}

/**
 * Tallas sugeridas en los selectores.
 *
 * No son un catálogo de la base: la tabla `talla` es de CU-08 y sirve a las
 * variantes de producto, no al perfil. Acá el dato es texto libre corto, así
 * que se ofrecen las tallas habituales como atajo y se admite escribir otra.
 */
export const TALLAS_SUPERIOR = ['XS', 'S', 'M', 'L', 'XL', 'XXL'] as const;
export const TALLAS_INFERIOR = ['28', '30', '32', '34', '36', '38', '40', '42'] as const;
export const TALLAS_CALZADO = ['35', '36', '37', '38', '39', '40', '41', '42', '43', '44'] as const;
