import { MatPaginatorIntl } from '@angular/material/paginator';

/**
 * Textos del paginador en español.
 *
 * Angular Material trae sus etiquetas en inglés y no las traduce solo. Sin
 * esto, una aplicación íntegramente en español muestra "Items per page" y
 * "1 – 10 of 37" en cada tabla.
 */
export function paginadorEnEspanol(): MatPaginatorIntl {
  const intl = new MatPaginatorIntl();

  intl.itemsPerPageLabel = 'Filas por página:';
  intl.nextPageLabel = 'Página siguiente';
  intl.previousPageLabel = 'Página anterior';
  intl.firstPageLabel = 'Primera página';
  intl.lastPageLabel = 'Última página';

  intl.getRangeLabel = (pagina: number, tamano: number, total: number): string => {
    if (total === 0) {
      return 'Sin resultados';
    }
    const desde = pagina * tamano;
    // El último elemento de la página no puede pasarse del total, y el total
    // puede cambiar entre peticiones si alguien más está creando usuarios.
    const hasta = Math.min(desde + tamano, total);
    return `${desde + 1} – ${hasta} de ${total}`;
  };

  return intl;
}
