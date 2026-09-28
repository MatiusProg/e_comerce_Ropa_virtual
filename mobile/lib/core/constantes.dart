/// Constantes de configuracion de la aplicacion movil.
///
/// El equivalente de `frontend-web/src/environments/environment*.ts`. La web
/// resuelve el entorno en tiempo de compilacion con dos archivos; Flutter lo
/// hace con `--dart-define`, que es el mecanismo equivalente y no obliga a
/// mantener dos copias del archivo.
library;

/// URL base de la API, incluido el prefijo de version.
///
/// Por omision apunta a la API **desplegada en Railway**, para que `flutter run`
/// funcione en cualquier maquina sin levantar el backend en local. Para apuntar
/// a un backend local:
///
/// ```bash
/// flutter run --dart-define=API_URL=http://10.0.2.2:8000/api/v1
/// ```
///
/// Nota: en el emulador de Android `localhost` es el propio emulador, no la
/// maquina anfitriona. La direccion del anfitrion es `10.0.2.2`.
///
/// En un **telefono fisico** conectado por USB, `10.0.2.2` tampoco sirve: hay
/// que usar la IP de la PC en la red local, y el backend tiene que escuchar
/// en `0.0.0.0` y no en `127.0.0.1`.
///
/// ```bash
/// flutter run --dart-define=API_URL=http://192.168.0.10:8000/api/v1
/// ```
const String apiUrlBase = String.fromEnvironment(
  'API_URL',
  defaultValue: 'https://ecomerceropavirtual-production.up.railway.app/api/v1',
);

/// La version de esta compilacion, para poder saber CUAL esta instalada.
///
/// POR QUE ESTA A MANO Y NO SALE DEL `pubspec`
/// ---------------------------------------------
/// Dart no puede leer el `pubspec` en tiempo de ejecucion: hace falta un
/// complemento (`package_info_plus`) que consulte al sistema operativo. Una
/// constante duplicada es peor que una fuente unica, pero agregar una
/// dependencia nativa la vispera de la entrega es peor todavia.
///
/// **Si cambia el `version:` del `pubspec`, cambiar esta linea tambien.**
///
/// Existe porque el 20/09 se publico un APK nuevo, se instalo encima del
/// viejo, y no habia forma de saber desde la pantalla cual de los dos estaba
/// corriendo: las dos versiones se veian parecidas y la duda tardo en
/// resolverse. Un numero a la vista lo contesta en un segundo.
const String versionApp = '1.0.0+2';

/// Tiempo maximo de espera para establecer la conexion.
const Duration tiempoDeConexion = Duration(seconds: 15);

/// Tiempo maximo de espera para recibir la respuesta.
///
/// Holgado a proposito: el plan gratuito de Railway duerme el servicio cuando
/// no recibe trafico, y la primera peticion despues de un rato paga el arranque
/// en frio.
const Duration tiempoDeRespuesta = Duration(seconds: 30);

/// Claves del almacenamiento seguro. Centralizadas para que no se escriban a
/// mano en dos lugares y dejen de coincidir.
class ClavesAlmacen {
  const ClavesAlmacen._();

  static const String token = 'vb_access_token';
  static const String expiraEn = 'vb_token_expira_en';
}
