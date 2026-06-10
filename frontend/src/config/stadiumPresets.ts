/** Stadium name fuzzy match → camera preset */

export interface StadiumPreset {
  keywords: string[]
  camera: { x: number; y: number; z: number }
  lookAt: { x: number; y: number; z: number }
}

export const STADIUM_PRESETS: StadiumPreset[] = [
  {
    keywords: ['metlife', 'new york', '纽约'],
    camera: { x: 12, y: 8, z: 14 },
    lookAt: { x: 0, y: 0, z: 0 },
  },
  {
    keywords: ['sofi', 'los angeles', '洛杉矶'],
    camera: { x: -10, y: 7, z: 12 },
    lookAt: { x: 0, y: 0, z: 0 },
  },
  {
    keywords: ['atlanta', '亚特兰大'],
    camera: { x: 8, y: 9, z: -11 },
    lookAt: { x: 0, y: 0, z: 0 },
  },
  {
    keywords: ['dallas', '达拉斯', 'arlington'],
    camera: { x: -14, y: 6, z: 8 },
    lookAt: { x: 0, y: 0, z: 0 },
  },
  {
    keywords: ['miami', '迈阿密', 'hard rock'],
    camera: { x: 10, y: 5, z: 10 },
    lookAt: { x: 0, y: 0, z: 0 },
  },
  {
    keywords: ['houston', '休斯顿', 'nrg'],
    camera: { x: -8, y: 10, z: -9 },
    lookAt: { x: 0, y: 0, z: 0 },
  },
  {
    keywords: ['philadelphia', '费城', 'lincoln'],
    camera: { x: 14, y: 7, z: -6 },
    lookAt: { x: 0, y: 0, z: 0 },
  },
  {
    keywords: ['seattle', '西雅图', 'lumen'],
    camera: { x: -6, y: 8, z: 14 },
    lookAt: { x: 0, y: 0, z: 0 },
  },
  {
    keywords: ['san francisco', '旧金山', 'levis', "levi's"],
    camera: { x: 6, y: 11, z: -12 },
    lookAt: { x: 0, y: 0, z: 0 },
  },
  {
    keywords: ['kansas', '堪萨斯', 'arrowhead'],
    camera: { x: -12, y: 9, z: -8 },
    lookAt: { x: 0, y: 0, z: 0 },
  },
  {
    keywords: ['boston', '波士顿', 'foxborough', 'gillette'],
    camera: { x: 9, y: 6, z: -14 },
    lookAt: { x: 0, y: 0, z: 0 },
  },
  {
    keywords: ['toronto', '多伦多', 'bmo'],
    camera: { x: -9, y: 7, z: 11 },
    lookAt: { x: 0, y: 0, z: 0 },
  },
]

export const DEFAULT_PRESET: StadiumPreset = {
  keywords: ['default'],
  camera: { x: 0, y: 12, z: 18 },
  lookAt: { x: 0, y: 0, z: 0 },
}

export function resolveStadiumPreset(stadiumName: string | undefined): StadiumPreset {
  if (!stadiumName) return DEFAULT_PRESET
  const lower = stadiumName.toLowerCase()
  for (const preset of STADIUM_PRESETS) {
    if (preset.keywords.some((k) => lower.includes(k.toLowerCase()))) {
      return preset
    }
  }
  return DEFAULT_PRESET
}
