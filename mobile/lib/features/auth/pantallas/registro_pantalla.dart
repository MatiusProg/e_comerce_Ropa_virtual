import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/enrutado/router.dart';
import '../../../core/red/error_api.dart';
import '../../../data/modelos/registro_cliente.dart';
import '../../../data/repositorios/auth_repositorio.dart';
import '../widgets/aviso_de_error.dart';

/// CU-01 · Registrar cliente.
///
/// Termina en el login, no dentro de la aplicacion: el endpoint de registro no
/// emite token a proposito —el paso 8 del flujo principal invita a iniciar
/// sesion, y emitir el token es CU-02—.
class RegistroPantalla extends ConsumerStatefulWidget {
  const RegistroPantalla({super.key});

  @override
  ConsumerState<RegistroPantalla> createState() => _RegistroPantallaState();
}

class _RegistroPantallaState extends ConsumerState<RegistroPantalla> {
  final _formulario = GlobalKey<FormState>();
  final _nombres = TextEditingController();
  final _apellidos = TextEditingController();
  final _documento = TextEditingController();
  final _telefono = TextEditingController();
  final _correo = TextEditingController();
  final _contrasena = TextEditingController();
  final _repeticion = TextEditingController();

  bool _enviando = false;
  bool _oculta = true;
  String? _error;

  @override
  void dispose() {
    for (final campo in [
      _nombres,
      _apellidos,
      _documento,
      _telefono,
      _correo,
      _contrasena,
      _repeticion,
    ]) {
      campo.dispose();
    }
    super.dispose();
  }

  Future<void> _enviar() async {
    if (!_formulario.currentState!.validate()) return;

    setState(() {
      _enviando = true;
      _error = null;
    });

    try {
      final cliente = await ref.read(authRepositorioProvider).registrar(
            RegistroCliente(
              nombres: _nombres.text,
              apellidos: _apellidos.text,
              correo: _correo.text,
              contrasena: _contrasena.text,
              documento: _documento.text,
              telefono: _telefono.text,
            ),
          );

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Cuenta creada, ${cliente.nombres}. Ingresá con tu correo.',
          ),
        ),
      );
      final correo = Uri.encodeComponent(cliente.correo);
      context.go('${Rutas.login}?correo=$correo');
    } on ErrorApi catch (error) {
      // Excepcion E1 del caso de uso: el correo o el documento ya estan
      // registrados (409). El mensaje viene del backend y ya distingue cual
      // de los dos es; repetirlo aca los dejaria desincronizados.
      if (mounted) setState(() => _error = error.mensaje);
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  String? _obligatorio(String? valor, String campo) =>
      (valor ?? '').trim().isEmpty ? 'Escribí $campo.' : null;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Crear cuenta')),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Form(
                key: _formulario,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    TextFormField(
                      controller: _nombres,
                      decoration: const InputDecoration(labelText: 'Nombres'),
                      textCapitalization: TextCapitalization.words,
                      textInputAction: TextInputAction.next,
                      maxLength: 80,
                      validator: (v) => _obligatorio(v, 'tus nombres'),
                    ),
                    TextFormField(
                      controller: _apellidos,
                      decoration: const InputDecoration(labelText: 'Apellidos'),
                      textCapitalization: TextCapitalization.words,
                      textInputAction: TextInputAction.next,
                      maxLength: 80,
                      validator: (v) => _obligatorio(v, 'tus apellidos'),
                    ),
                    TextFormField(
                      controller: _documento,
                      decoration: const InputDecoration(
                        labelText: 'Documento de identidad (opcional)',
                      ),
                      textInputAction: TextInputAction.next,
                      maxLength: 20,
                    ),
                    TextFormField(
                      controller: _telefono,
                      decoration: const InputDecoration(
                        labelText: 'Teléfono (opcional)',
                      ),
                      keyboardType: TextInputType.phone,
                      textInputAction: TextInputAction.next,
                      maxLength: 20,
                    ),
                    TextFormField(
                      controller: _correo,
                      decoration: const InputDecoration(
                        labelText: 'Correo electrónico',
                      ),
                      keyboardType: TextInputType.emailAddress,
                      textInputAction: TextInputAction.next,
                      maxLength: 120,
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
                    TextFormField(
                      controller: _contrasena,
                      decoration: InputDecoration(
                        labelText: 'Contraseña',
                        helperText:
                            'Al menos 8 caracteres, con letras y números',
                        suffixIcon: IconButton(
                          icon: Icon(
                            _oculta ? Icons.visibility : Icons.visibility_off,
                          ),
                          onPressed: () => setState(() => _oculta = !_oculta),
                        ),
                      ),
                      obscureText: _oculta,
                      textInputAction: TextInputAction.next,
                      maxLength: 128,
                      // Las mismas tres reglas que CONTRASENA_LONGITUD_MINIMA
                      // y _contrasena_fuerte del backend. Se repiten aca para
                      // avisar antes de gastar una peticion, no para
                      // reemplazar la validacion del servidor.
                      validator: (valor) {
                        final texto = valor ?? '';
                        if (texto.length < 8) {
                          return 'Tiene que tener al menos 8 caracteres.';
                        }
                        final tieneLetra = RegExp(r'[A-Za-z]').hasMatch(texto);
                        final tieneDigito = RegExp(r'\d').hasMatch(texto);
                        if (!tieneLetra || !tieneDigito) {
                          return 'Tiene que incluir al menos una letra y un número.';
                        }
                        return null;
                      },
                    ),
                    TextFormField(
                      controller: _repeticion,
                      decoration: const InputDecoration(
                        labelText: 'Repetí la contraseña',
                      ),
                      obscureText: _oculta,
                      textInputAction: TextInputAction.done,
                      maxLength: 128,
                      onFieldSubmitted: (_) => _enviando ? null : _enviar(),
                      validator: (valor) => valor != _contrasena.text
                          ? 'Las dos contraseñas no coinciden.'
                          : null,
                    ),
                    if (_error != null) ...[
                      const SizedBox(height: 8),
                      AvisoDeError(mensaje: _error!),
                    ],
                    const SizedBox(height: 20),
                    FilledButton(
                      onPressed: _enviando ? null : _enviar,
                      child: _enviando
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Text('Crear cuenta'),
                    ),
                    const SizedBox(height: 8),
                    TextButton(
                      onPressed:
                          _enviando ? null : () => context.go(Rutas.login),
                      child: const Text('Ya tengo cuenta'),
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
