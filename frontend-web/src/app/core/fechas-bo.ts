import { Injectable, Provider } from '@angular/core';
import { DateAdapter, MAT_DATE_FORMATS, MatDateFormats, NativeDateAdapter } from '@angular/material/core';

/**
 * El datepicker en formato boliviano: dd/mm/aaaa, al mostrar Y al leer.
 *
 * El `NativeDateAdapter` muestra con `Intl` (en es-BO da «8/10/2026», sin
 * ceros, que se confunde con el formato de EE. UU.) y LEE con `Date.parse`,
 * que interpreta «08/10/2026» como 10 de agosto. Quien tipeaba la fecha a
 * mano en Reportes pedía otro período sin enterarse.
 */
@Injectable()
export class AdaptadorFechasBo extends NativeDateAdapter {
  override format(fecha: Date, formato: object): string {
    if (formato === FORMATOS_FECHA_BO.display.dateInput) {
      const dia = `${fecha.getDate()}`.padStart(2, '0');
      const mes = `${fecha.getMonth() + 1}`.padStart(2, '0');
      return `${dia}/${mes}/${fecha.getFullYear()}`;
    }
    return super.format(fecha, formato);
  }

  override parse(valor: unknown, formato?: unknown): Date | null {
    if (typeof valor === 'string') {
      const m = /^\s*(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\s*$/.exec(valor);
      if (m) {
        const [dia, mes, anio] = [Number(m[1]), Number(m[2]), Number(m[3])];
        const fecha = new Date(anio, mes - 1, dia);
        // 31/02 no es una fecha: `Date` la corre al 3 de marzo sin avisar.
        const valida = fecha.getDate() === dia && fecha.getMonth() === mes - 1;
        return valida ? fecha : this.invalid();
      }
    }
    return super.parse(valor, formato);
  }
}

export const FORMATOS_FECHA_BO: MatDateFormats = {
  parse: { dateInput: null },
  display: {
    dateInput: { year: 'numeric', month: '2-digit', day: '2-digit' },
    monthLabel: { month: 'short' },
    monthYearLabel: { year: 'numeric', month: 'short' },
    dateA11yLabel: { year: 'numeric', month: 'long', day: 'numeric' },
    monthYearA11yLabel: { year: 'numeric', month: 'long' },
  },
};

export function proveerFechasBo(): Provider[] {
  return [
    { provide: DateAdapter, useClass: AdaptadorFechasBo },
    { provide: MAT_DATE_FORMATS, useValue: FORMATOS_FECHA_BO },
  ];
}
