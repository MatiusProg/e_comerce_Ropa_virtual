/// Modelos del contrato del perfil del cliente (CU-04).
///
/// Cada clase refleja un esquema de `backend/app/modules/seguridad/schemas.py`.
/// Igual que en `auth.dart`, los nombres de los campos JSON se escriben tal
/// como los emite la API y no se traducen.
library;

/// Espejo de `CiudadOut`. Solo se leen los tres campos que necesita el
/// selector de ciudad del formulario de direcciones; el resto de la respuesta
/// —los contadores de sucursales, que consume el panel de CU-05— se ignora.
class Ciudad {
  const Ciudad({
    required this.id,
    required this.nombre,
    required this.departamento,
  });

  final int id;
  final String nombre;
  final String departamento;

  factory Ciudad.desdeJson(Map<String, dynamic> json) => Ciudad(
    id: json['id'] as int,
    nombre: json['nombre'] as String,
    departamento: json['departamento'] as String,
  );
}

/// Espejo de `DireccionOut`. Una dirección de entrega del cliente.
class Direccion {
  const Direccion({
    required this.id,
    required this.ciudadId,
    required this.ciudad,
    required this.alias,
    required this.direccion,
    required this.predeterminada,
    this.referencia,
  });

  final int id;
  final int ciudadId;

  /// Nombre de la ciudad ya resuelto por el backend, para no tener que
  /// cruzarlo contra el listado al mostrar la lista.
  final String ciudad;

  final String alias;
  final String direccion;
  final String? referencia;
  final bool predeterminada;

  factory Direccion.desdeJson(Map<String, dynamic> json) => Direccion(
    id: json['id'] as int,
    ciudadId: json['ciudad_id'] as int,
    ciudad: json['ciudad'] as String,
    alias: json['alias'] as String,
    direccion: json['direccion'] as String,
    referencia: json['referencia'] as String?,
    predeterminada: json['predeterminada'] as bool,
  );
}

/// Espejo de `PerfilOut`. Es lo que muestra el paso 2 del flujo principal.
///
/// Las **categorías preferidas** que ese paso también menciona no están: son
/// del Ciclo 2 y su tabla es de Karen. Ver §6.11.3 de decisiones técnicas y §3
/// de la contrapropuesta del ciclo.
class Perfil {
  const Perfil({
    required this.nombres,
    required this.apellidos,
    required this.correo,
    required this.direcciones,
    this.documento,
    this.telefono,
    this.tallaSuperior,
    this.tallaInferior,
    this.tallaCalzado,
  });

  final String nombres;
  final String apellidos;
  final String correo;
  final String? documento;
  final String? telefono;

  /// Tallas habituales. Alimentan al recomendador del Ciclo 3 (CU-33).
  final String? tallaSuperior;
  final String? tallaInferior;
  final String? tallaCalzado;

  final List<Direccion> direcciones;

  String get nombreCompleto => '$nombres $apellidos';

  bool get tieneTallas =>
      tallaSuperior != null || tallaInferior != null || tallaCalzado != null;

  /// El mismo perfil con otra lista de direcciones. Los tres endpoints de
  /// direcciones devuelven la lista completa ya reordenada, así que alcanza
  /// con reemplazarla: pedir el perfil entero de nuevo sería una llamada de
  /// red por cada alta, baja o cambio de predeterminada.
  Perfil conDirecciones(List<Direccion> nuevas) => Perfil(
    nombres: nombres,
    apellidos: apellidos,
    correo: correo,
    documento: documento,
    telefono: telefono,
    tallaSuperior: tallaSuperior,
    tallaInferior: tallaInferior,
    tallaCalzado: tallaCalzado,
    direcciones: nuevas,
  );

  factory Perfil.desdeJson(Map<String, dynamic> json) => Perfil(
    nombres: json['nombres'] as String,
    apellidos: json['apellidos'] as String,
    correo: json['correo'] as String,
    documento: json['documento'] as String?,
    telefono: json['telefono'] as String?,
    tallaSuperior: json['talla_superior'] as String?,
    tallaInferior: json['talla_inferior'] as String?,
    tallaCalzado: json['talla_calzado'] as String?,
    direcciones: (json['direcciones'] as List<dynamic>)
        .map((e) => Direccion.desdeJson(e as Map<String, dynamic>))
        .toList(),
  );
}

/// Espejo de `PerfilEditarIn` (paso 3 del flujo principal).
///
/// El backend distingue **no enviar** un campo de **enviarlo vacío**: lo
/// primero lo deja como está, lo segundo lo borra. Como esta pantalla es un
/// formulario completo —muestra todos los campos a la vez y el usuario ve lo
/// que va a quedar—, se envían siempre todos, con cadena vacía en los que se
/// dejaron en blanco. Así vaciar un campo funciona, que es lo que el usuario
/// espera al borrar su teléfono y guardar.
class EdicionPerfil {
  const EdicionPerfil({
    required this.nombres,
    required this.apellidos,
    required this.correo,
    required this.documento,
    required this.telefono,
    required this.tallaSuperior,
    required this.tallaInferior,
    required this.tallaCalzado,
  });

  final String nombres;
  final String apellidos;
  final String correo;
  final String documento;
  final String telefono;
  final String tallaSuperior;
  final String tallaInferior;
  final String tallaCalzado;

  Map<String, dynamic> aJson() => {
    'nombres': nombres.trim(),
    'apellidos': apellidos.trim(),
    'correo': correo.trim().toLowerCase(),
    'documento': documento.trim(),
    'telefono': telefono.trim(),
    'talla_superior': tallaSuperior.trim(),
    'talla_inferior': tallaInferior.trim(),
    'talla_calzado': tallaCalzado.trim(),
  };
}

/// Espejo de `DireccionIn` (flujo alternativo 3a).
class NuevaDireccion {
  const NuevaDireccion({
    required this.ciudadId,
    required this.alias,
    required this.direccion,
    this.referencia,
    this.predeterminada = false,
  });

  final int ciudadId;
  final String alias;
  final String direccion;
  final String? referencia;
  final bool predeterminada;

  Map<String, dynamic> aJson() => {
    'ciudad_id': ciudadId,
    'alias': alias.trim(),
    'direccion': direccion.trim(),
    'predeterminada': predeterminada,
    if (referencia != null && referencia!.trim().isNotEmpty)
      'referencia': referencia!.trim(),
  };
}

/// Espejo de `CambioContrasenaIn` (flujo alternativo 3c).
///
/// La repetición viaja al servidor a propósito: el caso de uso pide la
/// contraseña nueva dos veces y el backend valida que coincidan, para que un
/// cliente de la API que no sea esta app tampoco pueda saltarse el paso.
class CambioContrasena {
  const CambioContrasena({
    required this.actual,
    required this.nueva,
    required this.repetida,
  });

  final String actual;
  final String nueva;
  final String repetida;

  Map<String, dynamic> aJson() => {
    'contrasena_actual': actual,
    'contrasena_nueva': nueva,
    'contrasena_repetida': repetida,
  };
}
