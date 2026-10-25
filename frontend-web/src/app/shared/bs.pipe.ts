import { Pipe, PipeTransform } from '@angular/core';

/**
 * Un monto en bolivianos, siempre igual en toda la web: «Bs 1.500,00».
 *
 * Coma para los decimales y punto para los miles, como se escribe en Bolivia.
 * Antes convivían «Bs 400.00» (la tienda pegaba el texto de la API),
 * «Bs400,00» (el `currency` de Angular) y «Bs 1.500» (Mi plan).
 *
 * No usa `formatNumber` del locale: el CLDR del español no agrupa los números
 * de cuatro cifras («1500»), y Angular e `Intl` no coinciden en eso.
 */
export function formatoBs(valor: number | string | null | undefined): string {
  if (valor === null || valor === undefined || valor === '') return '';
  const numero = Number(valor);
  if (!Number.isFinite(numero)) return '';
  const [enteros, decimales] = Math.abs(numero).toFixed(2).split('.');
  const conMiles = enteros.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return `${numero < 0 ? '−' : ''}Bs ${conMiles},${decimales}`;
}

@Pipe({ name: 'bs' })
export class BsPipe implements PipeTransform {
  transform(valor: number | string | null | undefined): string {
    return formatoBs(valor);
  }
}
