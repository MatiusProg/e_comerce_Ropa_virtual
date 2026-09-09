/// Los tres formularios del perfil (CU-04), como hojas inferiores.
///
/// Son hojas y no rutas propias a propósito: `core/enrutado/router.dart` es uno
/// de los cinco archivos compartidos del ciclo, y cada ruta que no hace falta
/// agregar ahí es una ocasión menos de chocar. Además el formulario vuelve
/// exactamente al punto del perfil desde donde se abrió.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/red/excepciones.dart';
import '../../data/modelos/perfil.dart';
import '../../data/repositorios/repositorio_auth.dart' show contrasenaLongitudMinima;
import '../auth/estado_sesion.dart';
import '../auth/pantalla_login.dart' show AvisoError, validarCorreo;
import 'estado_perfil.dart';

/// Abre una hoja inferior que ocupa lo que necesite y sube con el teclado.
Future<void> _abrirHoja(BuildContext context, Widget contenido) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (contextoHoja) => Padding(
      // El teclado tapa los campos de abajo si la hoja no se levanta con el.
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(contextoHoja).viewInsets.bottom,
      ),
      child: contenido,
    ),
  );
}

Future<void> abrirEdicionDeDatos(BuildContext context, Perfil perfil) =>
    _abrirHoja(context, _FormularioDatos(perfil: perfil));

Future<void> abrirNuevaDireccion(BuildContext context) =>
    _abrirHoja(context, const _FormularioDireccion());

Future<void> abrirCambioDeContrasena(BuildContext context) =>
    _abrirHoja(context, const _FormularioContrasena());

/// Envoltorio común: título, contenido y botón de guardar con su estado de
/// envío y su aviso de error.
class _Hoja extends StatelessWidget {
  const _Hoja({
    required this.titulo,
    required this.campos,
    required this.enviando,
    required this.error,
    required this.alGuardar,
    required this.textoBoton,
  });

  final String titulo;
  final List<Widget> campos;
  final bool enviando;
  final String? error;
  final VoidCallback alGuardar;
  final String textoBoton;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Center(
            child: Container(
              width: 40,
              height: 4,
              margin: const EdgeInsets.only(bottom: 16),
              decoration: BoxDecoration(
                color: const Color(0xFFD6C4CC),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          Text(
            titulo,
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 16),
          ...campos,
          if (error != null) ...[
            const SizedBox(height: 12),
            AvisoError(mensaje: error!),
          ],
          const SizedBox(height: 20),
          FilledButton(
            onPressed: enviando ? null : alGuardar,
            child: enviando
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : Text(textoBoton),
          ),
        ],
      ),
    );
  }
}

// --- Paso 3 · datos personales y tallas habituales -------------------------

class _FormularioDatos extends ConsumerStatefulWidget {
  const _FormularioDatos({required this.perfil});

  final Perfil perfil;

  @override
  ConsumerState<_FormularioDatos> createState() => _FormularioDatosState();
}

class _FormularioDatosState extends ConsumerState<_FormularioDatos> {
  final _formulario = GlobalKey<FormState>();
  late final _nombres = TextEditingController(text: widget.perfil.nombres);
  late final _apellidos = TextEditingController(text: widget.perfil.apellidos);
  late final _correo = TextEditingController(text: widget.perfil.correo);
  late final _documento = TextEditingController(
    text: widget.perfil.documento ?? '',
  );
  late final _telefono = TextEditingController(
    text: widget.perfil.telefono ?? '',
  );
  late final _superior = TextEditingController(
    text: widget.perfil.tallaSuperior ?? '',
  );
  late final _inferior = TextEditingController(
    text: widget.perfil.tallaInferior ?? '',
  );
  late final _calzado = TextEditingController(
    text: widget.perfil.tallaCalzado ?? '',
  );

  bool _enviando = false;
  String? _error;

  @override
  void dispose() {
    for (final campo in [
      _nombres,
      _apellidos,
      _correo,
      _documento,
      _telefono,
      _superior,
      _inferior,
      _calzado,
    ]) {
      campo.dispose();
    }
    super.dispose();
  }

  Future<void> _guardar() async {
    if (!_formulario.currentState!.validate()) return;
    setState(() {
      _enviando = true;
      _error = null;
    });
    try {
      await ref.read(perfilProvider.notifier).editar(
        EdicionPerfil(
          nombres: _nombres.text,
          apellidos: _apellidos.text,
          correo: _correo.text,
          documento: _documento.text,
          telefono: _telefono.text,
          tallaSuperior: _superior.text,
          tallaInferior: _inferior.text,
          tallaCalzado: _calzado.text,
        ),
      );
      if (mounted) Navigator.of(context).pop();
    } on ErrorApi catch (fallo) {
      // Excepción E2 del caso de uso: el correo nuevo ya pertenece a otra
      // cuenta. El mensaje lo redacta el backend.
      if (mounted) setState(() => _error = fallo.mensaje);
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  String? _obligatorio(String? valor, String campo) =>
      (valor ?? '').trim().isEmpty ? 'Ingrese $campo' : null;

  @override
  Widget build(BuildContext context) {
    return Form(
      key: _formulario,
      child: _Hoja(
        titulo: 'Editar mis datos',
        enviando: _enviando,
        error: _error,
        alGuardar: _guardar,
        textoBoton: 'Guardar cambios',
        campos: [
          TextFormField(
            controller: _nombres,
            decoration: const InputDecoration(labelText: 'Nombres'),
            textCapitalization: TextCapitalization.words,
            maxLength: 80,
            validator: (v) => _obligatorio(v, 'sus nombres'),
          ),
          TextFormField(
            controller: _apellidos,
            decoration: const InputDecoration(labelText: 'Apellidos'),
            textCapitalization: TextCapitalization.words,
            maxLength: 80,
            validator: (v) => _obligatorio(v, 'sus apellidos'),
          ),
          TextFormField(
            controller: _correo,
            decoration: const InputDecoration(labelText: 'Correo electrónico'),
            keyboardType: TextInputType.emailAddress,
            maxLength: 120,
            validator: validarCorreo,
          ),
          TextFormField(
            controller: _documento,
            decoration: const InputDecoration(
              labelText: 'Documento de identidad',
              helperText: 'Opcional. Vacíelo para borrarlo.',
            ),
            maxLength: 20,
          ),
          TextFormField(
            controller: _telefono,
            decoration: const InputDecoration(
              labelText: 'Teléfono',
              helperText: 'Opcional. Vacíelo para borrarlo.',
            ),
            keyboardType: TextInputType.phone,
            maxLength: 20,
          ),
          const SizedBox(height: 8),
          const Text(
            'Tallas habituales',
            style: TextStyle(fontWeight: FontWeight.w600),
          ),
          const Text(
            'Sirven para recomendarle prendas de su talla.',
            style: TextStyle(fontSize: 12, color: Color(0xFF6B5A62)),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: TextFormField(
                  controller: _superior,
                  decoration: const InputDecoration(labelText: 'Superior'),
                  maxLength: 10,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: TextFormField(
                  controller: _inferior,
                  decoration: const InputDecoration(labelText: 'Inferior'),
                  maxLength: 10,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: TextFormField(
                  controller: _calzado,
                  decoration: const InputDecoration(labelText: 'Calzado'),
                  maxLength: 10,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// --- Flujo alternativo 3a · nueva dirección de entrega ---------------------

class _FormularioDireccion extends ConsumerStatefulWidget {
  const _FormularioDireccion();

  @override
  ConsumerState<_FormularioDireccion> createState() =>
      _FormularioDireccionState();
}

class _FormularioDireccionState extends ConsumerState<_FormularioDireccion> {
  final _formulario = GlobalKey<FormState>();
  final _alias = TextEditingController();
  final _direccion = TextEditingController();
  final _referencia = TextEditingController();

  int? _ciudadId;
  bool _predeterminada = false;
  bool _enviando = false;
  String? _error;

  @override
  void dispose() {
    _alias.dispose();
    _direccion.dispose();
    _referencia.dispose();
    super.dispose();
  }

  Future<void> _guardar() async {
    if (!_formulario.currentState!.validate()) return;
    setState(() {
      _enviando = true;
      _error = null;
    });
    try {
      await ref.read(perfilProvider.notifier).agregarDireccion(
        NuevaDireccion(
          ciudadId: _ciudadId!,
          alias: _alias.text,
          direccion: _direccion.text,
          referencia: _referencia.text,
          predeterminada: _predeterminada,
        ),
      );
      if (mounted) Navigator.of(context).pop();
    } on ErrorApi catch (fallo) {
      if (mounted) setState(() => _error = fallo.mensaje);
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ciudades = ref.watch(ciudadesProvider);

    return Form(
      key: _formulario,
      child: _Hoja(
        titulo: 'Nueva dirección',
        enviando: _enviando,
        error: _error,
        alGuardar: _guardar,
        textoBoton: 'Agregar dirección',
        campos: [
          ciudades.when(
            loading: () => const Padding(
              padding: EdgeInsets.symmetric(vertical: 20),
              child: Center(child: CircularProgressIndicator()),
            ),
            error: (fallo, _) => AvisoError(
              mensaje: fallo is ErrorApi
                  ? fallo.mensaje
                  : 'No se pudieron cargar las ciudades.',
            ),
            data: (lista) => DropdownButtonFormField<int>(
              initialValue: _ciudadId,
              decoration: const InputDecoration(labelText: 'Ciudad'),
              items: [
                for (final ciudad in lista)
                  DropdownMenuItem(
                    value: ciudad.id,
                    child: Text('${ciudad.nombre} — ${ciudad.departamento}'),
                  ),
              ],
              onChanged: (valor) => setState(() => _ciudadId = valor),
              validator: (valor) =>
                  valor == null ? 'Elija una ciudad' : null,
            ),
          ),
          const SizedBox(height: 4),
          TextFormField(
            controller: _alias,
            decoration: const InputDecoration(
              labelText: 'Alias',
              hintText: 'Casa, trabajo…',
            ),
            maxLength: 40,
            validator: (v) =>
                (v ?? '').trim().isEmpty ? 'Ingrese un alias' : null,
          ),
          TextFormField(
            controller: _direccion,
            decoration: const InputDecoration(labelText: 'Dirección'),
            maxLength: 200,
            maxLines: 2,
            validator: (v) =>
                (v ?? '').trim().isEmpty ? 'Ingrese la dirección' : null,
          ),
          TextFormField(
            controller: _referencia,
            decoration: const InputDecoration(
              labelText: 'Referencia',
              helperText: 'Opcional. Un punto conocido cerca.',
            ),
            maxLength: 200,
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Usarla como predeterminada'),
            value: _predeterminada,
            onChanged: (valor) => setState(() => _predeterminada = valor),
          ),
        ],
      ),
    );
  }
}

// --- Flujo alternativo 3c · cambio de contraseña ---------------------------

class _FormularioContrasena extends ConsumerStatefulWidget {
  const _FormularioContrasena();

  @override
  ConsumerState<_FormularioContrasena> createState() =>
      _FormularioContrasenaState();
}

class _FormularioContrasenaState extends ConsumerState<_FormularioContrasena> {
  final _formulario = GlobalKey<FormState>();
  final _actual = TextEditingController();
  final _nueva = TextEditingController();
  final _repetida = TextEditingController();

  bool _enviando = false;
  bool _oculta = true;
  String? _error;

  @override
  void dispose() {
    _actual.dispose();
    _nueva.dispose();
    _repetida.dispose();
    super.dispose();
  }

  Future<void> _guardar() async {
    if (!_formulario.currentState!.validate()) return;
    setState(() {
      _enviando = true;
      _error = null;
    });
    try {
      await ref.read(perfilProvider.notifier).cambiarContrasena(
        CambioContrasena(
          actual: _actual.text,
          nueva: _nueva.text,
          repetida: _repetida.text,
        ),
      );
      if (!mounted) return;
      Navigator.of(context).pop();
      // El backend acaba de revocar todas las sesiones, esta incluida. Se
      // cierra la sesion aqui mismo en vez de esperar a que la proxima
      // peticion falle con 401 y saque al usuario sin explicarle por que.
      await ref.read(sesionProvider.notifier).cerrarPorCambioDeContrasena();
    } on ErrorApi catch (fallo) {
      // La contraseña actual incorrecta llega como 400 con su mensaje.
      if (mounted) setState(() => _error = fallo.mensaje);
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Form(
      key: _formulario,
      child: _Hoja(
        titulo: 'Cambiar contraseña',
        enviando: _enviando,
        error: _error,
        alGuardar: _guardar,
        textoBoton: 'Cambiar contraseña',
        campos: [
          TextFormField(
            controller: _actual,
            decoration: InputDecoration(
              labelText: 'Contraseña actual',
              suffixIcon: IconButton(
                tooltip: _oculta ? 'Mostrar contraseña' : 'Ocultar contraseña',
                icon: Icon(
                  _oculta ? Icons.visibility_outlined : Icons.visibility_off_outlined,
                ),
                onPressed: () => setState(() => _oculta = !_oculta),
              ),
            ),
            obscureText: _oculta,
            maxLength: 128,
            validator: (v) => (v ?? '').isEmpty
                ? 'Ingrese su contraseña actual'
                : null,
          ),
          TextFormField(
            controller: _nueva,
            decoration: const InputDecoration(
              labelText: 'Contraseña nueva',
              helperText: 'Al menos $contrasenaLongitudMinima caracteres, con letras y números',
            ),
            obscureText: _oculta,
            maxLength: 128,
            // Las mismas reglas que el backend, para avisar antes de gastar
            // una llamada de red. La validación de verdad es la del servidor.
            validator: (valor) {
              final texto = valor ?? '';
              if (texto.length < contrasenaLongitudMinima) {
                return 'Debe tener al menos $contrasenaLongitudMinima caracteres';
              }
              final tieneLetra = RegExp(r'[A-Za-z]').hasMatch(texto);
              final tieneDigito = RegExp(r'\d').hasMatch(texto);
              if (!tieneLetra || !tieneDigito) {
                return 'Debe incluir al menos una letra y un número';
              }
              return null;
            },
          ),
          TextFormField(
            controller: _repetida,
            decoration: const InputDecoration(
              labelText: 'Repetir la contraseña nueva',
            ),
            obscureText: _oculta,
            maxLength: 128,
            validator: (valor) => valor != _nueva.text
                ? 'Las contraseñas no coinciden'
                : null,
          ),
        ],
      ),
    );
  }
}
