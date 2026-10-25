/**
 * CU-12 · Personalizar la tienda de la empresa — los contratos.
 *
 * Replica `backend/app/modules/plataforma/mi_tienda/schemas.py`.
 */

/** Lo que ve el administrador en «Mi tienda». */
export interface MarcaEmpresa {
  empresa: string;
  slug: string;
  /** Ruta `/media/...`; `null` es el logo de Violet. */
  logo_url: string | null;
  /** `#rrggbb`; `null` es el color de Violet. */
  color_principal: string | null;
  color_secundario: string | null;
  /** 1a: si el plan incluye la marca propia. */
  incluida: boolean;
}

export interface ColoresMarca {
  color_principal: string | null;
  color_secundario: string | null;
}

/** La marca que aplica la tienda en línea (pública). Todo `null`: la de Violet. */
export interface MarcaTienda {
  empresa: string | null;
  logo_url: string | null;
  color_principal: string | null;
  color_secundario: string | null;
}

/** Los colores de Violet, los mismos que `--vb-malva` y `--vb-oro` de styles.scss. */
export const COLORES_VIOLET: Readonly<{ principal: string; secundario: string }> = {
  principal: '#8e4a67',
  secundario: '#c9a227',
};
