import type { AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms';

/**
 * Validadores que alinean el formulario con lo que exige el backend.
 *
 * `Validators.minLength` cuenta los espacios: «     » pasaba en el front y el
 * servidor lo rechazaba (él recorta antes de medir). Este recorta primero.
 */
export function minimoSinEspacios(minimo: number): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    const texto = typeof control.value === 'string' ? control.value.trim() : '';
    if (texto.length === 0) return { required: true };
    return texto.length < minimo ? { minlength: { requiredLength: minimo, actualLength: texto.length } } : null;
  };
}

/** Solo enteros: un `type="number"` acepta 1.5 y el backend pide horas enteras. */
export const entero: ValidatorFn = (control: AbstractControl): ValidationErrors | null => {
  const v = control.value;
  if (v === null || v === undefined || v === '') return null;
  return Number.isInteger(Number(v)) ? null : { entero: true };
};
