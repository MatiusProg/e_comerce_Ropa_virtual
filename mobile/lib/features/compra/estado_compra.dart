/// Estado de la compra del cliente (CU-26 y CU-27).
///
/// Sigue el patron de `estado_reservas.dart`: los proveedores arriba, el
/// control abajo. Ninguna pantalla construye un repositorio ni guarda
/// resultados en un `State`; el estado vive aca y las pantallas lo observan.
///
/// EL CARRITO ES UN NOTIFIER Y NO UN FutureProvider
/// -------------------------------------------------
/// Las reservas se leen con `FutureProvider` porque cada pantalla pide lo suyo
/// y nadie mas lo mira. El carrito no: lo miran la burbuja del icono del
/// catalogo, la ficha del producto y la pantalla del carrito, **a la vez**, y
/// cambia desde cualquiera de las tres.
///
/// Con `FutureProvider` cada una tendria que invalidarlo y volver a pedirlo
/// despues de cada cambio --- un viaje extra por operacion --- o se
/// desincronizarian. Con un `Notifier` el estado es uno solo: los cinco
/// endpoints devuelven el carrito entero a proposito (decision de CU-26), asi
/// que cada operacion ya trae el estado nuevo y actualizarlo es una asignacion.
library;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/modelos/compra.dart';
import '../../data/repositorios/repositorio_compra.dart';
import '../auth/estado_sesion.dart';

// --- Proveedores ------------------------------------------------------------

final repositorioCompraProvider = Provider<RepositorioCompra>((ref) {
  return RepositorioCompra(ref.watch(clienteApiProvider));
});

/// El carrito del cliente, compartido por todas las pantallas que lo miran.
final carritoProvider = AsyncNotifierProvider<ControlCarrito, Carrito>(
  ControlCarrito.new,
);

/// Las opciones del pedido: carrito, sucursales que abastecen y direcciones.
///
/// `FutureProvider` y no `Notifier` porque, al reves que el carrito, esto lo
/// mira una sola pantalla y no cambia solo: se refresca invalidandolo.
final opcionesDePedidoProvider = FutureProvider<OpcionesDePedido>((ref) async {
  // Depende del carrito a proposito: si el cliente vuelve atras y saca una
  // prenda, las sucursales que abastecen cambian, y esta pantalla tiene que
  // recalcularse sola en vez de mostrar una lista vieja.
  ref.watch(carritoProvider);
  return ref.watch(repositorioCompraProvider).opciones();
});

/// La ficha de un pedido propio, por codigo.
///
/// Es lo que consulta la pantalla de retorno del pago. **No se cachea entre
/// consultas**: el estado lo mueve el webhook de CU-28 por fuera de la app, asi
/// que la pantalla lo vuelve a pedir cada vez que el cliente refresca. Es D5 en
/// la practica --- la verdad esta en la base, no en esta pantalla.
final pedidoProvider = FutureProvider.family<Pedido, String>((ref, codigo) {
  return ref.watch(repositorioCompraProvider).obtener(codigo);
});

// --- El carrito -------------------------------------------------------------

class ControlCarrito extends AsyncNotifier<Carrito> {
  RepositorioCompra get _repositorio => ref.read(repositorioCompraProvider);

  @override
  Future<Carrito> build() => _repositorio.verCarrito();

  /// Agrega una prenda. **SUMA** a lo que ya hubiera de esa variante.
  ///
  /// Devuelve `null` si se agrego, o el mensaje del servidor si no. No lanza:
  /// que una prenda ya no se ofrezca no es un fallo del sistema, es algo que el
  /// cliente tiene que leer.
  Future<String?> agregar({required int varianteId, int cantidad = 1}) {
    return _operar(() => _repositorio.agregar(
      varianteId: varianteId,
      cantidad: cantidad,
    ));
  }

  /// Fija la cantidad de una linea. **NO suma.**
  Future<String?> fijarCantidad({
    required int varianteId,
    required int cantidad,
  }) {
    return _operar(() => _repositorio.fijarCantidad(
      varianteId: varianteId,
      cantidad: cantidad,
    ));
  }

  Future<String?> quitar(int varianteId) {
    return _operar(() => _repositorio.quitar(varianteId));
  }

  Future<String?> vaciar() {
    return _operar(_repositorio.vaciar);
  }

  /// Vuelve a pedir el carrito al servidor.
  ///
  /// Hace falta porque los precios se leen en vivo: el carrito que el cliente
  /// dejo abierto anoche puede tener otro total hoy.
  Future<void> refrescar() async {
    // Sin marcar `loading`: la pantalla del carrito refresca tirando hacia
    // abajo, y ahi el indicador de `RefreshIndicator` ya dice que algo esta
    // pasando. Vaciar el estado ademas haria parpadear la lista.
    state = await AsyncValue.guard(_repositorio.verCarrito);
  }

  /// Corre una operacion y deja el carrito que devuelve.
  ///
  /// NO pone el estado en `loading` mientras tanto: las operaciones del carrito
  /// son de un toque --- subir una unidad, quitar una linea --- y vaciar la
  /// lista para volver a pintarla medio segundo despues hace saltar la pantalla
  /// bajo el dedo. La pantalla muestra el progreso en el propio boton.
  Future<String?> _operar(Future<Carrito> Function() accion) async {
    try {
      state = AsyncValue.data(await accion());
      return null;
    } on ErrorCompra catch (fallo) {
      // El carrito anterior se conserva: un fallo al quitar una linea no
      // deberia dejar la pantalla en blanco.
      return fallo.mensaje;
    }
  }
}
