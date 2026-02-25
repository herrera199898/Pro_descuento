"use client"

import { FileSpreadsheet, Calculator, Loader2, Timer, Hash } from "lucide-react"
import { Button } from "@/components/ui/button"

interface ResultsPanelProps {
  results: string
  time: string
  isCalculating: boolean
  isExporting: boolean
  onCalculate: () => void
  onExport: () => void
}

export function ResultsPanel({
  results,
  time,
  isCalculating,
  isExporting,
  onCalculate,
  onExport,
}: ResultsPanelProps) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 sm:flex-row">
        <Button
          onClick={onCalculate}
          disabled={isCalculating}
          className="flex-1 h-11 text-sm font-medium"
        >
          {isCalculating ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Calculator className="size-4" />
          )}
          {isCalculating ? "Calculando..." : "Calcular cantidad"}
        </Button>
        <Button
          onClick={onExport}
          disabled={isExporting}
          variant="outline"
          className="flex-1 h-11 text-sm font-medium border-primary/30 text-primary hover:bg-primary/10 hover:text-primary"
        >
          {isExporting ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <FileSpreadsheet className="size-4" />
          )}
          {isExporting ? "Exportando..." : "Exportar Excel"}
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="flex items-center gap-3 rounded-lg bg-secondary/50 border border-border/50 px-4 py-3">
          <div className="flex items-center justify-center size-8 rounded-md bg-primary/15 text-primary">
            <Hash className="size-4" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Resultados</p>
            <p className="text-sm font-semibold text-foreground font-mono">
              {results || "-"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-lg bg-secondary/50 border border-border/50 px-4 py-3">
          <div className="flex items-center justify-center size-8 rounded-md bg-primary/15 text-primary">
            <Timer className="size-4" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Tiempo</p>
            <p className="text-sm font-semibold text-foreground font-mono">
              {time || "-"}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
