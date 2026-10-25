/**
 * P12 · Plataforma SaaS — CU-11 Contratar un plan desde la web (2do parcial).
 * Replica backend/app/modules/plataforma/contratacion/schemas.py.
 */

export interface FuncionPublica {
  clave: string;
  nombre: string;
  incluida: boolean;
}

/** Un plan que se ofrece. `null` en un límite es ilimitado. */
export interface PlanPublico {
  codigo: string;
  nombre: string;
  precio_mensual: number;
  duracion_dias: number;
  max_sucursales: number | null;
  max_empleados: number | null;
  cupo_reportes_ia: number | null;
  cupo_fotos_ia: number | null;
  bitacora_dias: number | null;
  funciones: FuncionPublica[];
}

export interface CiudadPublica {
  id: number;
  nombre: string;
  departamento: string;
}

export interface SlugVerificado {
  slug: string;
  disponible: boolean;
  /** 5a: otros libres, cuando el pedido está ocupado. */
  sugerencias: string[];
}

export interface Contratar {
  nombre: string;
  razon_social: string | null;
  nit: string | null;
  slug: string;
  correo_contacto: string | null;
  plan_codigo: string;
  sucursal: { ciudad_id: number; nombre: string; direccion: string };
  administrador: { correo: string; nombres: string; apellidos: string; contrasena: string };
  pago: { metodo: 'QR'; codigo_operacion: string };
}

export interface Contratacion {
  empresa: string;
  slug: string;
  plan: string;
  vencimiento: string;
  administrador_correo: string;
  correo_enviado: boolean;
  pago: { comprobante: string; metodo: string; monto: number; pagado_en: string };
}
