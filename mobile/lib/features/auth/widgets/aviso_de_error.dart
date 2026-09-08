import 'package:flutter/material.dart';

/// Muestra los mensajes de los flujos alternativos del caso de uso tal como
/// los redacta el backend: E1 credenciales invalidas, E2 cuenta desactivada,
/// correo o documento ya registrados.
class AvisoDeError extends StatelessWidget {
  const AvisoDeError({super.key, required this.mensaje});

  final String mensaje;

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: tema.colorScheme.errorContainer,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            Icons.error_outline,
            size: 20,
            color: tema.colorScheme.onErrorContainer,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              mensaje,
              style: TextStyle(color: tema.colorScheme.onErrorContainer),
            ),
          ),
        ],
      ),
    );
  }
}
