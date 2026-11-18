import { useState } from 'react'
import { withWorkspace } from '../../api/client'
import './binaryToggle.css'

/**
 * 字块图 + 「自动 / 二值 / 彩图 / 灰度」切换（彩图与自动：2026-11-17 彩图书双层显示）。
 *
 * **缺省显示二值**（用户 2026-09-16）：最后进字形库的一定是二值的，审阅时看到的
 * 就该是库里那个形，灰度会干扰判断。点一下切回灰度看扫描原样——同一个坐标两套图。
 *
 * 服务端 `?src=bin` 用 `char_index` 的 `bbox_page` 从整页二值副本上重裁
 * （`utils/binarized.py`）；副本没生成时**自动退回灰度**，不报错、不空图。
 *
 * ⚠️ `withWorkspace` 不能省：`<img src>` 发不出自定义请求头，工作区只能走查询串，
 * 不带的话服务端按默认工作区找不到这本书的 cache，直接 500。
 *
 * 复用点：Step7 定字裁决卡、异体组视图、夹注卡——凡是「给人看一个字块让他判」
 * 的地方都该用这个，别各写一份（各写一份的结果就是有的地方看二值、有的看灰度，
 * 人对不上号）。
 */
export type PatchSrc = 'auto' | 'bin' | 'color' | 'gray'

const SRC_LABEL: Record<PatchSrc, string> = { auto: '自动', bin: '二值', color: '彩图', gray: '灰度' }
const SRC_TITLE: Record<PatchSrc, string> = {
  auto: '自动：落进二值体检可疑区（朱印朱批、二值与灰度差得多、纸纹斑点）的字块给彩图，其余给二值',
  bin: '二值＝进库那张（整页二值副本）',
  color: '彩图＝原图原样（彩图书就是彩色）',
  gray: '灰度＝管线缓存里的裁片',
}

export function BinaryToggleImage({ src, alt, defaultBin = true, showToggle = true, extra }: {
  /** 字块图 URL，形如 `/api/cache/<book>/char_patch/<key>.png`（不带 query） */
  src: string
  alt?: string
  /** 缺省看二值（自动）还是灰度。只在「就是要看扫描原样」的场合传 false */
  defaultBin?: boolean
  /** 关掉切换按钮（缩略图列表等放不下按钮的地方） */
  showToggle?: boolean
  /** 按钮行里再塞几个别的按钮（如「看原图」） */
  extra?: React.ReactNode
}) {
  // 缺省「自动」：服务端按二值体检决定给二值还是彩图（2026-11-17）；没写 ink 的老书没有体检，自动＝二值，与以前一样
  const [mode, setMode] = useState<PatchSrc>(defaultBin ? 'auto' : 'gray')
  const q = mode === 'gray' ? '' : `src=${mode}`
  const url = withWorkspace(src + (q ? (src.includes('?') ? '&' : '?') + q : ''))
  return (
    <div className="bti">
      <img src={url} alt={alt ?? ''} loading="lazy" />
      {(showToggle || extra) && (
        <div className="bti-btns">
          {showToggle && (['auto', 'bin', 'color', 'gray'] as PatchSrc[]).map((m) => (
            <button key={m} className={'bti-btn' + (m === mode ? ' bti-on' : '')} title={SRC_TITLE[m]}
                    onClick={(e) => { e.stopPropagation(); setMode(m) }}>
              {SRC_LABEL[m]}
            </button>
          ))}
          {extra}
        </div>
      )}
    </div>
  )
}
