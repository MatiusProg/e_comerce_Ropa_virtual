/// CU-21 · Cargar las medidas del cuerpo.
///
/// PARA QUE SIRVEN
/// ---------------
/// Con ellas el vestidor puede hacer dos cosas que antes no podía: dibujar
/// cada talla del tamaño que de verdad tiene ---hasta el 18/09 la XS y la XXL
/// se veían idénticas en pantalla--- y decir cuál le corresponde al cliente.
///
/// POR QUÉ EL FORMULARIO EXPLICA CÓMO MEDIRSE
/// -------------------------------------------
/// Porque es la parte que se hace mal. Una cintura medida sobre la cadera, o
/// un busto medido por encima de la ropa de invierno, entran perfectamente en
/// el rango que valida el servidor y hacen que el probador recomiende mal sin
/// que nada avise. El texto de ayuda no es adorno: es la validación que ningún
/// CHECK puede hacer.
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/repositorios/repositorio_medidas.dart';
import '../auth/estado_sesion.dart';

class PantallaMedidas extends ConsumerStatefulWidget {
  const PantallaMedidas({super.key});

  @override
  ConsumerState<PantallaMedidas> createState() => _PantallaMedidasState();
}

class _PantallaMedidasState extends ConsumerState<PantallaMedidas> {
  final _formulario = GlobalKey<FormState>();
  final _busto = TextEditingController();
  final _cintura = TextEditingController();
  final _cadera = TextEditingController();
  final _altura = TextEditingController();

  bool _cargando = true;
  bool _guardando = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _traer();
  }

  @override
  void dispose() {
    _busto.dispose();
    _cintura.dispose();
    _cadera.dispose();
    _altura.dispose();
    super.dispose();
  }

  Future<void> _traer() async {
    try {
      final medidas = await RepositorioMedidas(
        ref.read(clienteApiProvider),
      ).mias();
      if (!mounted) return;
      setState(() {
        // `null` es el estado normal de quien nunca las cargó, no un error:
        // el formulario simplemente queda vacío.
        if (medidas != null) {
          _busto.text = _texto(medidas.bustoCm);
          _cintura.text = _texto(medidas.cinturaCm);
          _cadera.text = _texto(medidas.caderaCm);
          _altura.text = medidas.alturaCm == null
              ? ''
              : _texto(medidas.alturaCm!);
        }
        _cargando = false;
      });
    } catch (fallo) {
      if (!mounted) return;
      setState(() {
        _error = '$fallo';
        _cargando = false;
      });
    }
  }

  /// 92.0 se muestra como «92»: el decimal sobra salvo que lo tenga.
  static String _texto(double valor) =>
      valor == valor.roundToDouble() ? '${valor.round()}' : '$valor';

  Future<void> _guardar() async {
    if (!_formulario.currentState!.validate()) return;
    setState(() {
      _guardando = true;
      _error = null;
    });
    try {
      await RepositorioMedidas(ref.read(clienteApiProvider)).guardar(
        MedidasCuerpo(
          bustoCm: double.parse(_busto.text.replaceAll(',', '.')),
          cinturaCm: double.parse(_cintura.text.replaceAll(',', '.')),
          caderaCm: double.parse(_cadera.text.replaceAll(',', '.')),
          alturaCm: _altura.text.trim().isEmpty
              ? null
              : double.parse(_altura.text.replaceAll(',', '.')),
        ),
      );
      if (!mounted) return;
      Navigator.of(context).pop(true);
    } catch (fallo) {
      if (!mounted) return;
      setState(() {
        _error = '$fallo';
        _guardando = false;
      });
    }
  }

  /// Valida en el teléfono los MISMOS rangos que la tabla.
  ///
  /// No es desconfianza del servidor: es que el cliente vea el error al lado
  /// del campo en vez de recibir un 422 después de tocar Guardar.
  String? _validar(String? valor, String nombre, double min, double max,
      {bool obligatorio = true}) {
    final texto = (valor ?? '').trim().replaceAll(',', '.');
    if (texto.isEmpty) {
      return obligatorio ? 'Falta $nombre' : null;
    }
    final numero = double.tryParse(texto);
    if (numero == null) return 'Escribí solo números';
    if (numero < min || numero > max) {
      return 'Entre ${min.round()} y ${max.round()} cm';
    }
    return null;
  }

  Widget _campo(
    TextEditingController control,
    String etiqueta,
    String ayuda,
    double min,
    double max, {
    bool obligatorio = true,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 18),
      child: TextFormField(
        controller: control,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        inputFormatters: [
          FilteringTextInputFormatter.allow(RegExp(r'[0-9.,]')),
        ],
        decoration: InputDecoration(
          labelText: etiqueta,
          helperText: ayuda,
          helperMaxLines: 3,
          suffixText: 'cm',
          border: const OutlineInputBorder(),
        ),
        validator: (v) =>
            _validar(v, etiqueta.toLowerCase(), min, max,
                obligatorio: obligatorio),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Mis medidas')),
      body: _cargando
          ? const Center(child: CircularProgressIndicator())
          : Form(
              key: _formulario,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  const Text(
                    'Con tus medidas el vestidor dibuja cada talla del tamaño '
                    'que de verdad tiene, y te dice cuál te va.',
                    style: TextStyle(fontSize: 14),
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    'Medite con ropa liviana y sin apretar la cinta.',
                    style: TextStyle(fontSize: 12.5, color: Colors.black54),
                  ),
                  const SizedBox(height: 20),
                  _campo(_busto, 'Busto',
                      'Por la parte más saliente del busto, con la cinta '
                      'horizontal y pasando por debajo de las axilas.',
                      50, 200),
                  _campo(_cintura, 'Cintura',
                      'Por la parte más angosta del tronco, a la altura del '
                      'ombligo. No es donde se apoya el pantalón.',
                      40, 200),
                  _campo(_cadera, 'Cadera',
                      'Por la parte más ancha, unos 20 cm debajo de la '
                      'cintura.',
                      50, 200),
                  _campo(_altura, 'Altura', 'Opcional. Sirve para el largo de '
                      'vestidos y pantalones.', 100, 230,
                      obligatorio: false),
                  if (_error != null) ...[
                    Text(
                      _error!,
                      style: const TextStyle(color: Color(0xFFB3261E)),
                    ),
                    const SizedBox(height: 12),
                  ],
                  FilledButton(
                    onPressed: _guardando ? null : _guardar,
                    child: Text(_guardando ? 'Guardando…' : 'Guardar'),
                  ),
                ],
              ),
            ),
    );
  }
}
