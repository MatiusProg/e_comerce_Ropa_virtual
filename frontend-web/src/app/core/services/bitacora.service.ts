import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';

/**
 * CU-42 · Consultar la bitácora del sistema.
 *
 * Espejo de `backend/app/modules/bitacora/schemas.py`.
 *
 * **Solo lectura.** No hay `crear`, `editar` ni `borrar` porque el servidor
 * tampoco los expone: los asientos los pone un middleware y una bitácora que
 * se puede corregir no prueba nada.
 */

export interface AsientoBitacora {
  id: number;

  /**
   * Ya viene **en hora boliviana**, convertida por el servidor.
   *
   * Por eso acá se formatea sin volver a convertir: hacerlo en el navegador
   * la pasaría a la zona del aparato, y un equipo con la hora mal puesta
   * mostraría una bitácora distinta a la de la máquina de al lado — sobre un
   * registro cuyo único valor es que todos vean lo mismo.
   */
  ocurrido_en: string;

  usuario_id: number | null;
  /** El correo tal como estaba cuando pasó. */
  actor: string | null;
  /** El nombre completo, si la cuenta todavía existe. */
  nombre: string | null;
  rol: string | null;

  accion: string;
  entidad: string | null;
  entidad_id: string | null;

  metodo: string;
  ruta: string;
  estado_http: number;
  exito: boolean;

  ip: string | null;
  agente: string | null;
  detalle: Record<string, unknown> | null;
}

export interface PaginaBitacora {
  total: number;
  pagina: number;
  tamano: number;
  items: AsientoBitacora[];
}

export interface OpcionesBitacora {
  acciones: string[];
  entidades: string[];
  roles: string[];
}

export interface ConsultaBitacora {
  desde?: string | null;
  hasta?: string | null;
  usuario_id?: number | null;

  /**
   * Un rol, o `EMPLEADOS` para los tres internos a la vez.
   *
   * «Qué hicieron los empleados» es la pregunta que se hace de verdad, y
   * obligar a mirarlos de a un rol por vez la convierte en tres consultas.
   */
  rol?: string | null;

  accion?: string | null;
  entidad?: string | null;
  exito?: boolean | null;
  busqueda?: string | null;
  pagina?: number;
  tamano?: number;
}

@Injectable({ providedIn: 'root' })
export class BitacoraService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/bitacora`;

  consultar(consulta: ConsultaBitacora): Observable<PaginaBitacora> {
    let params = new HttpParams();
    for (const [clave, valor] of Object.entries(consulta)) {
      if (valor !== null && valor !== undefined && valor !== '') {
        params = params.set(clave, String(valor));
      }
    }
    return this.http.get<PaginaBitacora>(this.base, { params });
  }

  /**
   * Las acciones y entidades que hay registradas de verdad.
   *
   * Se piden al servidor en vez de escribirlas acá: la bitácora crece con
   * las rutas que existen, y una lista fija ofrecería filtros que no dan
   * ningún resultado y escondería los que sí.
   */
  opciones(): Observable<OpcionesBitacora> {
    return this.http.get<OpcionesBitacora>(`${this.base}/opciones`);
  }
}
