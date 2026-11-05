import { HttpClient, HttpResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';

import { environment } from '../../../environments/environment';

/** 3ra presentación · CU-40: una copia en el historial (RF-63). */
export interface Copia {
  id: number;
  tipo: 'MANUAL' | 'AUTOMATICA';
  archivo: string;
  tamano_bytes: number;
  sha256: string;
  filas: Record<string, number>;
  creado_en: string;
  creado_por: string | null;
  /** Solo las automáticas quedan guardadas (cifradas) en el servidor. */
  descargable: boolean;
}

export interface Restauracion {
  id: number;
  origen: 'ARCHIVO' | 'COPIA';
  archivo: string;
  sha256: string;
  datos_del: string;
  filas: Record<string, number>;
  creado_en: string;
  restaurado_por: string | null;
}

export interface HistorialDeCopias {
  plan: string | null;
  intervalo_manual_horas: number | null;
  retencion_automaticas: number;
  proxima_manual: string | null;
  copias: Copia[];
  restauraciones: Restauracion[];
}

export interface Restaurado {
  id: number;
  archivo: string;
  datos_del: string;
  filas: Record<string, number>;
}

export interface Descarga {
  archivo: Blob;
  nombre: string;
}

/**
 * CU-39 Exportar los datos de la empresa y CU-40 Gestionar copias de
 * seguridad. Las descargas van como `blob` y con la cabecera de sesión: un
 * enlace directo no la mandaría (ver `ReportesService.descargar`).
 */
@Injectable({ providedIn: 'root' })
export class DatosService {
  private readonly http = inject(HttpClient);
  private readonly api = environment.apiUrl;

  exportar(formato: 'xlsx' | 'zip'): Observable<Descarga> {
    return this.http
      .get(`${this.api}/exportacion/datos.${formato}`, { responseType: 'blob', observe: 'response' })
      .pipe(map((r) => this.descarga(r, `datos.${formato}`)));
  }

  historial(): Observable<HistorialDeCopias> {
    return this.http.get<HistorialDeCopias>(`${this.api}/respaldos`);
  }

  copiaManual(): Observable<Descarga> {
    return this.http
      .post(`${this.api}/respaldos/manual`, {}, { responseType: 'blob', observe: 'response' })
      .pipe(map((r) => this.descarga(r, 'respaldo.json')));
  }

  descargarCopia(id: number): Observable<Descarga> {
    return this.http
      .get(`${this.api}/respaldos/${id}/descarga`, { responseType: 'blob', observe: 'response' })
      .pipe(map((r) => this.descarga(r, 'respaldo.json')));
  }

  copiaAutomatica(): Observable<{ creada: boolean; motivo: string | null; borradas: number }> {
    return this.http.post<{ creada: boolean; motivo: string | null; borradas: number }>(
      `${this.api}/mantenimiento/respaldos`,
      {},
    );
  }

  restaurarArchivo(archivo: File): Observable<Restaurado> {
    const datos = new FormData();
    datos.append('archivo', archivo, archivo.name);
    return this.http.post<Restaurado>(`${this.api}/respaldos/restaurar`, datos);
  }

  restaurarCopia(id: number): Observable<Restaurado> {
    return this.http.post<Restaurado>(`${this.api}/respaldos/${id}/restaurar`, {});
  }

  private descarga(r: HttpResponse<Blob>, porOmision: string): Descarga {
    const cabecera = r.headers.get('content-disposition') ?? '';
    const nombre = /filename="([^"]+)"/.exec(cabecera)?.[1] ?? porOmision;
    return { archivo: r.body as Blob, nombre };
  }
}
