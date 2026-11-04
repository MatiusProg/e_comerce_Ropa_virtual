import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import type {
  GuardarRol,
  PermisoDelCatalogo,
  Persona,
  RolEmpresa,
} from '../models/roles.models';

/** CU-41 · Roles y permisos propios de la empresa (RF-64, RN-22). */
@Injectable({ providedIn: 'root' })
export class RolesService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/roles`;

  permisos(): Observable<PermisoDelCatalogo[]> {
    return this.http.get<PermisoDelCatalogo[]>(`${this.base}/permisos`);
  }

  listar(): Observable<RolEmpresa[]> {
    return this.http.get<RolEmpresa[]>(this.base);
  }

  crear(datos: GuardarRol): Observable<RolEmpresa> {
    return this.http.post<RolEmpresa>(this.base, datos);
  }

  /** El rol base no se cambia: no viaja. */
  editar(id: number, datos: Omit<GuardarRol, 'rol_base'>): Observable<RolEmpresa> {
    return this.http.patch<RolEmpresa>(`${this.base}/${id}`, datos);
  }

  estado(id: number, activo: boolean): Observable<RolEmpresa> {
    return this.http.patch<RolEmpresa>(`${this.base}/${id}/estado`, { activo });
  }

  personal(): Observable<Persona[]> {
    return this.http.get<Persona[]>(`${this.base}/personal`);
  }

  asignar(usuarioId: number, rolId: number | null): Observable<Persona> {
    return this.http.put<Persona>(`${this.base}/asignacion`, {
      usuario_id: usuarioId,
      rol_empresa_id: rolId,
    });
  }
}
