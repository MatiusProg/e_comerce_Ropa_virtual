import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';

/**
 * 3ra presentación · CU-36, CU-37 y CU-38 — el probador con la talla real.
 *
 * CU-36 (Administrador) prepara la prenda: puntos de la imagen y centímetros
 * por talla. CU-37 (Cliente) se la prueba sobre su foto a escala real. CU-38
 * pide la foto realista, que regula el plan (función `foto_ia` y su cupo).
 */

export interface Punto {
  x: number;
  y: number;
}

export interface PuntosDePrenda {
  hombro_izq: Punto;
  hombro_der: Punto;
  ruedo: Punto;
}

export interface MedidaDeTalla {
  talla_id: number;
  busto_cm: number | string;
  cintura_cm: number | string;
  cadera_cm: number | string;
  largo_cm: number | string;
}

export interface ImagenParaPreparar {
  imagen_id: number;
  url: string;
  variante_id: number;
  talla: string;
  color: string;
  puntos: PuntosDePrenda | null;
}

export interface TallaParaPreparar {
  talla_id: number;
  codigo: string;
  medidas: MedidaDeTalla | null;
}

export interface PrendaParaPreparar {
  producto_id: number;
  nombre: string;
  imagenes: ImagenParaPreparar[];
  tallas: TallaParaPreparar[];
  lista: boolean;
  faltan: string[];
}

export interface ProductoDelProbador {
  producto_id: number;
  nombre: string;
  activo: boolean;
  imagenes: number;
  imagenes_calibradas: number;
  tallas: number;
  tallas_medidas: number;
  lista: boolean;
}

export interface AjusteDeTalla {
  talla_id: number;
  codigo: string;
  busto_cm: string;
  cintura_cm: string;
  cadera_cm: string;
  largo_cm: string;
  ajuste: string;
  factor_ancho: number;
  factor_largo: number;
}

export interface PrendaDelProbador {
  variante_id: number;
  talla_id: number;
  talla: string;
  color_id: number;
  color: string;
  imagen_url: string;
  puntos: PuntosDePrenda;
}

export interface PruebaDeProducto {
  producto_id: number;
  nombre: string;
  prendas: PrendaDelProbador[];
  ajuste: {
    hay_medidas: boolean;
    hay_tabla: boolean;
    talla_recomendada: string | null;
    talla_recomendada_id: number | null;
    tallas: AjusteDeTalla[];
  };
  medidas: { busto_cm: string; altura_cm: string | null } | null;
  foto_ia: { disponible: boolean; motivo: string | null };
}

export interface SesionProbador {
  id: number;
  variante_id: number;
  producto_id: number;
  producto: string;
  talla: string;
  color: string;
  metodo: 'POSE' | 'MANUAL';
  ajuste: string | null;
  talla_recomendada: string | null;
  foto_url: string | null;
  foto_generada_por: string | null;
  creado_en: string;
}

export interface MedidasDelCliente {
  busto_cm: number;
  cintura_cm: number;
  cadera_cm: number;
  altura_cm: number | null;
}

/** El mensaje del servidor, o uno genérico; y si es un límite del plan. */
export interface ErrorProbador {
  mensaje: string;
  plan: boolean;
  estado: number;
}

/** Cómo le queda, en palabras. Las claves son las de `medidas.tallaje`. */
export const AJUSTE_EN_PALABRAS: Record<string, string> = {
  NO_ENTRA: 'Te quedaría muy chica',
  AJUSTADA: 'Te quedaría ajustada',
  A_TU_MEDIDA: 'A tu medida',
  HOLGADA: 'Te quedaría holgada',
  MUY_HOLGADA: 'Te quedaría muy grande',
};

@Injectable({ providedIn: 'root' })
export class ProbadorService {
  private readonly http = inject(HttpClient);
  private readonly admin = `${environment.apiUrl}/catalogo/probador`;
  private readonly vestidor = `${environment.apiUrl}/vestidor`;

  // --- CU-36 -----------------------------------------------------------------
  productos(): Observable<ProductoDelProbador[]> {
    return this.http.get<ProductoDelProbador[]>(`${this.admin}/productos`).pipe(catchError(traducir));
  }

  preparacion(productoId: number): Observable<PrendaParaPreparar> {
    return this.http
      .get<PrendaParaPreparar>(`${this.admin}/productos/${productoId}`)
      .pipe(catchError(traducir));
  }

  guardarPuntos(imagenId: number, puntos: PuntosDePrenda): Observable<PuntosDePrenda> {
    return this.http
      .put<PuntosDePrenda>(`${this.admin}/imagenes/${imagenId}/puntos`, puntos)
      .pipe(catchError(traducir));
  }

  guardarMedidas(productoId: number, tallas: MedidaDeTalla[]): Observable<PrendaParaPreparar> {
    return this.http
      .put<PrendaParaPreparar>(`${this.admin}/productos/${productoId}/medidas`, { tallas })
      .pipe(catchError(traducir));
  }

  // --- CU-37 -----------------------------------------------------------------
  prueba(productoId: number): Observable<PruebaDeProducto> {
    return this.http
      .get<PruebaDeProducto>(`${this.vestidor}/productos/${productoId}/prueba`)
      .pipe(catchError(traducir));
  }

  guardarMisMedidas(medidas: MedidasDelCliente): Observable<unknown> {
    return this.http
      .put(`${environment.apiUrl}/clientes/me/medidas`, medidas)
      .pipe(catchError(traducir));
  }

  registrar(varianteId: number, metodo: 'POSE' | 'MANUAL'): Observable<SesionProbador> {
    return this.http
      .post<SesionProbador>(`${this.vestidor}/sesiones`, { variante_id: varianteId, metodo })
      .pipe(catchError(traducir));
  }

  misPruebas(): Observable<SesionProbador[]> {
    return this.http.get<SesionProbador[]>(`${this.vestidor}/sesiones`).pipe(catchError(traducir));
  }

  borrar(sesionId: number): Observable<void> {
    return this.http
      .delete<void>(`${this.vestidor}/sesiones/${sesionId}`)
      .pipe(catchError(traducir));
  }

  // --- CU-38 -----------------------------------------------------------------
  generarFoto(sesionId: number, composicion: Blob): Observable<SesionProbador> {
    const datos = new FormData();
    datos.append('composicion', composicion, 'composicion.png');
    return this.http
      .post<SesionProbador>(`${this.vestidor}/sesiones/${sesionId}/foto`, datos)
      .pipe(catchError(traducir));
  }
}

function traducir(e: HttpErrorResponse): Observable<never> {
  const cuerpo = e.error as { detail?: unknown; codigo?: string } | null;
  let mensaje = 'No se pudo completar la operación. Intentá de nuevo.';
  if (e.status === 0) mensaje = 'No hay conexión con el servidor.';
  else if (typeof cuerpo?.detail === 'string') mensaje = cuerpo.detail;
  else if (Array.isArray(cuerpo?.detail) && e.status === 422)
    mensaje = 'Revisá los datos: hay un valor fuera de rango.';
  const error: ErrorProbador = { mensaje, plan: cuerpo?.codigo === 'plan_limit', estado: e.status };
  return throwError(() => error);
}
