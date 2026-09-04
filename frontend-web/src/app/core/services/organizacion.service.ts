import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { SucursalBreve } from '../models/organizacion.models';

/**
 * P2 · Organización.
 *
 * Hoy solo expone el listado de sucursales activas, que es lo que CU-03
 * necesita para el selector. El CRUD completo llega con CU-05.
 */
@Injectable({ providedIn: 'root' })
export class OrganizacionService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/organizacion`;

  sucursales(): Observable<SucursalBreve[]> {
    return this.http.get<SucursalBreve[]>(`${this.base}/sucursales`);
  }
}
