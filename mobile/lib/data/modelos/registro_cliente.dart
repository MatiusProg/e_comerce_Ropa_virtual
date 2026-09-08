/// Datos del formulario de registro (CU-01, paso 3).
///
/// Replica `ClienteRegistroIn`. Los campos opcionales viajan solo si tienen
/// valor: el backend distingue ausencia de cadena vacia, y mandar `""` en
/// `documento` haria fallar la validacion de longitud.
class RegistroCliente {
  const RegistroCliente({
    required this.nombres,
    required this.apellidos,
    required this.correo,
    required this.contrasena,
    this.documento,
    this.telefono,
  });

  final String nombres;
  final String apellidos;
  final String correo;
  final String contrasena;
  final String? documento;
  final String? telefono;

  Map<String, dynamic> aJson() => {
        'nombres': nombres.trim(),
        'apellidos': apellidos.trim(),
        'correo': correo.trim().toLowerCase(),
        'contrasena': contrasena,
        if (documento != null && documento!.trim().isNotEmpty)
          'documento': documento!.trim(),
        if (telefono != null && telefono!.trim().isNotEmpty)
          'telefono': telefono!.trim(),
      };
}
