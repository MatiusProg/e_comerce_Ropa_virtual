/**
 * CU-04 · Consultar plan y consumo — el contrato de `GET /plataforma/mi-plan`.
 *
 * Replica `backend/app/modules/plataforma/mi_plan/schemas.py`.
 */

export interface FuncionPlan {
  codigo: string;
  etiqueta: string;
  incluida: boolean;
  /** Para las que no son sí o no: «180 días», «Una por día». */
  detalle: string | null;
}

/** Un límite o cupo. `limite` null es ilimitado; `usado` null, que aún no se mide. */
export interface LimitePlan {
  codigo: string;
  etiqueta: string;
  usado: number | null;
  limite: number | null;
  alcanzado: boolean;
}

export interface Plan {
  id: number;
  codigo: string;
  nombre: string;
  precio_mensual: string;
  duracion_dias: number;
  max_sucursales: number | null;
  max_empleados: number | null;
  cupo_reportes_ia: number | null;
  cupo_fotos_ia: number | null;
  funciones: FuncionPlan[];
}

export type EstadoSuscripcion = 'VIGENTE' | 'SUSPENDIDA' | 'VENCIDA' | 'REEMPLAZADA';

export interface SuscripcionPlan {
  estado: EstadoSuscripcion;
  inicio: string;
  vencimiento: string;
  dias_restantes: number;
  solo_consulta: boolean;
}

export interface MiPlan {
  empresa: string;
  slug: string;
  suscripcion: SuscripcionPlan | null;
  plan: Plan | null;
  limites: LimitePlan[];
  cupos: LimitePlan[];
  otros_planes: Plan[];
}
