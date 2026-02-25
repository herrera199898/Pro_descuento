"use client"

import { Database, Zap } from "lucide-react"

export function ExportHeader() {
  return (
    <header className="flex flex-col gap-2">
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center size-10 rounded-lg bg-primary/15 text-primary">
          <Database className="size-5" />
        </div>
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-foreground">
            MercadoLibre Export
          </h1>
          <p className="text-sm text-muted-foreground">
            Herramienta de extraccion de datos
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2 mt-1">
        <div className="flex items-center gap-1.5 rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">
          <Zap className="size-3" />
          <span>Pro</span>
        </div>
        <span className="text-xs text-muted-foreground">
          Configura filtros, calcula resultados y exporta a Excel
        </span>
      </div>
    </header>
  )
}
