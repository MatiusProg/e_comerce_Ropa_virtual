import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import type {
  Aplicacion,
  Candidata,
  CrearMayorista,
  EditarMayorista,
  Mayorista,
  PaginaMayoristas,
  ReglaFueraDeTemporada,
} from '../models/ofertas.models';

/**
 * CU-31 (precios mayoristas) y CU-32 (fuera de temporada). Las ofertas
 * manuales siguen en `PromocionesService`.
 */
@Injectable({ providedIn: 'root' })
export class OfertasService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/ofertas`;

  listarMayoristas(busqueda = '', pagina = 1, tamano = 50): Observable<PaginaMayoristas> {
    let params = new HttpParams().set('pagina', pagina).set('tamano', tamano);
    if (busqueda.trim()) params = params.set('busqueda', busqueda.trim());
    return this.http.get<PaginaMayoristas>(`${this.base}/mayoristas`, { params });
  }

  crearMayorista(datos: CrearMayorista): Observable<Mayorista> {
    return this.http.post<Mayorista>(`${this.base}/mayoristas`, datos);
  }

  editarMayorista(id: number, datos: EditarMayorista): Observable<Mayorista> {
    return this.http.patch<Mayorista>(`${this.base}/mayoristas/${id}`, datos);
  }

  estadoMayorista(id: number, activo: boolean): Observable<Mayorista> {
    return this.http.patch<Mayorista>(`${this.base}/mayoristas/${id}/estado`, { activo });
  }

  regla(): Observable<ReglaFueraDeTemporada> {
    return this.http.get<ReglaFueraDeTemporada>(`${this.base}/fuera-de-temporada/regla`);
  }

  guardarRegla(datos: ReglaFueraDeTemporada): Observable<ReglaFueraDeTemporada> {
    const { por_omision: _omitida, ...cuerpo } = datos;
    return this.http.put<ReglaFueraDeTemporada>(`${this.base}/fuera-de-temporada/regla`, cuerpo);
  }

  candidatas(): Observable<Candidata[]> {
    return this.http.get<Candidata[]>(`${this.base}/fuera-de-temporada/candidatas`);
  }

  aplicar(): Observable<Aplicacion> {
    return this.http.post<Aplicacion>(`${this.base}/fuera-de-temporada/aplicar`, {});
  }
}
