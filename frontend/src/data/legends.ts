export interface LegendCard {
  id: 'ronaldo' | 'messi' | 'neymar'
  name: string
  tagline: string
  /** 卡片/登录页等小图 (~640px) */
  image: string
  /** 首页大屏背景 (~960px) */
  imageBackdrop: string
  accent: string
}

export const LEGEND_CARDS: LegendCard[] = [
  {
    id: 'ronaldo',
    name: 'C罗',
    tagline: '最后一舞 · 王者气场',
    image: '/legends/ronaldo.webp',
    imageBackdrop: '/legends/ronaldo-backdrop.webp',
    accent: '#e8c88a',
  },
  {
    id: 'messi',
    name: '梅西',
    tagline: '最后一舞 · 魔术师',
    image: '/legends/messi.webp',
    imageBackdrop: '/legends/messi-backdrop.webp',
    accent: '#7eb8ff',
  },
  {
    id: 'neymar',
    name: '内马尔',
    tagline: '最后一舞 · 桑巴 flair',
    image: '/legends/neymar.webp',
    imageBackdrop: '/legends/neymar-backdrop.webp',
    accent: '#c9788a',
  },
]
