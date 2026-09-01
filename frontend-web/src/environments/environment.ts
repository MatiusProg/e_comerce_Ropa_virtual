/**
 * Entorno de DESARROLLO.
 * La API corre en local (uvicorn --reload) o en el contenedor de docker-compose.
 */
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000/api/v1',
};
