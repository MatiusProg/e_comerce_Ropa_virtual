import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import {
  Alcance,
  CrearPromocion,
  EditarPromocion,
  PaginaPromociones,
  Promocion,
} from '../models/promociones.models';

export type ErrorPromociones =
  | { tipo: 'nombre-repetido'; mensaje: string }
  | { tipo: 'objetivo-inexistente'; mensaje: string }
  | { tipo: 'no-existe'; mensaje: string }
  | { tipo: 'rechazado'; mensaje: string }
  | { tipo: 'sin-permiso'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

@Injectable({ providedIn: 'root' })
export class PromocionesService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/catalogo/promociones`;

  listar(
    pagina = 1,
    tamano = 20,
    alcance?: Alcance | null,
    soloVigentes = false,
  ): Observable<PaginaPromociones> {
    let params = new HttpParams().set('pagina', pagina).set('tamano', tamano);
    if (alcance) params = params.set('alcance', alcance);
    if (soloVigentes) params = params.set('solo_vigentes', true);
    return this.http
      .get<PaginaPromociones>(this.base, { params })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  crear(datos: CrearPromocion): Observable<Promocion> {
    return this.http
      .post<Promocion>(this.base, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  editar(id: number, datos: EditarPromocion): Observable<Promocion> {
    return this.http
      .patch<Promocion>(`${this.base}/${id}`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /**
   * Enciende o apaga.
   *
   * No hay borrado: las ventas ya cobradas con la promoción la explican en su
   * historial, y volver a encenderla la temporada que viene es lo normal.
   */
  cambiarEstado(id: number, activa: boolean): Observable<Promocion> {
    return this.http
      .patch<Promocion>(`${this.base}/${id}/estado`, { activa })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  private traducir(error: HttpErrorResponse): ErrorPromociones {
    const detalle: unknown = error.error?.detail;
    const texto = typeof detalle === 'string' ? detalle : '';

    if (error.status === 409) {
      return { tipo: 'nombre-repetido', mensaje: texto || 'Ese nombre ya está usado.' };
    }
    if (error.status === 404) {
      // El servidor manda 404 tanto cuando la promoción no existe como cuando
      // el objetivo elegido no existe. Se separan por lo que la pantalla hace:
      // lo primero recarga la lista, lo segundo marca el campo.
      if (texto.toLowerCase().includes('promoción')) {
        return { tipo: 'no-existe', mensaje: texto };
      }
      return {
        tipo: 'objetivo-inexistente',
        mensaje: texto || 'Lo que eligió ya no existe.',
      };
    }
    if (error.status === 403) {
      return {
        tipo: 'sin-permiso',
        mensaje: texto || 'Las promociones son del Administrador.',
      };
    }
    if (error.status === 422) {
      return { tipo: 'rechazado', mensaje: texto || 'Revise los datos de la promoción.' };
    }
    if (error.status === 0) {
      return {
        tipo: 'sistema',
        mensaje: 'No se pudo contactar al servidor. Verifique su conexión.',
      };
    }
    return { tipo: 'sistema', mensaje: texto || 'No se pudo guardar la promoción.' };
  }
}
