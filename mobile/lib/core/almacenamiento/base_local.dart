/// SQLite del telefono (2do parcial, CU-13, CU-15, CU-17, CU-18 y CU-21).
///
/// Lo que pide el enunciado (§6.3) para trabajar sin red, en tablas y no en
/// un solo JSON: las sucursales, las prendas con su saldo por sucursal y las
/// operaciones pendientes con su estado. Sobrevive a cerrar la app (RF-17).
///
/// No guarda datos de pago ni contraseñas (RNF10): el token sigue en el
/// almacen cifrado (`almacen_seguro.dart`).
library;

import 'dart:convert';

import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';

import '../../data/modelos/inventario_offline.dart';
import '../../data/modelos/offline.dart';

class BaseLocal {
  BaseLocal._();

  static final BaseLocal instancia = BaseLocal._();

  /// 2: la vitrina con fotos (producto, categoria e imagen de cada prenda).
  /// 3: el inventario del encargado (CU-21): sus prendas y los proveedores.
  static const _version = 3;
  Database? _db;

  Future<Database> get _base async {
    return _db ??= await openDatabase(
      p.join(await getDatabasesPath(), 'violet_offline.db'),
      version: _version,
      onCreate: (db, _) async {
        await db.execute('''
          CREATE TABLE metadato (
            clave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
          )''');
        await db.execute('''
          CREATE TABLE sucursal_local (
            id INTEGER PRIMARY KEY,
            nombre TEXT NOT NULL,
            apertura TEXT NOT NULL,
            cierre TEXT NOT NULL
          )''');
        await db.execute('''
          CREATE TABLE prenda_local (
            variante_id INTEGER PRIMARY KEY,
            sku TEXT NOT NULL,
            producto_id INTEGER NOT NULL,
            producto TEXT NOT NULL,
            categoria TEXT NOT NULL,
            imagen_url TEXT,
            talla TEXT NOT NULL,
            color TEXT NOT NULL,
            precio TEXT NOT NULL
          )''');
        await db.execute('''
          CREATE TABLE disponible_local (
            variante_id INTEGER NOT NULL,
            sucursal_id INTEGER NOT NULL,
            disponible INTEGER NOT NULL,
            PRIMARY KEY (variante_id, sucursal_id)
          )''');
        await db.execute('''
          CREATE TABLE operacion_pendiente (
            uuid TEXT PRIMARY KEY,
            estado TEXT NOT NULL,
            cuerpo TEXT NOT NULL,
            resumen TEXT NOT NULL,
            creada_en TEXT NOT NULL,
            intentos INTEGER NOT NULL DEFAULT 0,
            motivo TEXT,
            reserva_id INTEGER
          )''');
        await db.execute('''
          CREATE TABLE prenda_inventario (
            variante_id INTEGER PRIMARY KEY,
            sku TEXT NOT NULL,
            producto TEXT NOT NULL,
            talla TEXT NOT NULL,
            color TEXT NOT NULL,
            disponible INTEGER NOT NULL,
            reservada INTEGER NOT NULL,
            stock_minimo INTEGER NOT NULL
          )''');
        await db.execute('''
          CREATE TABLE proveedor_local (
            id INTEGER PRIMARY KEY,
            razon_social TEXT NOT NULL
          )''');
      },
      onUpgrade: (db, anterior, _) async {
        if (anterior < 2) {
          // El paquete viejo no trae las fotos: se descarta y el cliente lo
          // vuelve a preparar. La cola NO se toca (RNF06).
          await db.execute('DROP TABLE prenda_local');
          await db.execute('''
            CREATE TABLE prenda_local (
              variante_id INTEGER PRIMARY KEY,
              sku TEXT NOT NULL,
              producto_id INTEGER NOT NULL,
              producto TEXT NOT NULL,
              categoria TEXT NOT NULL,
              imagen_url TEXT,
              talla TEXT NOT NULL,
              color TEXT NOT NULL,
              precio TEXT NOT NULL
            )''');
          await db.delete('disponible_local');
          await db.delete('sucursal_local');
          await db.delete('metadato');
        }
        if (anterior < 3) {
          await db.execute('''
          CREATE TABLE prenda_inventario (
            variante_id INTEGER PRIMARY KEY,
            sku TEXT NOT NULL,
            producto TEXT NOT NULL,
            talla TEXT NOT NULL,
            color TEXT NOT NULL,
            disponible INTEGER NOT NULL,
            reservada INTEGER NOT NULL,
            stock_minimo INTEGER NOT NULL
          )''');
          await db.execute('''
          CREATE TABLE proveedor_local (
            id INTEGER PRIMARY KEY,
            razon_social TEXT NOT NULL
          )''');
        }
      },
    );
  }

  // --- El paquete (CU-13) -------------------------------------------------

  /// Reemplaza el paquete entero en una sola transaccion: o queda el nuevo
  /// completo o sigue el anterior, nunca una mezcla.
  Future<void> guardarPaquete(PaqueteCliente paquete) async {
    final db = await _base;
    await db.transaction((tx) async {
      await tx.delete('sucursal_local');
      await tx.delete('prenda_local');
      await tx.delete('disponible_local');
      final lote = tx.batch();
      for (final s in paquete.sucursales) {
        lote.insert('sucursal_local', {
          'id': s.id,
          'nombre': s.nombre,
          'apertura': s.apertura,
          'cierre': s.cierre,
        });
      }
      for (final prenda in paquete.prendas) {
        lote.insert('prenda_local', {
          'variante_id': prenda.varianteId,
          'sku': prenda.sku,
          'producto_id': prenda.productoId,
          'producto': prenda.producto,
          'categoria': prenda.categoria,
          'imagen_url': prenda.imagenUrl,
          'talla': prenda.talla,
          'color': prenda.color,
          'precio': prenda.precio,
        });
        prenda.disponiblePorSucursal.forEach((sucursal, disponible) {
          lote.insert('disponible_local', {
            'variante_id': prenda.varianteId,
            'sucursal_id': sucursal,
            'disponible': disponible,
          });
        });
      }
      lote.insert(
          'metadato',
          {
            'clave': 'generado_en',
            'valor': paquete.generadoEn.toIso8601String(),
          },
          conflictAlgorithm: ConflictAlgorithm.replace);
      lote.insert(
          'metadato',
          {
            'clave': 'vigente_hasta',
            'valor': paquete.vigenteHasta.toIso8601String(),
          },
          conflictAlgorithm: ConflictAlgorithm.replace);
      await lote.commit(noResult: true);
    });
  }

  Future<PaqueteCliente?> leerPaquete() async {
    final db = await _base;
    final meta = {
      for (final f in await db.query('metadato'))
        f['clave'] as String: f['valor'] as String,
    };
    if (!meta.containsKey('generado_en')) return null;

    final disponibles = <int, Map<int, int>>{};
    for (final f in await db.query('disponible_local')) {
      disponibles.putIfAbsent(
              f['variante_id'] as int, () => {})[f['sucursal_id'] as int] =
          f['disponible'] as int;
    }
    return PaqueteCliente(
      generadoEn: DateTime.parse(meta['generado_en']!),
      vigenteHasta: DateTime.parse(meta['vigente_hasta']!),
      sucursales: [
        for (final f in await db.query('sucursal_local', orderBy: 'nombre'))
          SucursalOffline(
            id: f['id'] as int,
            nombre: f['nombre'] as String,
            apertura: f['apertura'] as String,
            cierre: f['cierre'] as String,
          ),
      ],
      prendas: [
        for (final f in await db.query(
          'prenda_local',
          orderBy: 'producto, talla, color',
        ))
          PrendaOffline(
            varianteId: f['variante_id'] as int,
            sku: f['sku'] as String,
            productoId: f['producto_id'] as int,
            producto: f['producto'] as String,
            categoria: f['categoria'] as String,
            imagenUrl: f['imagen_url'] as String?,
            talla: f['talla'] as String,
            color: f['color'] as String,
            precio: f['precio'] as String,
            disponiblePorSucursal: disponibles[f['variante_id'] as int] ?? {},
          ),
      ],
    );
  }

  /// Lo apartado sin red ya no esta disponible en el telefono: si no se
  /// descontara, el cliente podria reservar dos veces la misma unidad.
  Future<void> descontar(int sucursalId, Map<int, int> cantidades) async {
    final db = await _base;
    await db.transaction((tx) async {
      for (final entrada in cantidades.entries) {
        await tx.rawUpdate(
          'UPDATE disponible_local SET disponible = MAX(0, disponible - ?) '
          'WHERE variante_id = ? AND sucursal_id = ?',
          [entrada.value, entrada.key, sucursalId],
        );
      }
    });
  }

  // --- El inventario del encargado (CU-21) --------------------------------

  /// Reemplaza el paquete de inventario en una sola transaccion. Las claves
  /// del metadato llevan `inv_` para no pisar el paquete del cliente.
  Future<void> guardarPaqueteInventario(PaqueteInventario paquete) async {
    final db = await _base;
    await db.transaction((tx) async {
      await tx.delete('prenda_inventario');
      await tx.delete('proveedor_local');
      final lote = tx.batch();
      for (final p in paquete.prendas) {
        lote.insert('prenda_inventario', {
          'variante_id': p.varianteId,
          'sku': p.sku,
          'producto': p.producto,
          'talla': p.talla,
          'color': p.color,
          'disponible': p.disponible,
          'reservada': p.reservada,
          'stock_minimo': p.stockMinimo,
        });
      }
      for (final p in paquete.proveedores) {
        lote.insert('proveedor_local', {'id': p.id, 'razon_social': p.razonSocial});
      }
      final meta = {
        'inv_generado_en': paquete.generadoEn.toIso8601String(),
        'inv_vigente_hasta': paquete.vigenteHasta.toIso8601String(),
        'inv_sucursal_id': '${paquete.sucursalId}',
        'inv_sucursal': paquete.sucursal,
      };
      meta.forEach((clave, valor) {
        lote.insert('metadato', {'clave': clave, 'valor': valor},
            conflictAlgorithm: ConflictAlgorithm.replace);
      });
      await lote.commit(noResult: true);
    });
  }

  Future<PaqueteInventario?> leerPaqueteInventario() async {
    final db = await _base;
    final meta = {
      for (final f in await db.query('metadato'))
        f['clave'] as String: f['valor'] as String,
    };
    if (!meta.containsKey('inv_generado_en')) return null;
    return PaqueteInventario(
      generadoEn: DateTime.parse(meta['inv_generado_en']!),
      vigenteHasta: DateTime.parse(meta['inv_vigente_hasta']!),
      sucursalId: int.parse(meta['inv_sucursal_id']!),
      sucursal: meta['inv_sucursal']!,
      prendas: [
        for (final f in await db.query('prenda_inventario', orderBy: 'producto, talla, color'))
          PrendaInventario(
            varianteId: f['variante_id'] as int,
            sku: f['sku'] as String,
            producto: f['producto'] as String,
            talla: f['talla'] as String,
            color: f['color'] as String,
            disponible: f['disponible'] as int,
            reservada: f['reservada'] as int,
            stockMinimo: f['stock_minimo'] as int,
          ),
      ],
      proveedores: [
        for (final f in await db.query('proveedor_local', orderBy: 'razon_social'))
          ProveedorLocal(id: f['id'] as int, razonSocial: f['razon_social'] as String),
      ],
    );
  }

  /// Suma (o resta) al disponible local lo registrado sin red. Nunca baja de
  /// cero: si no alcanza, lo decide el servidor al sincronizar.
  Future<void> aplicarAInventario(Map<int, int> delta) async {
    final db = await _base;
    await db.transaction((tx) async {
      for (final e in delta.entries) {
        await tx.rawUpdate(
          'UPDATE prenda_inventario SET disponible = MAX(0, disponible + ?) '
          'WHERE variante_id = ?',
          [e.value, e.key],
        );
      }
    });
  }

  // --- La cola (CU-15, CU-17 y CU-18) -------------------------------------

  Future<void> guardarOperacion(OperacionGuardada op) async {
    final db = await _base;
    await db.insert(
        'operacion_pendiente',
        {
          'uuid': op.uuid,
          'estado': op.estado.codigo,
          'cuerpo': jsonEncode(op.cuerpo),
          'resumen': op.resumen,
          'creada_en': op.creadaEn.toIso8601String(),
          'intentos': op.intentos,
          'motivo': op.motivo,
          'reserva_id': op.reservaId,
        },
        conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<List<OperacionGuardada>> operaciones() async {
    final db = await _base;
    return [
      for (final f in await db.query(
        'operacion_pendiente',
        orderBy: 'creada_en DESC',
      ))
        OperacionGuardada(
          uuid: f['uuid'] as String,
          estado: EstadoOperacion.desdeCodigo(f['estado'] as String),
          cuerpo: jsonDecode(f['cuerpo'] as String) as Map<String, dynamic>,
          resumen: f['resumen'] as String,
          creadaEn: DateTime.parse(f['creada_en'] as String),
          intentos: f['intentos'] as int,
          motivo: f['motivo'] as String?,
          reservaId: f['reserva_id'] as int?,
        ),
    ];
  }

  /// Solo las ya decididas por el servidor. Las pendientes no se borran nunca
  /// desde la app (RNF06).
  Future<void> borrarDecididas() async {
    final db = await _base;
    await db.delete(
      'operacion_pendiente',
      where: 'estado IN (?, ?)',
      whereArgs: [
        EstadoOperacion.confirmada.codigo,
        EstadoOperacion.rechazada.codigo,
      ],
    );
  }
}
