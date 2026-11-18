import { useState } from 'react'
import { fetchProduct, overlayUrl, type OverlayBg } from '../api/products'
import type { ProductManifestEntry } from '../types/products'

// 用户 2026-09-11 测试反馈 §3："产物要分配到各 step"——v1 的"产物"是独立
// tab（选步骤+选页），方案 §三 定的是拆掉、按内容分流到各步。这个组件是
// 分流后的落点：每个 Step 页面自己嵌一份"看这一步的产物"，不用再选步骤
// （已经在这一步的页面里，步骤是固定的）。
function fmtTs(ts?: number): string {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

export function ProductViewer({ book, step, pages, pageTypeOf }: {
  book: string
  step: string
  pages: number[]
  /** 可选：页码 → 页型标签，Step1 用闸1 的 page_type 判定喂进来，在 metaLine
   * 里显示"这一页是什么类型"，不用去数值产物里翻 JSON 找。 */
  pageTypeOf?: (page: number) => string | undefined
}) {
  // 下拉框只在 all_pages 有数据时管用；示例库/未设 GUJI_WORKSPACE 时
  // all_pages 常是空的（2026-09-11 走查发现：dev_set 全 blocked 时下拉框
  // 一直是空的"选一页"，用户完全查不了任何产物）。v1 原本是自由文本输入，
  // 不受这个数据源限制——这里两个都留：有数据就给下拉快选，手动输入兜底。
  const [page, setPage] = useState('')
  const [manifest, setManifest] = useState<ProductManifestEntry | null>(null)
  const [json, setJson] = useState('')
  const [imgSrc, setImgSrc] = useState('')
  const [imgError, setImgError] = useState('')
  const [msg, setMsg] = useState('')
  // 底图与二值体检可疑区（用户 2026-11-17：算法走二值，显示尽量彩图，二值出问题处切过来看）
  const [bg, setBg] = useState<OverlayBg>('color')
  const [qc, setQc] = useState(false)

  function reloadImg(nbg: OverlayBg, nqc: boolean) {
    const p = Number.parseInt(page, 10)
    if (!p) return
    setImgError('')
    setImgSrc(overlayUrl(book, step, p, 0.35, nbg, nqc))
  }

  async function load() {
    const p = Number.parseInt(page, 10)
    if (!p) return
    setImgError('')
    setImgSrc(overlayUrl(book, step, p, 0.35, bg, qc))
    try {
      const d = await fetchProduct(book, step, p)
      setManifest(d.manifest)
      setJson(JSON.stringify(d.products, null, 1))
      setMsg('')
    } catch (e) {
      setManifest(null)
      setJson('')
      setMsg((e as Error).message)
    }
  }

  const m = manifest
  const pageNum = Number.parseInt(page, 10)
  const pageType = pageTypeOf && Number.isFinite(pageNum) ? pageTypeOf(pageNum) : undefined
  const metaLine = m
    ? `${page.padStart(4, '0')} · 指纹 ${m.fingerprint || '-'} · ${m.status || ''} · ${m.elapsed != null ? m.elapsed + 's' : ''} · ${fmtTs(m.ts)} · ${m.code_rev || ''}${pageType ? ` · 页型 ${pageType}` : ''}`
    : msg

  return (
    <div className="card">
      <h2>产物</h2>
      <div className="pv-toolbar">
        <label className="muted">页 <input value={page} onChange={(e) => setPage(e.target.value)} size={6} placeholder="页码" /></label>
        {pages.length > 0 && (
          <label className="muted">快选
            <select value="" onChange={(e) => e.target.value && setPage(e.target.value)}>
              <option value="">（可选）从有产物的页里选</option>
              {pages.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </label>
        )}
        <button onClick={load}>查看</button>
        <label className="muted" title="叠图画在哪张图上：彩图＝原图原样；二值＝管线与字形库看的那张（guji binarize 生成）；灰度＝亮度图。三张坐标相同">底图
          <select value={bg} onChange={(e) => { const v = e.target.value as OverlayBg; setBg(v); reloadImg(v, qc) }}>
            <option value="color">彩图</option>
            <option value="bin">二值</option>
            <option value="gray">灰度</option>
          </select>
        </label>
        <label className="muted" title="叠上二值体检的可疑区：红＝有色记号（朱印朱批），紫＝二值与灰度差得多，橙＝纸纹斑点">
          <input type="checkbox" checked={qc} onChange={(e) => { setQc(e.target.checked); reloadImg(bg, e.target.checked) }} />可疑区
        </label>
        <span className="muted mono">{metaLine}</span>
      </div>
      {imgSrc && (
        <div className="products">
          <div className="card">
            <h2>叠图</h2>
            {imgError
              ? <p className="muted">{imgError}</p>
              : <img src={imgSrc} alt="原图叠产物"
                     onError={async () => {
                       // 不是所有 Step 都有叠图画法（比如 context_decide），
                       // 后端 404 时给具体原因，别让浏览器画一个破损图标占地方。
                       try {
                         const r = await fetch(imgSrc)
                         const d = await r.json().catch(() => null)
                         setImgError(d?.detail || '这一步没有叠图')
                       } catch {
                         setImgError('这一步没有叠图')
                       }
                     }} />}
          </div>
          <div className="card"><h2>数值产物</h2><pre className="json">{json}</pre></div>
        </div>
      )}
    </div>
  )
}
