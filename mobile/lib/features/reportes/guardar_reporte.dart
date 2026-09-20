/// Bajar un reporte y dejarlo donde la persona lo pueda encontrar.
///
/// POR QUÉ ESTO EXISTE, Y NO ES SOLO `writeAsBytes`
/// --------------------------------------------------
/// La primera versión guardaba en `getApplicationDocumentsDirectory()` y
/// avisaba con el nombre del archivo. **Ese directorio es privado de la
/// aplicación**: no aparece en el explorador de archivos del teléfono, no se
/// puede adjuntar a un correo y no se ve desde la computadora. El reporte
/// quedaba bajado y la persona no lo encontraba — que para el caso de uso es
/// lo mismo que no haberlo bajado.
///
/// Escribir directo en `Descargas` tampoco sirve: desde Android 10 el
/// almacenamiento delimitado lo impide sin pasar por `MediaStore`, que es
/// código nativo.
///
/// Lo que sí funciona sin código nativo es **guardar y abrir la hoja de
/// compartir del sistema**. Desde ahí se manda a Drive, a WhatsApp, al correo
/// o a «Archivos» —que es justamente «guardar donde yo quiera»—. Es un toque
/// más y es el único que termina con el archivo en un lugar que la persona
/// eligió.
///
/// NO SE ABRE SOLO
/// ---------------
/// En un teléfono sin lector de Excel, abrirlo directo termina en «no hay
/// ninguna aplicación», que se lee como que la descarga falló. La hoja de
/// compartir, en cambio, siempre ofrece algo.
library;

import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import '../../data/repositorios/repositorio_reportes.dart';

/// Guarda el archivo y ofrece compartirlo. Devuelve la ruta donde quedó.
///
/// `origen` es el rectángulo desde el que se abre la hoja en tabletas y en
/// iPad; en un teléfono Android se ignora, pero pasarlo no cuesta nada y
/// evita que la hoja salga en una esquina si alguna vez corre en pantalla
/// grande.
Future<String> guardarYCompartir(
  ArchivoDeReporte archivo, {
  Rect? origen,
}) async {
  final carpeta = await getTemporaryDirectory();
  final destino = '${carpeta.path}/${archivo.nombre}';
  await File(destino).writeAsBytes(archivo.contenido);

  await SharePlus.instance.share(
    ShareParams(
      files: [XFile(destino, mimeType: archivo.tipoMime)],
      // El texto va como asunto del correo si se comparte por ahí.
      subject: archivo.nombre,
      sharePositionOrigin: origen,
    ),
  );

  return destino;
}

/// El rectángulo del widget que disparó la acción, para la hoja de compartir.
Rect? rectanguloDe(BuildContext context) {
  final caja = context.findRenderObject();
  if (caja is! RenderBox || !caja.hasSize) return null;
  return caja.localToGlobal(Offset.zero) & caja.size;
}
