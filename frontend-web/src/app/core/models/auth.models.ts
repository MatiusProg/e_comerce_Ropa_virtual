/**
 * P1 · Seguridad y Usuarios — modelos del contrato de la API.
 *
 * Estas interfaces son el espejo exacto de los esquemas Pydantic de
 * `backend/app/modules/seguridad/schemas.py`. Si cambia uno, cambia el otro:
 * son las dos caras del mismo contrato (RNF07).
 */

/** Cuerpo de POST /api/v1/auth/registro — CU-01, paso 3. */
export interface ClienteRegistroIn {
  nombres: string;
  apellidos: string;
  documento: string | null;
  telefono: string | null;
  correo: string;
  contrasena: string;
}

/** Respuesta 201 de POST /api/v1/auth/registro — CU-01, paso 8. */
export interface ClienteRegistradoOut {
  id: number;
  correo: string;
  nombres: string;
  apellidos: string;
  rol: string;
}

/**
 * Longitud mínima de la contraseña.
 * Replica CONTRASENA_LONGITUD_MINIMA del backend.
 */
export const CONTRASENA_LONGITUD_MINIMA = 8;

/**
 * La contraseña debe tener al menos una letra y un número.
 * Replica la validación `_contrasena_fuerte` del backend.
 */
export const CONTRASENA_PATRON = /^(?=.*[A-Za-z])(?=.*\d).+$/;
