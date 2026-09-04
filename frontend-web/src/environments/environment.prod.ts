/**
 * Entorno de PRODUCCION.
 * La web se sirve desde Railway y consume la API tambien desplegada en Railway,
 * que a su vez usa la base de datos de Supabase.
 *
 * Si este dominio cambia hay que cambiarlo aqui Y en CORS_ORIGINS del servicio
 * `api`: si solo se cambia aqui, la web carga bien y ninguna peticion funciona.
 */
export const environment = {
  production: true,
  apiUrl: 'https://ecomerceropavirtual-production.up.railway.app/api/v1',
};
