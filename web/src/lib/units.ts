export type Unit = "kmh" | "mph";

export const MPH_PER_KMH = 0.621371;

export const unitLabel = (u: Unit) => (u === "kmh" ? "km/h" : "mph");

/** The "elite sprint" KPI threshold (35 km/h) expressed in the active unit. */
export const eliteThreshold = (u: Unit) => (u === "kmh" ? 35 : 35 * MPH_PER_KMH);
