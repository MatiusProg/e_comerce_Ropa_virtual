/**
 * CU-29 y CU-30 · Analítica con ML — el contrato de `/analitica`.
 *
 * Replica `backend/app/modules/analitica/schemas.py`. Las métricas y los
 * parámetros llegan como diccionarios: cada modelo tiene las suyas.
 */

export interface MetricasDemanda {
  mae: number;
  rmse: number;
  r2: number;
  mae_linea_base: number;
  mejora_sobre_base_pct: number;
  filas_entrenamiento: number;
  filas_prueba: number;
  semanas_de_prueba: number;
}

export interface SiluetaK {
  k: number;
  silueta: number;
  inercia: number;
}

export interface MetricasSegmentos {
  k: number;
  silueta: number;
  inercia: number;
  siluetas: SiluetaK[];
}

export interface Entrenamiento<M> {
  id: number;
  entrenado_en: string;
  parametros: Record<string, unknown>;
  metricas: M;
  filas_entrenamiento: number;
  filas_reales: number;
  filas_sinteticas: number;
  duracion_ms: number;
}

export interface Prediccion {
  producto_id: number | null;
  producto: string;
  categoria: string;
  prevista: number;
  ultima_semana: number;
  media_4_semanas: number;
  reales_ultimas_4: number;
  tendencia: 'SUBE' | 'BAJA' | 'ESTABLE';
}

export interface ResultadoDemanda {
  semana_prevista: string;
  predicciones: Prediccion[];
  serie_validacion: { semana: string; real: number; prevista: number }[];
  historia: { semana: string; unidades: number }[];
  importancia: { variable: string; peso: number }[];
  total_previsto: number;
}

export interface Segmento {
  grupo: number;
  nombre: string;
  accion: string;
  clientes: number;
  clientes_reales: number;
  recencia_dias: number;
  compras: number;
  monto: number;
}

export interface ResumenAnalitica {
  entrenado: boolean;
  demanda: Entrenamiento<MetricasDemanda> | null;
  segmentos: Entrenamiento<MetricasSegmentos> | null;
  predicciones: ResultadoDemanda | null;
  grupos: Segmento[];
}

export interface ClienteSegmento {
  cliente_id: number;
  cliente: string;
  segmento: string;
  recencia_dias: number;
  compras: number;
  monto: number;
}

// --- Aporte propio · Anomalías en caja y devoluciones (Isolation Forest) ---

export interface RevisionAnomalia {
  por: string;
  en: string;
}

export interface Anomalia {
  id: number;
  fecha: string;
  cajero: string;
  sucursal: string;
  detalle: string;
  /** De 0 a 1: cuanto más cerca de 1, más rara. */
  puntaje: number;
  /** Qué se aparta de lo habitual; sale de los datos, no de un modelo de lenguaje. */
  explicacion: string;
  revision: RevisionAnomalia | null;
}

export interface GrupoAnomalias {
  suficientes: boolean;
  muestras: number;
  mensaje: string | null;
  medianas: Record<string, number>;
  marcadas: Anomalia[];
}

export interface MetricasAnomalias {
  contaminacion: number;
  muestras_turnos: number;
  marcados_turnos: number;
  pct_marcados_turnos: number;
  muestras_devoluciones: number;
  marcadas_devoluciones: number;
  pct_marcadas_devoluciones: number;
}

export interface ResultadoAnomalias {
  entrenado: boolean;
  entrenamiento: Entrenamiento<MetricasAnomalias> | null;
  turnos: GrupoAnomalias | null;
  devoluciones: GrupoAnomalias | null;
}

export type GrupoAnomalia = 'turnos' | 'devoluciones';
