import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { CiudadBreve, SucursalBreve } from '../models/organizacion.models';

/**
 * P2 · Organización.
 *
 * Hoy solo expone lecturas: las sucursales activas que CU-03 necesita para su
 * selector y las ciudades que CU-04 necesita para el suyo. El CRUD completo
 * llega con CU-05 — ver §6.11.2 de `docs/06-decisiones-tecnicas.md`.
 */
@Injectable({ providedIn: 'root' })
export class OrganizacionService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/organizacion`;

  sucursales(): Observable<SucursalBreve[]> {
    return this.http.get<SucursalBreve[]>(`${this.base}/sucursales`);
  }

  ciudades(): Observable<CiudadBreve[]> {
    return this.http.get<CiudadBreve[]>(`${this.base}/ciudades`);
  }
}
