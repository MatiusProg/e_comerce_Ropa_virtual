/// Configuracion de entorno de la app movil.
///
/// La URL de la API no se escribe en el codigo de cada repositorio: se resuelve
/// aca una sola vez. Se puede apuntar a otro servidor sin tocar el codigo:
///
///   flutter run --dart-define=API_URL=http://192.168.0.10:8000/api/v1
///
/// Eso hace falta al probar contra el backend local desde el telefono, porque
/// para el telefono `localhost` es el telefono, no la PC.
class Entorno {
  const Entorno._();

  /// API desplegada en Railway. Es el valor por defecto a proposito: el
  /// telefono no necesita que nadie levante nada para que la app funcione.
  static const String urlApi = String.fromEnvironment(
    'API_URL',
    defaultValue:
        'https://ecomerceropavirtual-production.up.railway.app/api/v1',
  );

  /// Tiempo maximo de espera de una peticion. Railway duerme los servicios
  /// inactivos del plan gratuito y la primera llamada del dia puede tardar.
  static const Duration esperaConexion = Duration(seconds: 20);
  static const Duration esperaRespuesta = Duration(seconds: 30);
}
