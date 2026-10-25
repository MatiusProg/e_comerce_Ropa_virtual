import { DOCUMENT } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';

import { environment } from '../../../environments/environment';
import { COLORES_VIOLET, MarcaTienda } from '../models/mi-tienda.models';

/** Las variables de styles.scss que la marca de la empresa reemplaza. */
const VARIABLES = [
  '--vb-malva',
  '--vb-malva-oscuro',
  '--vb-malva-claro',
  '--vb-oro',
  '--vb-degradado',
] as const;

/**
 * CU-12 · 1.11 — la tienda en línea aplica la marca de la empresa.
 *
 * Toda la interfaz pinta con las variables `--vb-*` de styles.scss. Con la
 * marca propia, se reemplazan en `:root` por los colores de la empresa: el
 * principal hace de malva (con un tono más oscuro y uno más claro sacados de
 * él) y el secundario de dorado. Sin marca, se quitan y vuelven los de Violet.
 *
 * Nunca falla: si la consulta no responde, la tienda sigue con Violet.
 */
@Injectable({ providedIn: 'root' })
export class MarcaService {
  private readonly http = inject(HttpClient);
  private readonly documento = inject(DOCUMENT);

  private readonly _marca = signal<MarcaTienda | null>(null);

  /** El logo de la empresa, o `null` para mostrar el nombre de Violet. */
  readonly logo = computed(() => this._marca()?.logo_url ?? null);
  readonly empresa = computed(() => this._marca()?.empresa ?? null);

  /** Pide la marca de la tienda que se mira y la aplica. */
  cargar(): void {
    this.http.get<MarcaTienda>(`${environment.apiUrl}/tienda/marca`).subscribe({
      next: (marca) => {
        this._marca.set(marca);
        this.aplicar(marca.color_principal, marca.color_secundario);
      },
      error: () => this.aplicar(null, null),
    });
  }

  /** Pone o quita los colores en `:root`. */
  private aplicar(principal: string | null, secundario: string | null): void {
    const estilo = this.documento.documentElement.style;
    // Primero se vuelve a Violet: así un color que se quitó no queda pegado.
    VARIABLES.forEach((v) => estilo.removeProperty(v));
    if (!principal && !secundario) {
      return;
    }
    if (principal) {
      estilo.setProperty('--vb-malva', principal);
      estilo.setProperty('--vb-malva-oscuro', mezclar(principal, '#000000', 0.25));
      estilo.setProperty('--vb-malva-claro', mezclar(principal, '#ffffff', 0.35));
    }
    if (secundario) {
      estilo.setProperty('--vb-oro', secundario);
    }
    const a = principal ?? COLORES_VIOLET.principal;
    const b = secundario ?? mezclar(a, '#ffffff', 0.45);
    estilo.setProperty('--vb-degradado', `linear-gradient(135deg, ${a} 0%, ${b} 100%)`);
  }
}

/** Mezcla dos colores `#rrggbb`: `peso` es cuánto del segundo entra. */
export function mezclar(color: string, con: string, peso: number): string {
  const canal = (hex: string, i: number) => parseInt(hex.slice(1 + i * 2, 3 + i * 2), 16);
  const partes = [0, 1, 2].map((i) =>
    Math.round(canal(color, i) * (1 - peso) + canal(con, i) * peso)
      .toString(16)
      .padStart(2, '0'),
  );
  return `#${partes.join('')}`;
}
