/**
 * El contenido del código QR de cobro, en formato EMVCo.
 *
 * QUÉ ES Y POR QUÉ ESTE FORMATO
 * -----------------------------
 * EMVCo «Merchant-Presented Mode» es el estándar internacional de los QR de
 * pago en comercios: el comercio muestra el código y el cliente lo escanea con
 * la aplicación de su banco. El contenido no es una URL sino una cadena de
 * campos etiquetados —id de dos dígitos, largo de dos dígitos, valor— que
 * cierra con un CRC para que la aplicación descarte un código mal leído.
 *
 * Acá se arma igual que uno real, con el monto, la moneda (068 = boliviano,
 * ISO 4217) y una referencia única por cobro. Lo único simulado es el otro
 * extremo: no hay ningún banco que lo reciba. La confirmación la da la
 * pantalla de cobro (`cobro-qr.ts`), que hace de banco en la demostración.
 *
 * Es una función pura a propósito: el CRC y el armado se prueban sin
 * pantalla, en `qr-emv.spec.ts`.
 */

export interface DatosCobroQr {
  /** El importe exacto, con dos decimales: «250.00». */
  monto: string;
  /** Única por cobro. Es lo que el banco devolvería al confirmar. */
  referencia: string;
  /** La sucursal, que EMVCo pone en el campo de ciudad del comercio. */
  sucursal: string;
  /** La caja que cobra, como etiqueta de terminal. */
  caja: string;
}

/** Identificador del esquema de pago. Dice «simulado» a propósito. */
const GUI_SIMULADO = 'BO.VIOLETBOUTIQUE.SIMULADO';

/** Código de rubro (MCC) de las tiendas de ropa. */
const MCC_ROPA = '5651';

/** Boliviano, ISO 4217 numérico. */
const MONEDA_BOB = '068';

/** Un campo EMVCo: id, largo en dos dígitos y el valor. */
function campo(id: string, valor: string): string {
  if (valor.length > 99) throw new Error(`El campo ${id} excede los 99 caracteres`);
  return id + valor.length.toString().padStart(2, '0') + valor;
}

/**
 * Deja un texto en ASCII y dentro del largo que admite el campo. Las
 * aplicaciones bancarias no garantizan leer acentos en los campos de nombre.
 */
function ascii(texto: string, largo: number): string {
  return texto
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^\x20-\x7E]/g, '')
    .toUpperCase()
    .slice(0, largo)
    .trim();
}

/**
 * CRC-16/CCITT-FALSE (polinomio 0x1021, valor inicial 0xFFFF), el que exige
 * EMVCo en el campo 63. Se calcula sobre toda la cadena INCLUIDO «6304», el
 * id y el largo del propio campo del CRC.
 */
export function crc16(texto: string): string {
  let crc = 0xffff;
  for (let i = 0; i < texto.length; i++) {
    crc ^= texto.charCodeAt(i) << 8;
    for (let b = 0; b < 8; b++) {
      crc = crc & 0x8000 ? ((crc << 1) ^ 0x1021) & 0xffff : (crc << 1) & 0xffff;
    }
  }
  return crc.toString(16).toUpperCase().padStart(4, '0');
}

/** Arma la cadena completa que va dentro del código QR. */
export function contenidoQr(d: DatosCobroQr): string {
  const cuerpo =
    campo('00', '01') + // versión del formato
    campo('01', '12') + // 12 = dinámico: vale para UN cobro, con monto fijo
    campo('26', campo('00', GUI_SIMULADO)) +
    campo('52', MCC_ROPA) +
    campo('53', MONEDA_BOB) +
    campo('54', d.monto) +
    campo('58', 'BO') +
    campo('59', 'VIOLET BOUTIQUE') +
    campo('60', ascii(d.sucursal, 15) || 'BOLIVIA') +
    campo('62', campo('05', ascii(d.referencia, 25)) + campo('07', ascii(d.caja, 25) || 'CAJA'));
  const conCabeceraCrc = cuerpo + '6304';
  return conCabeceraCrc + crc16(conCabeceraCrc);
}

/**
 * Una referencia nueva por cobro: «QR-» y ocho caracteres al azar.
 *
 * Sale de `crypto.getRandomValues` y no de `Math.random`: dos cajas cobrando
 * al mismo tiempo no pueden terminar con la misma referencia.
 */
export function nuevaReferencia(): string {
  const alfabeto = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // sin 0/O ni 1/I
  const bytes = crypto.getRandomValues(new Uint8Array(8));
  return 'QR-' + Array.from(bytes, (b) => alfabeto[b % alfabeto.length]).join('');
}
