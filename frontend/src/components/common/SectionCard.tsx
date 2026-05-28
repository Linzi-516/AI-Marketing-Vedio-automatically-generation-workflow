import type { ReactNode } from 'react'

interface SectionCardProps {
  title: string
  status?: string
  children: ReactNode
}

function SectionCard({ title, status = '未执行', children }: SectionCardProps) {
  return (
    <section className="section-card">
      <header className="section-header">
        <h2>{title}</h2>
        <span className="section-status">{status}</span>
      </header>
      <div className="section-body">{children}</div>
    </section>
  )
}

export default SectionCard
