/**
 * 2do parcial · CU-06 — el slug de la empresa con el que se inicia sesión.
 *
 * Para entrar hay que indicar la empresa (RN-12). Pedirla de cero en cada
 * visita es molesto, así que se recuerda la última que funcionó. La primera
 * vez viene la de Violet Boutique, que es la empresa del 1er parcial.
 *
 * El administrador de la plataforma deja el campo vacío.
 */
const CLAVE = 'vb.empresa';
export const EMPRESA_INICIAL = 'violet-boutique';

export function empresaRecordada(): string {
  try {
    return localStorage.getItem(CLAVE) ?? EMPRESA_INICIAL;
  } catch {
    return EMPRESA_INICIAL;
  }
}

export function recordarEmpresa(slug: string): void {
  try {
    localStorage.setItem(CLAVE, slug);
  } catch {
    // Sin almacenamiento (modo privado): la próxima vez se vuelve a escribir.
  }
}

/** El slug como lo espera el backend; vacío viaja como `null` (plataforma). */
export function normalizarEmpresa(slug: string): string | null {
  const limpio = slug.trim().toLowerCase();
  return limpio === '' ? null : limpio;
}
