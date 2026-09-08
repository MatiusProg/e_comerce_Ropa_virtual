import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/enrutado/router.dart';
import '../../../core/red/error_api.dart';
import '../estado/sesion.dart';
import '../widgets/aviso_de_error.dart';

/// CU-02 · Iniciar sesion.
///
/// Recibe `correoSugerido` cuando se llega desde el registro (CU-01 paso 8),
/// para no obligar a escribir de nuevo el correo recien creado.
class LoginPantalla extends ConsumerStatefulWidget {
  const LoginPantalla({super.key, this.correoSugerido});

  final String? correoSugerido;

  @override
  ConsumerState<LoginPantalla> createState() => _LoginPantallaState();
}

class _LoginPantallaState extends ConsumerState<LoginPantalla> {
  final _formulario = GlobalKey<FormState>();
  late final TextEditingController _correo =
      TextEditingController(text: widget.correoSugerido ?? '');
  final _contrasena = TextEditingController();

  bool _enviando = false;
  bool _oculta = true;
  String? _error;

  @override
  void dispose() {
    _correo.dispose();
    _contrasena.dispose();
    super.dispose();
  }

  Future<void> _enviar() async {
    if (!_formulario.currentState!.validate()) return;

    setState(() {
      _enviando = true;
      _error = null;
    });

    try {
      await ref
          .read(sesionProvider.notifier)
          .iniciar(_correo.text, _contrasena.text);
      // No se navega a mano: el `redirect` del enrutado reacciona al cambio de
      // sesion y lleva a /inicio. Si se hiciera aca, se harian las dos cosas.
    } on ErrorApi catch (error) {
      if (mounted) setState(() => _error = error.mensaje);
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Form(
                key: _formulario,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      'Violet Boutique',
                      textAlign: TextAlign.center,
                      style: tema.textTheme.headlineSmall?.copyWith(
                        color: tema.colorScheme.primary,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Ingresá con tu cuenta',
                      textAlign: TextAlign.center,
                      style: tema.textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 32),
                    TextFormField(
                      controller: _correo,
                      decoration: const InputDecoration(
                        labelText: 'Correo electrónico',
                        prefixIcon: Icon(Icons.mail_outline),
                      ),
                      keyboardType: TextInputType.emailAddress,
                      textInputAction: TextInputAction.next,
                      autofillHints: const [AutofillHints.email],
                      validator: (valor) {
                        final texto = (valor ?? '').trim();
                        if (texto.isEmpty) return 'Escribí tu correo.';
                        if (!texto.contains('@') || !texto.contains('.')) {
                          return 'Ese correo no parece válido.';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _contrasena,
                      decoration: InputDecoration(
                        labelText: 'Contraseña',
                        prefixIcon: const Icon(Icons.lock_outline),
                        suffixIcon: IconButton(
                          icon: Icon(
                            _oculta ? Icons.visibility : Icons.visibility_off,
                          ),
                          onPressed: () => setState(() => _oculta = !_oculta),
                        ),
                      ),
                      obscureText: _oculta,
                      textInputAction: TextInputAction.done,
                      autofillHints: const [AutofillHints.password],
                      onFieldSubmitted: (_) => _enviando ? null : _enviar(),
                      validator: (valor) => (valor ?? '').isEmpty
                          ? 'Escribí tu contraseña.'
                          : null,
                    ),
                    if (_error != null) ...[
                      const SizedBox(height: 16),
                      AvisoDeError(mensaje: _error!),
                    ],
                    const SizedBox(height: 24),
                    FilledButton(
                      onPressed: _enviando ? null : _enviar,
                      child: _enviando
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Text('Iniciar sesión'),
                    ),
                    const SizedBox(height: 12),
                    TextButton(
                      onPressed: _enviando
                          ? null
                          : () => context.go(Rutas.registro),
                      child: const Text('¿No tenés cuenta? Registrate'),
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
