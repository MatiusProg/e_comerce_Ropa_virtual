/**
 * CU-13 y CU-17 · El almacenamiento del navegador, en IndexedDB.
 *
 * POR QUÉ INDEXEDDB Y NO `localStorage`
 * -------------------------------------
 * `localStorage` es síncrono, guarda solo texto y tiene unos 5 MB: un catálogo
 * con sus precios más una semana de ventas sin red no entra, y cada escritura
 * frena la pantalla. IndexedDB es asíncrono, guarda objetos y sobrevive a
 * cerrar el navegador (RF-17), que es lo que pide el enunciado.
 *
 * Sin librería a propósito: son dos almacenes y cuatro operaciones. Dexie
 * traería más de lo que usamos.
 */

const NOMBRE = 'violet-offline';
const VERSION = 1;

/** El paquete de CU-13, una sola fila por clave (`mostrador`). */
export const PAQUETES = 'paquetes';
/** La cola de operaciones de CU-17, una fila por UUID. */
export const OPERACIONES = 'operaciones';

let abierta: Promise<IDBDatabase> | null = null;

function abrir(): Promise<IDBDatabase> {
  if (abierta) return abierta;
  abierta = new Promise((resolver, fallar) => {
    const pedido = indexedDB.open(NOMBRE, VERSION);
    pedido.onupgradeneeded = () => {
      const db = pedido.result;
      if (!db.objectStoreNames.contains(PAQUETES)) db.createObjectStore(PAQUETES);
      if (!db.objectStoreNames.contains(OPERACIONES)) {
        db.createObjectStore(OPERACIONES, { keyPath: 'uuid' });
      }
    };
    pedido.onsuccess = () => resolver(pedido.result);
    pedido.onerror = () => {
      abierta = null;
      fallar(pedido.error);
    };
  });
  return abierta;
}

function esperar<T>(pedido: IDBRequest<T>): Promise<T> {
  return new Promise((resolver, fallar) => {
    pedido.onsuccess = () => resolver(pedido.result);
    pedido.onerror = () => fallar(pedido.error);
  });
}

export async function leer<T>(almacen: string, clave: IDBValidKey): Promise<T | undefined> {
  const db = await abrir();
  return esperar(db.transaction(almacen).objectStore(almacen).get(clave)) as Promise<T | undefined>;
}

export async function todos<T>(almacen: string): Promise<T[]> {
  const db = await abrir();
  return esperar(db.transaction(almacen).objectStore(almacen).getAll()) as Promise<T[]>;
}

/**
 * Escribe y espera a que la transacción termine (`oncomplete`), no solo a que
 * el pedido salga bien: recién ahí el dato está en disco. Una venta que el
 * cajero ya cobró no puede perderse porque se cerró la pestaña un instante
 * después.
 */
export async function guardar(almacen: string, valor: unknown, clave?: IDBValidKey): Promise<void> {
  const db = await abrir();
  const tx = db.transaction(almacen, 'readwrite');
  tx.objectStore(almacen).put(valor, clave);
  await new Promise<void>((resolver, fallar) => {
    tx.oncomplete = () => resolver();
    tx.onerror = () => fallar(tx.error);
    tx.onabort = () => fallar(tx.error);
  });
}

export async function borrar(almacen: string, clave: IDBValidKey): Promise<void> {
  const db = await abrir();
  const tx = db.transaction(almacen, 'readwrite');
  tx.objectStore(almacen).delete(clave);
  await new Promise<void>((resolver, fallar) => {
    tx.oncomplete = () => resolver();
    tx.onerror = () => fallar(tx.error);
  });
}
