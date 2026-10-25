/// Un monto en bolivianos, igual que en la web: «Bs 1.500,00».
///
/// Coma para los decimales y punto para los miles, como se escribe en Bolivia.
/// La API manda los montos como texto («400.00»); antes se pegaban tal cual.
/// Espejo de `formatoBs` en `frontend-web/src/app/shared/bs.pipe.ts`.
String bs(Object? valor) {
  final numero = valor is num ? valor : num.tryParse('${valor ?? ''}');
  if (numero == null) return '';
  final partes = numero.abs().toStringAsFixed(2).split('.');
  final miles = partes[0].replaceAllMapped(
    RegExp(r'\B(?=(\d{3})+(?!\d))'),
    (_) => '.',
  );
  return '${numero < 0 ? '−' : ''}Bs $miles,${partes[1]}';
}
