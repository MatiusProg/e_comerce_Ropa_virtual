/// CU-01 · Registrar cliente.
///
/// El caso de uso termina invitando a iniciar sesion, no dentro de la app: el
/// backend responde 201 sin token. Por eso al registrarse con exito se vuelve
/// al login con el correo ya cargado, y no se entra directo.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/enrutado/router.dart';
import '../../core/red/excepciones.dart';
import '../../core/tema.dart';
import '../../data/modelos/auth.dart';
import '../../data/repositorios/repositorio_auth.dart';
import 'estado_sesion.dart';
import 'pantalla_login.dart' show AvisoError, validarCorreo;

class PantallaRegistro extends ConsumerStatefulWidget {
  const PantallaRegistro({super.key});

  @override
  ConsumerState<PantallaRegistro> createState() => _PantallaRegistroState();
}

class _PantallaRegistroState extends ConsumerState<PantallaRegistro> {
  final _formulario = GlobalKey<FormState>();
  final _nombres = TextEditingController();
  final _apellidos = TextEditingController();
  final _documento = TextEditingController();
  final _telefono = TextEditingController();
  final _correo = TextEditingController();
  final _contrasena = TextEditingController();
  final _repetir = TextEditingController();

  bool _enviando = false;
  bool _ocultarContrasena = true;
  String? _error;

  @override
  void dispose() {
    for (final c in [
      _nombres,
      _apellidos,
      _documento,
      _telefono,
      _correo,
      _contrasena,
      _repetir,
    ]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _registrar() async {
    if (!_formulario.currentState!.validate()) return;

    setState(() {
      _enviando = true;
      _error = null;
    });

    try {
      await ref
          .read(repositorioAuthProvider)
          .registrar(
            DatosRegistro(
              nombres: _nombres.text,
              apellidos: _apellidos.text,
              documento: _documento.text,
              telefono: _telefono.text,
              correo: _correo.text,
              contrasena: _contrasena.text,
            ),
          );

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Cuenta creada. Ya puede iniciar sesión.'),
          backgroundColor: ColoresVB.malva,
        ),
      );
      context.go(Rutas.login);
    } on ErrorApi catch (fallo) {
      if (mounted) setState(() => _error = fallo.mensaje);
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Crear cuenta'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: _enviando ? null : () => context.go(Rutas.login),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 480),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(22),
                  child: Form(
                    key: _formulario,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        _campo(
                          controlador: _nombres,
                          etiqueta: 'Nombres',
                          icono: Icons.person_outline,
                          obligatorio: 'Ingrese sus nombres',
                          maximo: 80,
                        ),
                        _campo(
                          controlador: _apellidos,
                          etiqueta: 'Apellidos',
                          icono: Icons.badge_outlined,
                          obligatorio: 'Ingrese sus apellidos',
                          maximo: 80,
                        ),
                        _campo(
                          controlador: _documento,
                          etiqueta: 'Documento de identidad (opcional)',
                          icono: Icons.credit_card,
                          maximo: 20,
                        ),
                        _campo(
                          controlador: _telefono,
                          etiqueta: 'Teléfono (opcional)',
                          icono: Icons.phone_outlined,
                          teclado: TextInputType.phone,
                          maximo: 20,
                        ),
                        _campo(
                          controlador: _correo,
                          etiqueta: 'Correo electrónico',
                          icono: Icons.mail_outline,
                          teclado: TextInputType.emailAddress,
                          validador: validarCorreo,
                          maximo: 120,
                        ),
                        _campoContrasena(
                          controlador: _contrasena,
                          etiqueta: 'Contraseña',
                          validador: (valor) {
                            final texto = valor ?? '';
                            if (texto.isEmpty) return 'Ingrese una contraseña';
                            if (texto.length < contrasenaLongitudMinima) {
                              return 'Debe tener al menos '
                                  '$contrasenaLongitudMinima caracteres';
                            }
                            return null;
                          },
                        ),
                        _campoContrasena(
                          controlador: _repetir,
                          etiqueta: 'Repetir contraseña',
                          validador: (valor) => valor != _contrasena.text
                              ? 'Las contraseñas no coinciden'
                              : null,
                        ),
                        if (_error != null) ...[
                          const SizedBox(height: 6),
                          AvisoError(mensaje: _error!),
                        ],
                        const SizedBox(height: 20),
                        FilledButton(
                          onPressed: _enviando ? null : _registrar,
                          child: _enviando
                              ? const SizedBox(
                                  width: 22,
                                  height: 22,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2.5,
                                    color: Colors.white,
                                  ),
                                )
                              : const Text('Crear cuenta'),
                        ),
                        TextButton(
                          onPressed: _enviando
                              ? null
                              : () => context.go(Rutas.login),
                          child: const Text('Ya tengo cuenta — Iniciar sesión'),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _campo({
    required TextEditingController controlador,
    required String etiqueta,
    required IconData icono,
    String? obligatorio,
    String? Function(String?)? validador,
    TextInputType? teclado,
    int? maximo,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: TextFormField(
        controller: controlador,
        enabled: !_enviando,
        keyboardType: teclado,
        maxLength: maximo,
        textInputAction: TextInputAction.next,
        decoration: InputDecoration(
          labelText: etiqueta,
          prefixIcon: Icon(icono),
          counterText: '',
        ),
        validator:
            validador ??
            (valor) {
              if (obligatorio == null) return null;
              return (valor == null || valor.trim().isEmpty)
                  ? obligatorio
                  : null;
            },
      ),
    );
  }

  Widget _campoContrasena({
    required TextEditingController controlador,
    required String etiqueta,
    required String? Function(String?) validador,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: TextFormField(
        controller: controlador,
        enabled: !_enviando,
        obscureText: _ocultarContrasena,
        maxLength: 128,
        decoration: InputDecoration(
          labelText: etiqueta,
          prefixIcon: const Icon(Icons.lock_outline),
          counterText: '',
          suffixIcon: IconButton(
            onPressed: () =>
                setState(() => _ocultarContrasena = !_ocultarContrasena),
            icon: Icon(
              _ocultarContrasena
                  ? Icons.visibility_outlined
                  : Icons.visibility_off_outlined,
            ),
          ),
        ),
        validator: validador,
      ),
    );
  }
}
