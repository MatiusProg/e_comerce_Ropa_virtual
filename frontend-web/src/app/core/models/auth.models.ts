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

/** Cuerpo de POST /api/v1/auth/login — CU-02. */
export interface LoginIn {
  correo: string;
  contrasena: string;
}

/** Usuario autenticado, tal como lo devuelven /auth/login y /auth/yo. */
export interface UsuarioAutenticado {
  id: number;
  correo: string;
  nombres: string;
  apellidos: string;
  rol: Rol;
  sucursal_id: number | null;
}

/** Respuesta 200 de POST /api/v1/auth/login. */
export interface TokenOut {
  access_token: string;
  token_type: string;
  expira_en: string;
  usuario: UsuarioAutenticado;
}

/** Los cuatro roles que carga el seed. */
export type Rol = 'ADMINISTRADOR' | 'CLIENTE' | 'ENCARGADO' | 'CAJERO';

/**
 * Ruta de inicio de cada rol, según el diagrama de navegación §3.2.
 * Es lo que decide a dónde cae alguien después de iniciar sesión.
 */
export const INICIO_POR_ROL: Record<Rol, string> = {
  ADMINISTRADOR: '/admin',
  CLIENTE: '/mi-cuenta',
  ENCARGADO: '/sucursal',
  CAJERO: '/caja',
};

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
