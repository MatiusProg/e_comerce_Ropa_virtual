import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import type {
  AccionTraspaso,
  FiltrosTraspasos,
  OrigenPosible,
  PaginaTraspasos,
  PrendaPedible,
  SolicitarTraspaso,
  Sugerencias,
  Traspaso,
} from '../models/traspasos.models';

/**
 * CU-33 Solicitar traspaso, CU-34 Atender traspaso y CU-35 Consultar
 * traspasos sugeridos. El alcance (qué sucursal) lo decide el servidor con el
 * token: el encargado ve y opera solo lo de la suya.
 */
@Injectable({ providedIn: 'root' })
export class TraspasosService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/traspasos`;

  listar(filtros: FiltrosTraspasos = {}): Observable<PaginaTraspasos> {
    let params = new HttpParams();
    for (const [clave, valor] of Object.entries(filtros)) {
      if (valor !== null && valor !== undefined && valor !== '') {
        params = params.set(clave, String(valor));
      }
    }
    return this.http.get<PaginaTraspasos>(this.base, { params });
  }

  prendas(busqueda: string): Observable<PrendaPedible[]> {
    const params = busqueda.trim() ? new HttpParams().set('busqueda', busqueda.trim()) : undefined;
    return this.http.get<PrendaPedible[]>(`${this.base}/prendas`, { params });
  }

  origenes(varianteId: number): Observable<OrigenPosible[]> {
    return this.http.get<OrigenPosible[]>(`${this.base}/origenes`, {
      params: new HttpParams().set('variante_id', varianteId),
    });
  }

  solicitar(datos: SolicitarTraspaso): Observable<Traspaso> {
    return this.http.post<Traspaso>(this.base, datos);
  }

  /** `cuerpo` solo lo usan aprobar (cantidad) y rechazar (motivo). */
  atender(id: number, accion: AccionTraspaso, cuerpo: object = {}): Observable<Traspaso> {
    return this.http.post<Traspaso>(`${this.base}/${id}/${accion.toLowerCase()}`, cuerpo);
  }

  sugeridos(dias: number): Observable<Sugerencias> {
    return this.http.get<Sugerencias>(`${this.base}/sugeridos`, {
      params: new HttpParams().set('dias', dias),
    });
  }
}
