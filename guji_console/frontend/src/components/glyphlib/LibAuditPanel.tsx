import { useEffect, useMemo, useState } from 'react'

// 一批只渲染这么多卡（每卡六张图）：四庫 435 张一次铺开，浏览器卡死（用户 2026-09-26）
const BATCH = 30
import { IdsPicker } from './IdsPicker'
import { aroundKey, contextImgUrl, fetchAroundBatch } from '../../api/review'
import type { AroundContext } from '../../types/review'
import { fetchLibAudit, FONT_NAME, libFontUrl, libPatchUrl, postLibAudit, PROV_LABEL,
  type AuditDecision, type AuditFinding, type AuditResult } from '../../api/glyphlib'

// 体检：`glyph-db selfcheck` 标出的可疑刻例，一张卡一个。本例与它的同字最近、
// 本书里最像的别的字、他书里最像的别的字、字体（本字 / 最像的别的字）并排。
// 裁决走 glyph_audit 事件（feedback/glyph_audit.py）：没问题 / 形近·异体 / 撤库 / 改字。
export function LibAuditPanel({ onPick, isAdmin }: { onPick: (c: string) => void; isAdmin: boolean }) {
  const [r, setR] = useState<AuditResult | null>(null)
  const [err, setErr] = useState('')
  const [flag, setFlag] = useState('')
  const [done, setDone] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState('')
  const [picking, setPicking] = useState('')
  const [skipped, setSkipped] = useState<Set<string>>(new Set())   // 翻过去没裁的，本轮不再出
  const [view, setView] = useState<string[] | null>(null)          // 当前这一批的卡（key）
  const [around, setAround] = useState<Record<string, AroundContext>>({})  // `册|p:c:s` → 前后各 10 字
  useEffect(() => { fetchLibAudit().then(setR).catch((e) => setErr((e as Error).message)) }, [])

  const shown = useMemo(() => (r?.findings ?? []).filter((f) => !flag || f.flags.includes(flag)
    || (flag === 'human_conflict' && f.human_conflict) || (flag === 'context' && f.provenance === 'context')), [r, flag])

  // 下一批：跳过当前批里没裁的，从剩下（未裁、未跳过）的里再取 BATCH 张
  const takeBatch = (skip: Set<string>) =>
    shown.filter((f) => !done[f.key] && !skip.has(f.key)).slice(0, BATCH).map((f) => f.key)
  const batchKeys = view ?? takeBatch(skipped)
  const byKey = new Map(shown.map((f) => [f.key, f]))
  const batch = batchKeys.map((k) => byKey.get(k)).filter((f): f is AuditFinding => !!f)
  const left = shown.filter((f) => !done[f.key] && !skipped.has(f.key) && !batchKeys.includes(f.key)).length
  const nBatchDone = batch.filter((f) => done[f.key]).length
  const batchSig = batch.map((f) => f.key).join(',')
  useEffect(() => {
    // 一批卡的文字上下文：本例、本书同字参照、本书对手，按册一次批量取（产物不在本机的册取不到，不显示）
    const byBook = new Map<string, Map<string, { page: number; col: number; slot: number; sub: string }>>()
    for (const f of batch) {
      for (const iid of [f.instance_id, f.same_peer_ws ? null : f.same_peer, f.rival_peer]) {
        const c = iid ? cellOf(iid) : null
        if (!c || around[ctxKey(c)]) continue
        if (!byBook.has(c.book)) byBook.set(c.book, new Map())
        byBook.get(c.book)!.set(aroundKey(c), { page: c.page, col: c.col, slot: c.slot, sub: c.sub })
      }
    }
    byBook.forEach((m, book) => {
      fetchAroundBatch(book, 10, 10, [...m.values()])
        .then((res) => setAround((a) => {
          const n = { ...a }
          for (const [k, v] of Object.entries(res.around)) n[`${book}|${k}`] = v
          return n
        }))
        .catch(() => {})
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batchSig])
  function nextBatch() {
    const skip = new Set(skipped)
    batch.forEach((f) => { if (!done[f.key]) skip.add(f.key) })
    setSkipped(skip)
    setView(takeBatch(skip))
    window.scrollTo({ top: 0 })
  }
  function restart() { setSkipped(new Set()); setView(null) }

  async function decide(f: AuditFinding, d: Omit<AuditDecision, 'key' | 'instance_id'>) {
    setBusy(f.key)
    try {
      const res = await postLibAudit({ key: f.key, instance_id: f.instance_id, flags: f.flags, char_self: f.char,
        peer: f.rival_peer ?? f.xrival_peer, peer_char: f.rival_char ?? f.xrival_char ?? f.font_char, ...d })
      if (!res.ok) { alert(res.error || res.consume_error || '失败'); return }
      setDone((m) => ({ ...m, [f.key]: label(d) }))
    } catch (e) { alert((e as Error).message) } finally { setBusy('') }
  }

  if (err) return <p className="error">{err}</p>
  if (!r) return <p className="muted">读取中…</p>
  if (!r.meta.n_checked) return (
    <div className="card"><p>还没跑过体检。在工作区上跑：</p>
      <pre className="mono">python -m open_guji_cv glyph-db selfcheck</pre>
      <p className="muted">结果落 <span className="mono">{r.out}</span>。北行约 15 分钟、四庫约 1 小时（两核）。</p></div>
  )
  const fc = r.meta.flag_counts ?? {}
  return (
    <div>
      <div className="pv-toolbar">
        <span className="muted">体检于 {r.meta.created_at}，查 {r.meta.n_checked?.toLocaleString()} 例，标 {r.meta.n_flagged} 例；
          已裁 {r.n_decided + Object.keys(done).length}，参照：{(r.meta.others ?? []).join('、') || '仅本书'}</span>
        <label className="muted">只看
          <select value={flag} onChange={(e) => { setFlag(e.target.value); restart() }}>
            <option value="">全部 {r.findings.length}</option>
            {Object.entries(r.flag_labels).map(([k, t]) => <option key={k} value={k}>{t} {fc[k] ?? 0}</option>)}
            <option value="human_conflict">人裁 × 人裁冲突</option>
            <option value="context">上下文放行的</option>
          </select>
        </label>
      </div>
      {r.meta.fonts && (
        <details className="card gl-fonts">
          <summary>本书刻例与各字体的相似度（本字，弹性覆盖率）</summary>
          <table className="pb-table">
            <thead><tr><th className="pb-left">字体</th><th>中位</th><th>P10</th><th>最像它的刻例</th></tr></thead>
            <tbody>
              {Object.entries(r.meta.fonts).sort((a, b) => b[1].median - a[1].median).map(([k, v]) => (
                <tr key={k}><td className="pb-left">{FONT_NAME[k] ?? k}</td><td>{v.median.toFixed(3)}</td>
                  <td>{v.p10.toFixed(3)}</td><td>{v.best_for.toLocaleString()}</td></tr>
              ))}
            </tbody>
          </table>
          <p className="muted gl-note">与各字体都不像（按字中位 &lt;0.80）的字 {(r.meta.chars_font_far ?? []).length} 个：
            {(r.meta.chars_font_far ?? []).slice(0, 60).map((c) => (
              <a key={c} href="#" onClick={(e) => { e.preventDefault(); onPick(c) }}> {c}</a>))}</p>
        </details>
      )}
      <div className="pv-toolbar gl-batchbar">
        <span>本批 {batch.length} 张，已裁 {nBatchDone}；后面还有 {left} 张{skipped.size ? `，跳过 ${skipped.size} 张` : ''}</span>
        <button className={nBatchDone === batch.length && left ? 'primary' : ''} disabled={!left} onClick={nextBatch}>下一批 {BATCH}</button>
        {skipped.size > 0 && <button onClick={restart}>回头看跳过的</button>}
      </div>
      {batch.map((f) => (
        <div key={f.key} className={`card gl-audit${done[f.key] ? ' gl-done' : ''}`}>
          <div className="gl-audit-head">
            <a href="#" className="gl-big-sm" onClick={(e) => { e.preventDefault(); onPick(f.char) }}>{f.char}</a>
            <span className="mono muted">{f.instance_id}</span>
            <span className="muted">{PROV_LABEL[f.provenance] ?? f.provenance}</span>
            {f.flags.map((k) => <span key={k} className="gl-tag">{r.flag_labels[k] ?? k}</span>)}
            {f.human_conflict && <span className="gl-tag gl-tag-hot">人裁互撞</span>}
            <span className="muted">分 {f.score}</span>
            {done[f.key] && <b className="gl-done-mark">{done[f.key]}</b>}
          </div>
          <div className="gl-tiles">
            <SelfFig iid={f.instance_id} />
            {f.same_peer && <Fig src={libPatchUrl(f.same_peer, f.same_peer_ws || undefined)}
              cap={`同字${f.same_peer_ws ? '·他书' : ''} ${f.best_same.toFixed(2)}`} />}
            {f.rival_peer && <Fig src={libPatchUrl(f.rival_peer)} cap={`本书「${f.rival_char}」${f.rival.toFixed(2)}`} />}
            {f.xrival_peer && <Fig src={libPatchUrl(f.xrival_peer, f.xrival_ws)} cap={`${f.xrival_ws}「${f.xrival_char}」${f.xrival.toFixed(2)}`} />}
            {(() => {
              const by = f.font_own_by ?? {}
              const best = Object.keys(by).sort((a, b) => by[b] - by[a])[0]
              const tip = Object.entries(by).map(([k, v]) => `${FONT_NAME[k] ?? k} ${v.toFixed(2)}`).join('\n')
              return <span title={tip}><Fig src={libFontUrl(f.char, best)}
                cap={`${best ? FONT_NAME[best] ?? best : '字体'}本字 ${f.font_own == null ? '—' : f.font_own.toFixed(2)}`} /></span>
            })()}
            {f.font_char && <Fig src={libFontUrl(f.font_char)} cap={`字体「${f.font_char}」${f.font_best.toFixed(2)}`} />}
          </div>
          <div className="gl-ctx-text">
            <CtxText around={around} iid={f.instance_id} label="本例" />
            {f.same_peer && !f.same_peer_ws && <CtxText around={around} iid={f.same_peer} label="同字参照" />}
            {f.rival_peer && <CtxText around={around} iid={f.rival_peer} label={`对手「${f.rival_char}」`} />}
          </div>
          <div className="gl-tiles gl-ctx">
            {f.same_peer && !f.same_peer_ws && <Ctx iid={f.same_peer} cap="同字参照所在列" />}
            {f.rival_peer && <Ctx iid={f.rival_peer} cap={`对手「${f.rival_char}」所在列`} />}
          </div>
          {!done[f.key] && !isAdmin && (
            <p className="muted">体检裁决（撤库/改字）需要管理员权限，只有管理员能操作。</p>
          )}
          {!done[f.key] && isAdmin && (
            <div className="gl-actions">
              <button disabled={!!busy} onClick={() => decide(f, { v: 'ok' })}>没问题</button>
              <button disabled={!!busy} onClick={() => decide(f, { v: 'near_form' })}
                title="两个都没标错，只是形近或异体">形近·异体</button>
              <button disabled={!!busy} onClick={() => decide(f, { v: 'evict', target: f.instance_id })}
                title="本例撤出字形库（图坏 / 切坏 / 认不准）">撤本例</button>
              {f.same_peer && !f.same_peer_ws && <button disabled={!!busy} onClick={() => decide(f, { v: 'evict', target: f.same_peer! })}
                title="本例没错，那张同字参照标错了（或图坏），撤它">撤同字参照「{f.char}」</button>}
              {f.rival_peer && <button disabled={!!busy} onClick={() => decide(f, { v: 'evict', target: f.rival_peer! })}
                title="本书里那个对手标错了，撤它">撤对手「{f.rival_char}」</button>}
              {[f.rival_char, f.xrival_char, f.font_char].filter((c, i, a) => c && a.indexOf(c) === i).map((c) => (
                <button key={c} disabled={!!busy} onClick={() => decide(f, { v: 'relabel', char: c! })}>改成「{c}」</button>
              ))}
              <button disabled={!!busy} onClick={() => {
                const c = [...(prompt('本例其实是哪个字？') ?? '').trim()][0]
                if (c) decide(f, { v: 'relabel', char: c })
              }}>改成…</button>
              <span className="gl-sep" />
              <button disabled={!!busy} onClick={() => decide(f, { v: 'fidelity', fidelity: 'exact' })}
                title="字没标错，且刻的就是这个码位的通行字形">完全一致</button>
              <button disabled={!!busy} onClick={() => setPicking(f.key)}
                title="写实际结构，先在 Unicode 里反查">最近似码位 / 无码…</button>
            </div>
          )}
          {!done[f.key] && picking === f.key && (
            <IdsPicker initial="" current={f.char} onCancel={() => setPicking('')}
              onPick={(p) => { setPicking(''); if (p.kind === 'relabel') decide(f, { v: 'relabel', char: p.char })
                else decide(f, { v: 'fidelity', fidelity: p.fidelity, ids: p.ids, force: p.force }) }} />
          )}
        </div>
      ))}
      {batch.length === 0 && <p className="muted">这一类没有待裁的卡。</p>}
      {batch.length > 0 && (
        <div className="pv-toolbar gl-batchbar">
          <span className="muted">本批已裁 {nBatchDone} / {batch.length}</span>
          <button className={nBatchDone === batch.length && left ? 'primary' : ''} disabled={!left} onClick={nextBatch}>下一批 {BATCH}（跳过本批没裁的）</button>
        </div>
      )}
      <p className="muted gl-note">撤库、改字改的是 glyph.db；裁完 <span className="mono">guji db sync</span> 推回中心库（服务器上定时自动推）。</p>
    </div>
  )
}

function label(d: Omit<AuditDecision, 'key' | 'instance_id'>) {
  if (d.v === 'fidelity') return d.fidelity === 'exact' ? '完全一致' : `${d.fidelity === 'nearest' ? '最近似' : '无码'} ${d.ids}`
  return d.v === 'ok' ? '没问题' : d.v === 'near_form' ? '形近·异体' : d.v === 'evict' ? '已撤' : `改成 ${d.char}`
}

function Fig({ src, cap, strong }: { src: string; cap: string; strong?: boolean }) {
  return (
    <figure className="gl-tile gl-audit-fig">
      <img className={`gl-img gl-img-lg${strong ? ' gl-img-self' : ''}`} src={src} alt={cap} loading="lazy"
        onError={(e) => { (e.target as HTMLImageElement).style.visibility = 'hidden' }} />
      <figcaption>{cap}</figcaption>
    </figure>
  )
}

// 实例 id → 格：`v2:vol02:58:2:10` / `vol01:10:4:17` / `v2:vol01:88:1:3a` → 册、页、列、格、夹注。v1:（旧格序坐标）不出上下文。
function cellOf(iid: string): { book: string; page: number; col: number; slot: number; sub: string } | null {
  const p = iid.split(':')
  if (p[0] === 'v1') return null
  const q = p[0] === 'v2' ? p.slice(1) : p
  const m = q.length === 4 ? /^(\d+)([ab]?)$/.exec(q[3]) : null
  if (!m) return null
  const [book, page, col] = [q[0], +q[1], +q[2]]
  return Number.isFinite(page) && Number.isFinite(col) ? { book, page, col, slot: +m[1], sub: m[2] } : null
}

const ctxKey = (c: { book: string; page: number; col: number; slot: number; sub: string }) => `${c.book}|${aroundKey(c)}`

// 本例：切分前的列图，上下各多一格，红框标出本格——上下切分错能一眼看出（Sheldon 2026-11-03）。
// 该册产物不在本机就退回库里的图块。
function SelfFig({ iid }: { iid: string }) {
  const c = cellOf(iid)
  const [fallback, setFallback] = useState(!c)
  const src = fallback || !c ? libPatchUrl(iid) : contextImgUrl(c.book, c.page, c.col, c.slot, 1, true)
  return (
    <figure className="gl-tile gl-audit-fig">
      <img className={fallback ? 'gl-img gl-img-lg gl-img-self' : 'gl-self-ctx'} src={src} alt="本例" loading="lazy"
        onError={() => { if (!fallback) setFallback(true) }} />
      <figcaption>本例{fallback ? '' : '（红框，上下各一格）'}</figcaption>
    </figure>
  )
}

// 文字上下文：前后各 10 字，本格加粗标红（有整理本字用整理本，否则刻本读法）
function CtxText({ around, iid, label }: { around: Record<string, AroundContext>; iid: string; label: string }) {
  const c = cellOf(iid)
  const a = c ? around[ctxKey(c)] : undefined
  if (!a || a.at < 0 || !a.slots.length) return null
  const t = (k: number) => a.slots[k]?.text || a.slots[k]?.char || '□'
  return (
    <div className="gl-ctx-line"><span className="muted">{label}</span>{' '}
      {a.slots.slice(0, a.at).map((_, k) => t(k)).join('')}
      <b className="gl-ctx-hit">{t(a.at)}</b>
      {a.slots.slice(a.at + 1).map((_, k) => t(a.at + 1 + k)).join('')}
    </div>
  )
}

// 同字参照 / 对手所在列：同样上下各一格、红框
function Ctx({ iid, cap }: { iid: string; cap: string }) {
  const c = cellOf(iid)
  if (!c) return null
  return (
    <figure className="gl-tile gl-audit-fig gl-ctx-fig">
      <img className="gl-ctx-img" src={contextImgUrl(c.book, c.page, c.col, c.slot, 1, true)} alt={cap} loading="lazy"
        onError={(e) => { (e.target as HTMLImageElement).closest('figure')!.style.display = 'none' }} />
      <figcaption>{cap}</figcaption>
    </figure>
  )
}
