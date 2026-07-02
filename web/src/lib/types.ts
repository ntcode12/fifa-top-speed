export interface SpeedRow {
  match: string;
  team: string;
  jersey: number;
  player: string;
  top_speed_kmh: number;
}

export interface DeltaRow {
  player: string;
  team: string;
  slow: number;
  fast: number;
  delta: number;
}
