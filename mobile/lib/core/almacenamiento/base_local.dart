/// SQLite del telefono (2do parcial, CU-13, CU-15, CU-17 y CU-18).
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

import '../../data/modelos/offline.dart';

class BaseLocal {
  BaseLocal._();

  static final BaseLocal instancia = BaseLocal._();

  static const _version = 1;
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
            producto TEXT NOT NULL,
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
          'producto': prenda.producto,
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
      lote.insert('metadato', {
        'clave': 'generado_en',
        'valor': paquete.generadoEn.toIso8601String(),
      }, conflictAlgorithm: ConflictAlgorithm.replace);
      lote.insert('metadato', {
        'clave': 'vigente_hasta',
        'valor': paquete.vigenteHasta.toIso8601String(),
      }, conflictAlgorithm: ConflictAlgorithm.replace);
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
      disponibles.putIfAbsent(f['variante_id'] as int, () => {})[f['sucursal_id']
              as int] =
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
            producto: f['producto'] as String,
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

  // --- La cola (CU-15, CU-17 y CU-18) -------------------------------------

  Future<void> guardarOperacion(OperacionGuardada op) async {
    final db = await _base;
    await db.insert('operacion_pendiente', {
      'uuid': op.uuid,
      'estado': op.estado.codigo,
      'cuerpo': jsonEncode(op.cuerpo),
      'resumen': op.resumen,
      'creada_en': op.creadaEn.toIso8601String(),
      'intentos': op.intentos,
      'motivo': op.motivo,
      'reserva_id': op.reservaId,
    }, conflictAlgorithm: ConflictAlgorithm.replace);
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
