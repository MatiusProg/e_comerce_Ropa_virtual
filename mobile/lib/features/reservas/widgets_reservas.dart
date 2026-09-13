/// Piezas compartidas por las tres pantallas de reservas.
///
/// Viven en su propio archivo y no dentro de una pantalla porque las usan las
/// tres: si el chip de estado se declarara en «Mis reservas» y lo importara el
/// detalle, el dia que se toque una pantalla se estaria tocando la otra.
library;

import 'package:flutter/material.dart';

import '../../core/tema.dart';
import '../../data/modelos/reservas.dart';

/// Los colores de cada estado.
///
/// El estado es lo primero que el cliente mira, asi que se distingue por color
/// ademas de por texto --- pero los cinco se leen igual en blanco y negro,
/// porque el color solo acompaña al rotulo y nunca lo reemplaza.
({Color fondo, Color texto}) coloresDeEstado(EstadoReserva estado) {
  return switch (estado) {
    // Las dos vivas, en la paleta de la marca: son las que piden atencion.
    EstadoReserva.pendiente => (
      fondo: ColoresVB.rosaPalido,
      texto: ColoresVB.malvaOscuro,
    ),
    EstadoReserva.preparada => (
      fondo: Color(0xFFFBF0D6),
      texto: Color(0xFF8A6D12),
    ),
    // Cerrada y bien: la unica en verde.
    EstadoReserva.atendida => (
      fondo: Color(0xFFDFF3E6),
      texto: Color(0xFF2A6B43),
    ),
    // Cerradas sin prueba. En gris y no en rojo: no son un error, son el curso
    // normal de las cosas y pintarlas de alarma solo asustaria al cliente.
    EstadoReserva.cancelada => (
      fondo: Color(0xFFEFEAEC),
      texto: Color(0xFF6B5A62),
    ),
    EstadoReserva.expirada => (
      fondo: Color(0xFFEFEAEC),
      texto: Color(0xFF6B5A62),
    ),
  };
}

class ChipEstadoReserva extends StatelessWidget {
  const ChipEstadoReserva(this.estado, {super.key});

  final EstadoReserva estado;

  @override
  Widget build(BuildContext context) {
    final paleta = coloresDeEstado(estado);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: paleta.fondo,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        estado.rotulo,
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.3,
          color: paleta.texto,
        ),
      ),
    );
  }
}

/// Un aviso a pantalla completa, para los fallos y para las listas vacias.
class AvisoReservas extends StatelessWidget {
  const AvisoReservas({
    required this.mensaje,
    this.icono = Icons.info_outline,
    this.accion,
    super.key,
  });

  final String mensaje;
  final IconData icono;
  final Widget? accion;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icono, size: 44, color: ColoresVB.malvaClaro),
            const SizedBox(height: 14),
            Text(
              mensaje,
              textAlign: TextAlign.center,
              style: const TextStyle(height: 1.5, color: Color(0xFF6B5A62)),
            ),
            if (accion != null) ...[const SizedBox(height: 20), accion!],
          ],
        ),
      ),
    );
  }
}

/// El rotulo de una seccion. El mismo de la ficha del catalogo.
class RotuloSeccion extends StatelessWidget {
  const RotuloSeccion(this.texto, {super.key});

  final String texto;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 18, bottom: 8),
      child: Text(
        texto.toUpperCase(),
        style: const TextStyle(
          fontSize: 11,
          letterSpacing: 0.8,
          fontWeight: FontWeight.w700,
          color: Color(0xFF9A8A92),
        ),
      ),
    );
  }
}

/// Una prenda de la reserva: el SKU arriba y la combinacion abajo.
///
/// La misma fila sirve para el borrador de CU-22 y para el detalle de CU-23,
/// que muestran lo mismo con distinto final --- alli el boton de quitar, aca el
/// resultado de la prueba.
class FilaPrenda extends StatelessWidget {
  const FilaPrenda({
    required this.producto,
    required this.sku,
    required this.talla,
    required this.color,
    required this.cantidad,
    this.rechazada = false,
    this.alFinal,
    super.key,
  });

  final String producto;
  final String sku;
  final String talla;
  final String color;
  final int cantidad;

  /// E1: el servidor dijo que esta prenda no se puede reservar.
  final bool rechazada;

  final Widget? alFinal;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 34,
            height: 34,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: rechazada ? const Color(0xFFFBE3E3) : ColoresVB.rosaPalido,
              borderRadius: BorderRadius.circular(radioChicoVB),
            ),
            child: Text(
              '×$cantidad',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w700,
                color: rechazada
                    ? const Color(0xFFA33A3A)
                    : ColoresVB.malvaOscuro,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  producto,
                  style: const TextStyle(
                    fontWeight: FontWeight.w600,
                    height: 1.3,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  '$talla · $color',
                  style: const TextStyle(
                    fontSize: 13,
                    color: Color(0xFF6B5A62),
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  sku,
                  style: const TextStyle(
                    fontFamily: 'monospace',
                    fontSize: 11,
                    color: Color(0xFF9A8A92),
                  ),
                ),
                if (rechazada) ...[
                  const SizedBox(height: 4),
                  const Text(
                    'Esta prenda ya no se puede reservar.',
                    style: TextStyle(fontSize: 12, color: Color(0xFFA33A3A)),
                  ),
                ],
              ],
            ),
          ),
          if (alFinal != null) alFinal!,
        ],
      ),
    );
  }
}
