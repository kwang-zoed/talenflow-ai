import { pcaTextArr } from 'element-china-area-data'

/** 全国省 / 市 / 区三级数据 + 远程选项 */
export const CHINA_REGION_OPTIONS = [
  ...pcaTextArr,
  {
    value: '远程',
    label: '远程',
    children: [{ value: '远程办公', label: '远程办公' }],
  },
]

export function regionLabelFromPath(path = []) {
  return Array.isArray(path) ? path.filter(Boolean).join('/') : ''
}

export function pathFromRegionLabel(label = '') {
  if (!label) return []
  return String(label).split('/').filter(Boolean)
}
