/**
 * P12 · Plataforma SaaS — CU-01 Gestionar empresas (2do parcial).
 * Replica los esquemas de backend/app/modules/plataforma/schemas.py.
 */

export interface SuscripcionResumen {
  plan_codigo: string;
  plan_nombre: string;
  inicio: string;
  vencimiento: string;
  estado: 'VIGENTE' | 'SUSPENDIDA' | 'VENCIDA' | 'REEMPLAZADA';
}

export interface Empresa {
  id: number;
  nombre: string;
  razon_social: string | null;
  nit: string | null;
  slug: string;
  correo_contacto: string | null;
  estado: 'ACTIVA' | 'BAJA';
  creado_en: string;
  suscripcion: SuscripcionResumen | null;
  sucursales: number;
  usuarios: number;
}

export interface EmpresaCreada extends Empresa {
  administrador_correo: string;
  /** Se devuelve UNA vez, para el caso en que el correo no llegue. */
  contrasena_temporal: string;
  correo_enviado: boolean;
}

export interface EmpresaCrear {
  nombre: string;
  razon_social: string | null;
  nit: string | null;
  slug: string;
  correo_contacto: string | null;
  plan_codigo: string;
  sucursal: { ciudad_id: number; nombre: string; direccion: string };
  administrador: { correo: string; nombres: string; apellidos: string };
}

export interface EmpresaEditar {
  nombre?: string;
  razon_social?: string | null;
  nit?: string | null;
  correo_contacto?: string | null;
}

export interface PlanOferta {
  codigo: string;
  nombre: string;
  precio_mensual: number;
  duracion_dias: number;
}

/** La misma regla que el CHECK de la tabla `empresa` (RN-14). */
export const PATRON_SLUG = /^[a-z0-9]+(-[a-z0-9]+)*$/;
