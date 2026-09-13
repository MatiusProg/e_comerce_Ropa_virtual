/// CU-22 · Crear reserva de prendas --- pasos 2 a 7.
///
/// La pantalla **invierte el orden del formulario a proposito**: el servidor
/// recibe sucursal, franja y prendas, y aca se piden primero las prendas. La
/// pregunta del cliente es «¿dónde puedo probarme esto?», no «¿qué hay en la
/// sucursal Centro?». El porque completo esta en `estado_reservas.dart`, sobre
/// `ControlBorrador`.
///
/// **La prenda se elige en dos pasos: producto y despues variante.** Un
/// catalogo de sesenta productos con cinco tallas y cuatro colores son mil
/// doscientas variantes; una lista con eso no se puede usar en un telefono.
/// Mismo criterio que el remito de CU-13 y que el formulario de la web.
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/enrutado/router.dart';
import '../../core/tema.dart';
import '../../data/modelos/catalogo.dart';
import '../../data/modelos/reservas.dart';
import '../../data/repositorios/repositorio_reservas.dart';
import '../catalogo/estado_catalogo.dart';
import 'estado_reservas.dart';
import 'widgets_reservas.dart';

/// Las duraciones que ofrece el selector, dentro de lo que admite el servidor
/// (`DURACION_MINIMA_MINUTOS` .. `DURACION_MAXIMA_MINUTOS`).
const List<int> _duraciones = [15, 30, 45, 60, 90, 120];

/// Hasta cuando deja reservar el selector de dia.
///
/// Son los tres dias de `RESERVA_ANTICIPACION_MAXIMA_HORAS` por omision. Es una
/// **conveniencia del selector, no la regla**: la regla la aplica el servidor,
/// que puede estar configurado con otro valor, y el mensaje de E5 lo dice si
/// alguien llega igual.
const int _diasDeAnticipacion = 3;

class PantallaNuevaReserva extends ConsumerStatefulWidget {
  const PantallaNuevaReserva({super.key});

  @override
  ConsumerState<PantallaNuevaReserva> createState() =>
      _EstadoPantallaNuevaReserva();
}

class _EstadoPantallaNuevaReserva
    extends ConsumerState<PantallaNuevaReserva> {
  late DateTime _dia = DateTime.now().add(const Duration(days: 1));
  TimeOfDay _hora = const TimeOfDay(hour: 15, minute: 0);
  int _duracion = 60;

  bool _guardando = false;
  String? _error;

  @override
  Widget build(BuildContext context) {
    final borrador = ref.watch(borradorProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Nueva reserva'),
        actions: [
          if (!borrador.vacio)
            TextButton(
              onPressed: _guardando
                  ? null
                  : () => ref.read(borradorProvider.notifier).limpiar(),
              child: const Text(
                'Vaciar',
                style: TextStyle(color: Colors.white),
              ),
            ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 4, 20, 32),
        children: [
          // --- 1. Las prendas -------------------------------------------
          const RotuloSeccion('1 · Qué se quiere probar'),
          Card(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
              child: Column(
                children: [
                  if (borrador.vacio)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 14),
                      child: Text(
                        'Todavía no agregó ninguna prenda.',
                        style: TextStyle(color: Color(0xFF9A8A92)),
                      ),
                    )
                  else
                    for (final linea in borrador.lineas)
                      FilaPrenda(
                        producto: linea.producto,
                        sku: linea.sku,
                        talla: linea.talla,
                        color: linea.color,
                        cantidad: linea.cantidad,
                        rechazada: linea.rechazada,
                        alFinal: IconButton(
                          tooltip: 'Quitar',
                          icon: const Icon(Icons.close, size: 18),
                          color: const Color(0xFF9A8A92),
                          onPressed: _guardando
                              ? null
                              : () => ref
                                    .read(borradorProvider.notifier)
                                    .quitar(linea.varianteId),
                        ),
                      ),
                  const SizedBox(height: 4),
                  OutlinedButton.icon(
                    onPressed: _guardando || borrador.lleno
                        ? null
                        : _abrirSelectorDePrenda,
                    icon: const Icon(Icons.add, size: 20),
                    label: Text(
                      borrador.lleno
                          ? 'Máximo 10 prendas'
                          : 'Agregar una prenda',
                    ),
                    style: OutlinedButton.styleFrom(
                      minimumSize: const Size.fromHeight(46),
                      foregroundColor: ColoresVB.malvaOscuro,
                      side: const BorderSide(color: Color(0xFFE3D3DA)),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(radioChicoVB),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),

          // --- 2. La sucursal -------------------------------------------
          const RotuloSeccion('2 · Dónde se las prueba'),
          _SelectorDeSucursal(
            borrador: borrador,
            habilitado: !_guardando,
            alElegir: (id) =>
                ref.read(borradorProvider.notifier).elegirSucursal(id),
          ),

          // --- 3. La franja ---------------------------------------------
          const RotuloSeccion('3 · Cuándo pasa'),
          Card(
            child: Column(
              children: [
                ListTile(
                  enabled: !_guardando,
                  leading: const Icon(
                    Icons.calendar_today_outlined,
                    color: ColoresVB.malva,
                  ),
                  title: const Text('Día'),
                  subtitle: Text(diaLargo(_dia)),
                  trailing: const Icon(Icons.chevron_right, size: 20),
                  onTap: _elegirDia,
                ),
                const Divider(height: 1),
                ListTile(
                  enabled: !_guardando,
                  leading: const Icon(
                    Icons.access_time,
                    color: ColoresVB.malva,
                  ),
                  title: const Text('Hora de llegada'),
                  subtitle: Text(_hora.format(context)),
                  trailing: const Icon(Icons.chevron_right, size: 20),
                  onTap: _elegirHora,
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Cuánto tiempo necesita',
                        style: TextStyle(
                          fontSize: 13,
                          color: Color(0xFF6B5A62),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 8,
                        children: [
                          for (final minutos in _duraciones)
                            ChoiceChip(
                              label: Text(_rotuloDuracion(minutos)),
                              selected: _duracion == minutos,
                              onSelected: _guardando
                                  ? null
                                  : (_) =>
                                        setState(() => _duracion = minutos),
                              selectedColor: ColoresVB.rosaPalido,
                              labelStyle: TextStyle(
                                fontSize: 13,
                                fontWeight: _duracion == minutos
                                    ? FontWeight.w700
                                    : FontWeight.w400,
                                color: _duracion == minutos
                                    ? ColoresVB.malvaOscuro
                                    : const Color(0xFF5C4C55),
                              ),
                              side: const BorderSide(
                                color: Color(0xFFE3D3DA),
                              ),
                            ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      Text(
                        'Le apartamos el probador de ${_hora.format(context)} '
                        'a ${soloHora(_finDeFranja())}.',
                        style: const TextStyle(
                          fontSize: 12.5,
                          color: Color(0xFF9A8A92),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          if (_error != null) ...[
            const SizedBox(height: 18),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFFFBE3E3),
                borderRadius: BorderRadius.circular(radioChicoVB),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(
                    Icons.error_outline,
                    size: 20,
                    color: Color(0xFFA33A3A),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      _error!,
                      style: const TextStyle(
                        height: 1.4,
                        color: Color(0xFF8A2E2E),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],

          const SizedBox(height: 24),
          FilledButton(
            onPressed: _guardando || !borrador.hayPrendasYSucursal
                ? null
                : _confirmar,
            child: _guardando
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : Text(
                    borrador.vacio
                        ? 'Confirmar reserva'
                        : 'Reservar ${borrador.unidades} '
                              '${borrador.unidades == 1 ? "unidad" : "unidades"}',
                  ),
          ),
          const SizedBox(height: 10),
          const Text(
            'Apartamos las prendas en la sucursal hasta que termine su franja. '
            'Puede cancelar cuando quiera.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 12, color: Color(0xFF9A8A92)),
          ),
        ],
      ),
    );
  }

  String _rotuloDuracion(int minutos) =>
      minutos < 60 ? '$minutos min' : '${(minutos / 60).toStringAsFixed(minutos % 60 == 0 ? 0 : 1)} h';

  DateTime _inicioDeFranja() => DateTime(
    _dia.year,
    _dia.month,
    _dia.day,
    _hora.hour,
    _hora.minute,
  );

  DateTime _finDeFranja() =>
      _inicioDeFranja().add(Duration(minutes: _duracion));

  // --- Seleccion de prenda ------------------------------------------------

  Future<void> _abrirSelectorDePrenda() async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: ColoresVB.marfil,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(radioVB)),
      ),
      builder: (_) => const _SelectorDePrenda(),
    );
  }

  // --- Franja -------------------------------------------------------------

  Future<void> _elegirDia() async {
    final hoy = DateTime.now();
    final elegido = await showDatePicker(
      context: context,
      initialDate: _dia,
      firstDate: DateTime(hoy.year, hoy.month, hoy.day),
      lastDate: hoy.add(const Duration(days: _diasDeAnticipacion)),
      helpText: 'Elija el día',
    );
    if (elegido != null) setState(() => _dia = elegido);
  }

  Future<void> _elegirHora() async {
    final elegida = await showTimePicker(
      context: context,
      initialTime: _hora,
      helpText: 'Hora de llegada',
    );
    if (elegida != null) setState(() => _hora = elegida);
  }

  // --- Confirmacion -------------------------------------------------------

  Future<void> _confirmar() async {
    final borrador = ref.read(borradorProvider);
    if (!borrador.hayPrendasYSucursal) return;

    setState(() {
      _guardando = true;
      _error = null;
    });

    try {
      final reserva = await ref
          .read(repositorioReservasProvider)
          .crear(
            ReservaCrear(
              sucursalId: borrador.sucursalId!,
              // Con el desfase y la hora de pared, NO en UTC. Ver `conDesfase`.
              franjaInicio: conDesfase(_inicioDeFranja()),
              franjaFin: conDesfase(_finDeFranja()),
              lineas: borrador.lineas.map((l) => l.aLinea()).toList(),
            ),
          );

      ref.read(borradorProvider.notifier).limpiar();
      ref.invalidate(misReservasProvider(true));

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Reserva confirmada. Le apartamos ${reserva.unidades} '
            '${reserva.unidades == 1 ? "unidad" : "unidades"} '
            'en ${reserva.sucursal}.',
          ),
        ),
      );
      // `pushReplacement` y no `push`: el formulario ya no sirve --- su
      // borrador esta vacio ---, y volver atras tiene que llevar a la lista.
      context.pushReplacement(Rutas.reservaDetalle(reserva.id));
    } on ErrorReservas catch (fallo) {
      if (!mounted) return;
      setState(() => _error = fallo.mensaje);

      switch (fallo.tipo) {
        // E1: se señalan las prendas rechazadas en vez de invalidar la reserva
        // entera, que es justo lo que pide la excepcion.
        case TipoErrorReserva.lineasInvalidas:
          ref.read(borradorProvider.notifier).marcarRechazadas(fallo.variantes);
        // E9 / riesgo R5: perdimos la carrera por el stock. La disponibilidad
        // que mostramos ya no vale, asi que se vuelve a pedir en vez de dejar
        // al cliente reintentando contra un numero viejo.
        case TipoErrorReserva.sinStock:
          ref.read(borradorProvider.notifier).refrescarSucursales();
        case _:
          break;
      }
    } finally {
      if (mounted) setState(() => _guardando = false);
    }
  }
}

/// El selector de sucursal: **solo las que tienen todas las prendas**.
class _SelectorDeSucursal extends StatelessWidget {
  const _SelectorDeSucursal({
    required this.borrador,
    required this.habilitado,
    required this.alElegir,
  });

  final BorradorReserva borrador;
  final bool habilitado;
  final ValueChanged<int?> alElegir;

  @override
  Widget build(BuildContext context) {
    if (borrador.vacio) {
      return const _Nota(
        'Primero agregue las prendas: le mostramos solo las sucursales que '
        'las tienen todas.',
      );
    }
    if (borrador.buscandoSucursales) {
      return const _Nota('Buscando sucursales con existencia…');
    }
    if (borrador.sucursalesPosibles.isEmpty) {
      return const _Nota(
        'Ninguna sucursal tiene todas las prendas en la cantidad pedida. '
        'Pruebe quitando alguna o bajando la cantidad.',
        alarma: true,
      );
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            DropdownButtonFormField<int>(
              initialValue: borrador.sucursalId,
              isExpanded: true,
              decoration: const InputDecoration(labelText: 'Sucursal'),
              items: [
                for (final sucursal in borrador.sucursalesPosibles)
                  DropdownMenuItem(
                    value: sucursal.sucursalId,
                    child: Text(
                      '${sucursal.sucursalNombre} · ${sucursal.ciudadNombre}',
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
              ],
              onChanged: habilitado ? alElegir : null,
            ),
            const Padding(
              padding: EdgeInsets.only(top: 10, bottom: 8),
              child: Text(
                'Solo aparecen las sucursales donde hay existencia de todas '
                'las prendas que eligió.',
                style: TextStyle(fontSize: 12.5, color: Color(0xFF9A8A92)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Nota extends StatelessWidget {
  const _Nota(this.texto, {this.alarma = false});

  final String texto;
  final bool alarma;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: alarma ? const Color(0xFFFBF0D6) : Colors.white,
        border: Border.all(
          color: alarma ? const Color(0xFFEBD9A8) : const Color(0xFFEFE0E6),
        ),
        borderRadius: BorderRadius.circular(radioVB),
      ),
      child: Text(
        texto,
        style: TextStyle(
          height: 1.45,
          fontSize: 13.5,
          color: alarma ? const Color(0xFF8A6D12) : const Color(0xFF6B5A62),
        ),
      ),
    );
  }
}

// =========================================================================
// El selector de prenda --- paso 2 del caso de uso
// =========================================================================

/// Busca un producto, deja elegir talla y color, y agrega la linea.
///
/// Se consulta el catalogo de Karen (CU-17 y CU-18) a traves de su repositorio,
/// que es la costura **C2** --- P6 consume `variante_producto` de P3 --- y por
/// eso importa `RepositorioCatalogo` en vez de llamar a `/tienda` por su
/// cuenta.
class _SelectorDePrenda extends ConsumerStatefulWidget {
  const _SelectorDePrenda();

  @override
  ConsumerState<_SelectorDePrenda> createState() => _EstadoSelectorDePrenda();
}

class _EstadoSelectorDePrenda extends ConsumerState<_SelectorDePrenda> {
  final TextEditingController _busqueda = TextEditingController();
  Timer? _debounce;

  List<ProductoVitrina> _resultados = const [];
  bool _buscando = false;

  FichaPrenda? _ficha;
  bool _cargandoFicha = false;
  int? _tallaElegida;
  int? _colorElegido;
  int _cantidad = 1;

  String? _error;

  @override
  void dispose() {
    _debounce?.cancel();
    _busqueda.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      // El teclado tapa el campo de busqueda sin esto.
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SizedBox(
        height: MediaQuery.sizeOf(context).height * 0.85,
        child: Column(
          children: [
            const SizedBox(height: 10),
            Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: const Color(0xFFE3D3DA),
                borderRadius: BorderRadius.circular(999),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 14, 20, 10),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      _ficha == null ? 'Elija la prenda' : _ficha!.nombre,
                      style: const TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w600,
                        color: ColoresVB.malvaOscuro,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  if (_ficha != null)
                    TextButton(
                      onPressed: _volverABuscar,
                      child: const Text('Cambiar'),
                    ),
                ],
              ),
            ),
            Expanded(
              child: _ficha == null ? _paso1Buscar() : _paso2Variante(_ficha!),
            ),
          ],
        ),
      ),
    );
  }

  // --- Paso 1: buscar el producto -----------------------------------------

  Widget _paso1Buscar() {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: TextField(
            controller: _busqueda,
            autofocus: true,
            textInputAction: TextInputAction.search,
            decoration: InputDecoration(
              hintText: 'Buscar por nombre o código',
              prefixIcon: const Icon(Icons.search),
              suffixIcon: _buscando
                  ? const Padding(
                      padding: EdgeInsets.all(14),
                      child: SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                    )
                  : null,
            ),
            onChanged: _alEscribir,
          ),
        ),
        const SizedBox(height: 8),
        Expanded(
          child: _resultados.isEmpty
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(28),
                    child: Text(
                      _busqueda.text.trim().length < 2
                          ? 'Escriba al menos dos letras para buscar.'
                          : _buscando
                          ? ''
                          : 'No encontramos prendas con ese nombre.',
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Color(0xFF9A8A92)),
                    ),
                  ),
                )
              : ListView.builder(
                  itemCount: _resultados.length,
                  itemBuilder: (context, i) {
                    final producto = _resultados[i];
                    return ListTile(
                      title: Text(producto.nombre),
                      subtitle: Text(
                        '${producto.codigo} · ${producto.precioRotulado}',
                        style: const TextStyle(fontSize: 12.5),
                      ),
                      trailing: const Icon(Icons.chevron_right, size: 20),
                      onTap: () => _elegirProducto(producto),
                    );
                  },
                ),
        ),
      ],
    );
  }

  /// 300 ms, igual que la web. Sin esto se dispara una consulta por tecla.
  void _alEscribir(String texto) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 300), () {
      _buscar(texto);
    });
  }

  Future<void> _buscar(String texto) async {
    final limpio = texto.trim();
    if (limpio.length < 2) {
      setState(() {
        _resultados = const [];
        _buscando = false;
      });
      return;
    }

    setState(() => _buscando = true);
    try {
      final pagina = await ref
          .read(repositorioCatalogoProvider)
          .listar(ConsultaVitrina(busqueda: limpio, tamano: 20));
      if (!mounted) return;
      setState(() => _resultados = pagina.items);
    } catch (_) {
      if (!mounted) return;
      setState(() => _resultados = const []);
    } finally {
      if (mounted) setState(() => _buscando = false);
    }
  }

  // --- Paso 2: talla, color y cantidad ------------------------------------

  Future<void> _elegirProducto(ProductoVitrina producto) async {
    setState(() {
      _cargandoFicha = true;
      _error = null;
    });
    try {
      final ficha = await ref
          .read(repositorioCatalogoProvider)
          .obtenerFicha(producto.id);
      if (!mounted) return;
      setState(() {
        _ficha = ficha;
        _tallaElegida = null;
        _colorElegido = null;
        _cantidad = 1;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _error = 'No se pudo abrir esa prenda.');
    } finally {
      if (mounted) setState(() => _cargandoFicha = false);
    }
  }

  void _volverABuscar() {
    setState(() {
      _ficha = null;
      _tallaElegida = null;
      _colorElegido = null;
      _error = null;
    });
  }

  Widget _paso2Variante(FichaPrenda prenda) {
    if (_cargandoFicha) {
      return const Center(child: CircularProgressIndicator());
    }

    final variante = prenda.varianteDe(_tallaElegida, _colorElegido);
    final tallasOfrecidas = prenda.tallasDeColor(_colorElegido);
    final coloresOfrecidos = prenda.coloresDeTalla(_tallaElegida);

    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
      children: [
        const RotuloSeccion('Talla'),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final talla in prenda.tallas)
              ChoiceChip(
                label: Text(talla.codigo),
                selected: _tallaElegida == talla.id,
                // Las combinaciones que no existen se deshabilitan en vez de
                // ocultarse: que exista S negra y M roja pero no S roja es
                // informacion util, y esconder la talla la haria parecer
                // inexistente.
                onSelected: tallasOfrecidas.contains(talla)
                    ? (_) => _elegirTalla(prenda, talla.id)
                    : null,
                selectedColor: ColoresVB.rosaPalido,
                side: const BorderSide(color: Color(0xFFE3D3DA)),
              ),
          ],
        ),
        const RotuloSeccion('Color'),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final color in prenda.colores)
              ChoiceChip(
                avatar: CircleAvatar(
                  radius: 8,
                  backgroundColor: Color(color.valorArgb),
                ),
                label: Text(color.nombre),
                selected: _colorElegido == color.id,
                onSelected: coloresOfrecidos.contains(color)
                    ? (_) => _elegirColor(prenda, color.id)
                    : null,
                selectedColor: ColoresVB.rosaPalido,
                side: const BorderSide(color: Color(0xFFE3D3DA)),
              ),
          ],
        ),

        const RotuloSeccion('Cantidad'),
        Row(
          children: [
            IconButton.outlined(
              onPressed: _cantidad > 1
                  ? () => setState(() => _cantidad--)
                  : null,
              icon: const Icon(Icons.remove),
            ),
            SizedBox(
              width: 56,
              child: Text(
                '$_cantidad',
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            IconButton.outlined(
              // El tope de 10 es el del esquema (`cantidad: int = Field(le=10)`).
              onPressed: _cantidad < 10
                  ? () => setState(() => _cantidad++)
                  : null,
              icon: const Icon(Icons.add),
            ),
            const Spacer(),
            if (variante != null)
              Text(
                'Bs ${variante.precio}',
                style: const TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.w600,
                  color: ColoresVB.malvaOscuro,
                ),
              ),
          ],
        ),

        if (_error != null) ...[
          const SizedBox(height: 16),
          Text(
            _error!,
            style: const TextStyle(color: Color(0xFFA33A3A), height: 1.4),
          ),
        ],

        const SizedBox(height: 22),
        FilledButton(
          onPressed: variante == null ? null : () => _agregar(prenda, variante),
          child: Text(
            variante == null
                ? 'Elija talla y color'
                : 'Agregar a la reserva',
          ),
        ),
      ],
    );
  }

  void _elegirTalla(FichaPrenda prenda, int tallaId) {
    setState(() {
      _tallaElegida = _tallaElegida == tallaId ? null : tallaId;
      // Si el color elegido no existe en la talla nueva, se suelta: dejarlo
      // mostraria una combinacion inexistente como si fuera valida.
      if (_colorElegido != null &&
          !prenda.coloresDeTalla(_tallaElegida).any(
            (c) => c.id == _colorElegido,
          )) {
        _colorElegido = null;
      }
    });
  }

  void _elegirColor(FichaPrenda prenda, int colorId) {
    setState(() {
      _colorElegido = _colorElegido == colorId ? null : colorId;
      if (_tallaElegida != null &&
          !prenda.tallasDeColor(_colorElegido).any(
            (t) => t.id == _tallaElegida,
          )) {
        _tallaElegida = null;
      }
    });
  }

  void _agregar(FichaPrenda prenda, VariantePrenda variante) {
    final problema = ref
        .read(borradorProvider.notifier)
        .agregar(prenda: prenda, variante: variante, cantidad: _cantidad);

    if (problema != null) {
      setState(() => _error = problema);
      return;
    }
    Navigator.of(context).pop();
  }
}
