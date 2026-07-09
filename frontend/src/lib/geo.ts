// Distancia haversine en km entre dos puntos.
export function distKm(la1: number, lo1: number, la2: number, lo2: number): number {
  const R = 6371;
  const dLa = ((la2 - la1) * Math.PI) / 180;
  const dLo = ((lo2 - lo1) * Math.PI) / 180;
  const a =
    Math.sin(dLa / 2) ** 2 +
    Math.cos((la1 * Math.PI) / 180) *
      Math.cos((la2 * Math.PI) / 180) *
      Math.sin(dLo / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

/** URL de "Cómo llegar" en Google Maps hacia un destino. */
export function urlComoLlegar(lat: number, lng: number): string {
  return `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`;
}
