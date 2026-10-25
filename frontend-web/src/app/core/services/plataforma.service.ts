import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import type {
  Empresa,
  EmpresaCreada,
  EmpresaCrear,
  EmpresaEditar,
  FuncionDePlan,
  Plan,
  PlanGuardado,
  PlanGuardar,
  PlanOferta,
} from '../models/plataforma.models';
import type { Ciudad } from '../models/organizacion.models';

/**
 * Errores previstos del CU-01. `slug-repetido` y `correo-repetido` se separan
 * porque el formulario marca el campo que corresponde (alternativo 4a).
 */
export type ErrorPlataforma =
  | { tipo: 'slug-repetido'; mensaje: string }
  | { tipo: 'correo-repetido'; mensaje: string }
  | { tipo: 'nombre-repetido'; mensaje: string }
  | { tipo: 'no-encontrado'; mensaje: string }
  | { tipo: 'validacion'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

/**
 * P12 · Plataforma SaaS — CU-01 Gestionar empresas y CU-02 Gestionar planes.
 * Solo ADMIN_PLATAFORMA.
 */
@Injectable({ providedIn: 'root' })
export class PlataformaService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/plataforma`;

  listarEmpresas(busqueda?: string): Observable<Empresa[]> {
    let params = new HttpParams();
    if (busqueda) params = params.set('busqueda', busqueda);
    return this.http
      .get<Empresa[]>(`${this.base}/empresas`, { params })
      .pipe(catchError((e) => this.traducir(e)));
  }

  planes(): Observable<PlanOferta[]> {
    return this.http.get<PlanOferta[]>(`${this.base}/planes`).pipe(catchError((e) => this.traducir(e)));
  }

  // --- CU-02 ------------------------------------------------------------

  /** Todos los planes, también los que ya no se ofrecen. */
  listarPlanes(): Observable<Plan[]> {
    const params = new HttpParams().set('incluir_inactivos', true);
    return this.http
      .get<Plan[]>(`${this.base}/planes`, { params })
      .pipe(catchError((e) => this.traducir(e)));
  }

  funcionesDePlan(): Observable<FuncionDePlan[]> {
    return this.http
      .get<FuncionDePlan[]>(`${this.base}/planes/funciones`)
      .pipe(catchError((e) => this.traducir(e)));
  }

  crearPlan(datos: PlanGuardar): Observable<PlanGuardado> {
    return this.http
      .post<PlanGuardado>(`${this.base}/planes`, datos)
      .pipe(catchError((e) => this.traducir(e)));
  }

  editarPlan(id: number, datos: PlanGuardar): Observable<PlanGuardado> {
    return this.http
      .put<PlanGuardado>(`${this.base}/planes/${id}`, datos)
      .pipe(catchError((e) => this.traducir(e)));
  }

  cambiarEstadoPlan(id: number, activo: boolean): Observable<Plan> {
    const accion = activo ? 'activar' : 'desactivar';
    return this.http
      .post<Plan>(`${this.base}/planes/${id}/${accion}`, {})
      .pipe(catchError((e) => this.traducir(e)));
  }

  /** Las ciudades son compartidas por todas las empresas. */
  ciudades(): Observable<Ciudad[]> {
    return this.http
      .get<Ciudad[]>(`${environment.apiUrl}/organizacion/ciudades`)
      .pipe(catchError((e) => this.traducir(e)));
  }

  crearEmpresa(datos: EmpresaCrear): Observable<EmpresaCreada> {
    return this.http
      .post<EmpresaCreada>(`${this.base}/empresas`, datos)
      .pipe(catchError((e) => this.traducir(e)));
  }

  editarEmpresa(id: number, datos: EmpresaEditar): Observable<Empresa> {
    return this.http
      .patch<Empresa>(`${this.base}/empresas/${id}`, datos)
      .pipe(catchError((e) => this.traducir(e)));
  }

  cambiarEstado(id: number, activa: boolean): Observable<Empresa> {
    const accion = activa ? 'reactivar' : 'baja';
    return this.http
      .post<Empresa>(`${this.base}/empresas/${id}/${accion}`, {})
      .pipe(catchError((e) => this.traducir(e)));
  }

  private traducir(e: HttpErrorResponse): Observable<never> {
    const detalle = typeof e.error?.detail === 'string' ? e.error.detail : null;
    let error: ErrorPlataforma;
    if (e.status === 409 && detalle?.includes('slug')) {
      error = { tipo: 'slug-repetido', mensaje: detalle };
    } else if (e.status === 409 && detalle?.includes('plan')) {
      error = { tipo: 'nombre-repetido', mensaje: detalle };
    } else if (e.status === 409) {
      error = { tipo: 'correo-repetido', mensaje: detalle ?? 'El correo ya tiene una cuenta.' };
    } else if (e.status === 404) {
      error = { tipo: 'no-encontrado', mensaje: detalle ?? 'La empresa no existe.' };
    } else if (e.status === 422 || e.status === 400) {
      error = { tipo: 'validacion', mensaje: detalle ?? 'Revise los datos del formulario.' };
    } else {
      error = { tipo: 'sistema', mensaje: 'No se pudo completar la operación. Intente de nuevo.' };
    }
    return throwError(() => error);
  }
}
