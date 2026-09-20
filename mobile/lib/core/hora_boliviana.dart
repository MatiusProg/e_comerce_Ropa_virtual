/// La hora de Bolivia en el teléfono. Espejo de `app/core/tiempo.py`.
///
/// EL DEFECTO QUE ESTO ARREGLA — 20/09/2026
/// ------------------------------------------
/// El servidor manda las fechas **ya en hora boliviana**, con su desfase:
///
///     "2026-09-20T13:16:13-04:00"
///
/// Y `DateTime.parse` **las convierte a UTC**: devuelve un `DateTime` con
/// `isUtc: true` valiendo `17:16Z`. Formatearlo con `DateFormat` muestra
/// entonces **17:16 donde tenía que decir 13:16**. Cuatro horas adelantada,
/// sin ningún error, sin nada que avise.
///
/// Pasó en la bitácora y lo vio Mateo probando el APK.
///
/// POR QUÉ NO ALCANZA CON `toLocal()`
/// ------------------------------------
/// En un teléfono configurado en Bolivia da el resultado correcto, y por eso
/// es tentador. Pero entonces la pantalla depende de la zona del aparato: un
/// teléfono con la hora mal puesta —o el de alguien que viajó— mostraría una
/// bitácora distinta a la de la computadora de al lado, **sobre un registro
/// cuyo único valor es que todos vean lo mismo**.
///
/// Se fija el desfase y listo. Bolivia está en UTC-4 sin horario de verano
/// desde 1932: no hay transiciones que resolver.
library;

/// El desfase de Bolivia. Fijo, sin horario de verano.
const Duration desfaseBolivia = Duration(hours: -4);

/// El mismo instante, con los valores de reloj de Bolivia.
///
/// Lo que devuelve queda marcado como UTC aunque no lo sea: es un
/// contenedor de «hora de pared» para que `DateFormat` imprima esos números
/// tal cual. **No se usa para comparar ni para restar** — para eso está el
/// instante original.
DateTime enHoraBoliviana(DateTime momento) =>
    momento.toUtc().add(desfaseBolivia);
