/// CU-02 · Iniciar sesion.
///
/// Contraparte movil de `features/auth/login/` de la web. Los mensajes de error
/// no se inventan aqui: se muestra el `detail` que devuelve el backend, que ya
/// distingue credenciales invalidas (401) de cuenta desactivada (403).
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/enrutado/router.dart';
import '../../core/red/excepciones.dart';
import '../../core/tema.dart';
import 'estado_sesion.dart';

class PantallaLogin extends ConsumerStatefulWidget {
  const PantallaLogin({super.key});

  @override
  ConsumerState<PantallaLogin> createState() => _PantallaLoginState();
}

class _PantallaLoginState extends ConsumerState<PantallaLogin> {
  final _formulario = GlobalKey<FormState>();
  final _correo = TextEditingController();
  final _contrasena = TextEditingController();

  bool _enviando = false;
  bool _ocultarContrasena = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    // Si la sesion se cerro sola por token expirado, el estado trae el aviso.
    final sesion = ref.read(sesionProvider);
    if (sesion is SesionCerrada && sesion.aviso != null) {
      _error = sesion.aviso;
    }
  }

  @override
  void dispose() {
    _correo.dispose();
    _contrasena.dispose();
    super.dispose();
  }

  Future<void> _entrar() async {
    if (!_formulario.currentState!.validate()) return;

    setState(() {
      _enviando = true;
      _error = null;
    });

    try {
      await ref
          .read(sesionProvider.notifier)
          .iniciarSesion(
            correo: _correo.text,
            contrasena: _contrasena.text,
          );
      // No se navega a mano: al cambiar la sesion, la redireccion del
      // enrutador lleva sola al inicio.
    } on ErrorApi catch (fallo) {
      if (mounted) setState(() => _error = fallo.mensaje);
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: degradadoVB),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 420),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const _Encabezado(),
                    const SizedBox(height: 28),
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(24),
                        child: Form(
                          key: _formulario,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              Text(
                                'Iniciar sesion',
                                textAlign: TextAlign.center,
                                style: Theme.of(context).textTheme.titleLarge
                                    ?.copyWith(fontWeight: FontWeight.w600),
                              ),
                              const SizedBox(height: 20),
                              TextFormField(
                                controller: _correo,
                                enabled: !_enviando,
                                keyboardType: TextInputType.emailAddress,
                                textInputAction: TextInputAction.next,
                                autofillHints: const [AutofillHints.email],
                                decoration: const InputDecoration(
                                  labelText: 'Correo electronico',
                                  prefixIcon: Icon(Icons.mail_outline),
                                ),
                                validator: validarCorreo,
                              ),
                              const SizedBox(height: 14),
                              TextFormField(
                                controller: _contrasena,
                                enabled: !_enviando,
                                obscureText: _ocultarContrasena,
                                textInputAction: TextInputAction.done,
                                autofillHints: const [AutofillHints.password],
                                onFieldSubmitted: (_) => _entrar(),
                                decoration: InputDecoration(
                                  labelText: 'Contrasena',
                                  prefixIcon: const Icon(Icons.lock_outline),
                                  suffixIcon: IconButton(
                                    onPressed: () => setState(
                                      () => _ocultarContrasena =
                                          !_ocultarContrasena,
                                    ),
                                    icon: Icon(
                                      _ocultarContrasena
                                          ? Icons.visibility_outlined
                                          : Icons.visibility_off_outlined,
                                    ),
                                    tooltip: _ocultarContrasena
                                        ? 'Mostrar contrasena'
                                        : 'Ocultar contrasena',
                                  ),
                                ),
                                validator: (valor) =>
                                    (valor == null || valor.isEmpty)
                                    ? 'Ingrese su contrasena'
                                    : null,
                              ),
                              if (_error != null) ...[
                                const SizedBox(height: 16),
                                AvisoError(mensaje: _error!),
                              ],
                              const SizedBox(height: 22),
                              FilledButton(
                                onPressed: _enviando ? null : _entrar,
                                child: _enviando
                                    ? const SizedBox(
                                        width: 22,
                                        height: 22,
                                        child: CircularProgressIndicator(
                                          strokeWidth: 2.5,
                                          color: Colors.white,
                                        ),
                                      )
                                    : const Text('Entrar'),
                              ),
                              const SizedBox(height: 6),
                              TextButton(
                                onPressed: _enviando
                                    ? null
                                    : () => context.go(Rutas.registro),
                                child: const Text(
                                  'No tengo cuenta — Registrarme',
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _Encabezado extends StatelessWidget {
  const _Encabezado();

  @override
  Widget build(BuildContext context) {
    return const Column(
      children: [
        Icon(Icons.checkroom, color: Colors.white, size: 46),
        SizedBox(height: 10),
        Text(
          'Violet Boutique',
          style: TextStyle(
            color: Colors.white,
            fontSize: 28,
            fontWeight: FontWeight.w300,
            letterSpacing: 2.5,
          ),
        ),
      ],
    );
  }
}

/// Bloque de error de formulario. Compartido por login y registro.
class AvisoError extends StatelessWidget {
  const AvisoError({required this.mensaje, super.key});

  final String mensaje;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: const Color(0xFFFDECEF),
        borderRadius: BorderRadius.circular(radioChicoVB),
        border: Border.all(color: const Color(0xFFF3C6CF)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.error_outline, size: 20, color: Color(0xFFB3261E)),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              mensaje,
              style: const TextStyle(color: Color(0xFF8C1D18), fontSize: 13.5),
            ),
          ),
        ],
      ),
    );
  }
}

/// Validacion de correo, compartida por los dos formularios de `auth`.
///
/// Deliberadamente laxa: la validacion que manda es la del backend
/// (`EmailStr` de Pydantic). Esta solo evita gastar una llamada de red en un
/// campo vacio o sin arroba.
String? validarCorreo(String? valor) {
  final texto = valor?.trim() ?? '';
  if (texto.isEmpty) return 'Ingrese su correo electronico';
  if (!RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(texto)) {
    return 'El correo no tiene un formato valido';
  }
  return null;
}
