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

/** CU-02 · un plan con todo lo que define. `null` en un límite es ilimitado. */
export interface Plan extends PlanOferta {
  id: number;
  max_sucursales: number | null;
  max_empleados: number | null;
  cupo_reportes_ia: number | null;
  cupo_fotos_ia: number | null;
  /** Días de bitácora que ve la empresa; `null` es todo el historial. */
  bitacora_dias: number | null;
  funciones: string[];
  activo: boolean;
  /** Empresas con una suscripción vigente o suspendida en este plan. */
  empresas: number;
}

export interface PlanGuardar {
  nombre: string;
  precio_mensual: number;
  duracion_dias: number;
  max_sucursales: number | null;
  max_empleados: number | null;
  cupo_reportes_ia: number | null;
  cupo_fotos_ia: number | null;
  bitacora_dias: number | null;
  funciones: string[];
}

/** Alternativo 5a: una empresa que ya pasa un límite del plan. No se le borra nada. */
export interface EmpresaExcedida {
  empresa: string;
  recurso: string;
  uso: number;
  limite: number;
}

export interface PlanGuardado extends Plan {
  excedidas: EmpresaExcedida[];
}

export interface FuncionDePlan {
  clave: string;
  nombre: string;
}

/** La misma regla que el CHECK de la tabla `empresa` (RN-14). */
export const PATRON_SLUG = /^[a-z0-9]+(-[a-z0-9]+)*$/;

// --- CU-03 Gestionar suscripciones ------------------------------------------

export type EstadoSuscripcion = SuscripcionResumen['estado'];

export interface Suscripcion {
  id: number;
  plan_id: number;
  plan_codigo: string;
  plan_nombre: string;
  inicio: string;
  vencimiento: string;
  /** Una VIGENTE con la fecha pasada llega como VENCIDA. */
  estado: EstadoSuscripcion;
  dias_restantes: number;
}

export interface PagoSimulado {
  id: number;
  suscripcion_id: number;
  concepto: 'ALTA' | 'CAMBIO' | 'RENOVACION';
  plan_nombre: string;
  monto: number;
  comprobante: string;
  pagado_en: string;
}

/** Paso 2: la actual (o la última, si no hay) y el historial. */
export interface SuscripcionesEmpresa {
  empresa_id: number;
  empresa: string;
  actual: Suscripcion | null;
  historial: Suscripcion[];
  pagos: PagoSimulado[];
}

export interface SuscripcionGuardada extends SuscripcionesEmpresa {
  pago: PagoSimulado | null;
  /** 5a: lo que ya pasa los límites del plan nuevo. No se borra nada. */
  excedidas: EmpresaExcedida[];
}

export interface AsignarPlan {
  plan_id: number;
  /** `YYYY-MM-DD`; sin indicar, hoy. */
  inicio: string | null;
}

export interface Vencimiento {
  vencidas: number;
  empresas: string[];
}
