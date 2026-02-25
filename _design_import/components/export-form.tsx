"use client"

import { useState } from "react"
import {
  Search,
  Globe,
  DollarSign,
  Percent,
  Filter,
  Tag,
  FileText,
  Link2,
  Cookie,
  Settings2,
} from "lucide-react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Separator } from "@/components/ui/separator"
import { Card, CardContent } from "@/components/ui/card"
import { TagInput } from "@/components/tag-input"
import { ResultsPanel } from "@/components/results-panel"
import { ExportHeader } from "@/components/export-header"

export function ExportForm() {
  const [search, setSearch] = useState("notebook rtx")
  const [country, setCountry] = useState("chile")
  const [priceMin, setPriceMin] = useState("0")
  const [priceMax, setPriceMax] = useState("0")
  const [discountMin, setDiscountMin] = useState("0")
  const [condition, setCondition] = useState("any")
  const [includeTags, setIncludeTags] = useState<string[]>([])
  const [excludeTags, setExcludeTags] = useState<string[]>([])
  const [maxPages, setMaxPages] = useState("0")
  const [exactUrl, setExactUrl] = useState("")
  const [cookiesFile, setCookiesFile] = useState("cookies.txt")
  const [searchAll, setSearchAll] = useState(true)
  const [sortByPrice, setSortByPrice] = useState(true)
  const [includeInternational, setIncludeInternational] = useState(false)

  const [results, setResults] = useState("")
  const [time, setTime] = useState("")
  const [isCalculating, setIsCalculating] = useState(false)
  const [isExporting, setIsExporting] = useState(false)

  const handleCalculate = () => {
    setIsCalculating(true)
    setTimeout(() => {
      setResults("1,247")
      setTime("2.3s")
      setIsCalculating(false)
    }, 1500)
  }

  const handleExport = () => {
    setIsExporting(true)
    setTimeout(() => {
      setIsExporting(false)
    }, 2000)
  }

  return (
    <div className="min-h-screen bg-background p-4 md:p-8">
      <div className="mx-auto max-w-3xl flex flex-col gap-6">
        <ExportHeader />

        <Card className="border-border/60">
          <CardContent className="flex flex-col gap-6">
            {/* Section: Busqueda principal */}
            <div className="flex flex-col gap-4">
              <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <Search className="size-4" />
                <span>Busqueda Principal</span>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="flex flex-col gap-2 sm:col-span-2">
                  <Label htmlFor="search" className="text-xs text-muted-foreground">
                    Busqueda
                  </Label>
                  <Input
                    id="search"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="ej: notebook rtx"
                  />
                </div>

                <div className="flex flex-col gap-2">
                  <Label htmlFor="country" className="text-xs text-muted-foreground">
                    <Globe className="size-3 inline mr-1" />
                    Pais
                  </Label>
                  <Select value={country} onValueChange={setCountry}>
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="chile">Chile</SelectItem>
                      <SelectItem value="argentina">Argentina</SelectItem>
                      <SelectItem value="mexico">Mexico</SelectItem>
                      <SelectItem value="colombia">Colombia</SelectItem>
                      <SelectItem value="brasil">Brasil</SelectItem>
                      <SelectItem value="peru">Peru</SelectItem>
                      <SelectItem value="uruguay">Uruguay</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex flex-col gap-2">
                  <Label htmlFor="condition" className="text-xs text-muted-foreground">
                    <Filter className="size-3 inline mr-1" />
                    Estado
                  </Label>
                  <Select value={condition} onValueChange={setCondition}>
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="any">Cualquiera</SelectItem>
                      <SelectItem value="new">Nuevo</SelectItem>
                      <SelectItem value="used">Usado</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            <Separator />

            {/* Section: Precio y descuento */}
            <div className="flex flex-col gap-4">
              <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <DollarSign className="size-4" />
                <span>Precio y Descuento</span>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div className="flex flex-col gap-2">
                  <Label htmlFor="priceMin" className="text-xs text-muted-foreground">
                    Precio minimo
                  </Label>
                  <Input
                    id="priceMin"
                    type="number"
                    value={priceMin}
                    onChange={(e) => setPriceMin(e.target.value)}
                    placeholder="0"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <Label htmlFor="priceMax" className="text-xs text-muted-foreground">
                    Precio maximo
                  </Label>
                  <Input
                    id="priceMax"
                    type="number"
                    value={priceMax}
                    onChange={(e) => setPriceMax(e.target.value)}
                    placeholder="0"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <Label htmlFor="discount" className="text-xs text-muted-foreground">
                    <Percent className="size-3 inline mr-1" />
                    Descuento minimo
                  </Label>
                  <Input
                    id="discount"
                    type="number"
                    value={discountMin}
                    onChange={(e) => setDiscountMin(e.target.value)}
                    placeholder="0"
                  />
                </div>
              </div>
            </div>

            <Separator />

            {/* Section: Palabras clave */}
            <div className="flex flex-col gap-4">
              <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <Tag className="size-4" />
                <span>Palabras Clave</span>
              </div>

              <div className="flex flex-col gap-4">
                <div className="flex flex-col gap-2">
                  <Label className="text-xs text-muted-foreground">
                    Palabras a incluir
                  </Label>
                  <TagInput
                    label="Incluir"
                    placeholder="ej: gamer"
                    tags={includeTags}
                    onAddTag={(tag) =>
                      setIncludeTags((prev) => [...prev, tag])
                    }
                    onRemoveTag={(tag) =>
                      setIncludeTags((prev) => prev.filter((t) => t !== tag))
                    }
                    variant="include"
                  />
                </div>

                <div className="flex flex-col gap-2">
                  <Label className="text-xs text-muted-foreground">
                    Palabras a descartar
                  </Label>
                  <TagInput
                    label="Excluir"
                    placeholder="ej: carcasa"
                    tags={excludeTags}
                    onAddTag={(tag) =>
                      setExcludeTags((prev) => [...prev, tag])
                    }
                    onRemoveTag={(tag) =>
                      setExcludeTags((prev) => prev.filter((t) => t !== tag))
                    }
                    variant="exclude"
                  />
                </div>
              </div>
            </div>

            <Separator />

            {/* Section: Configuracion avanzada */}
            <div className="flex flex-col gap-4">
              <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <Settings2 className="size-4" />
                <span>Configuracion Avanzada</span>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div className="flex flex-col gap-2">
                  <Label htmlFor="maxPages" className="text-xs text-muted-foreground">
                    <FileText className="size-3 inline mr-1" />
                    {'Max paginas (0 = sin limite)'}
                  </Label>
                  <Input
                    id="maxPages"
                    type="number"
                    value={maxPages}
                    onChange={(e) => setMaxPages(e.target.value)}
                    placeholder="0"
                  />
                </div>
                <div className="flex flex-col gap-2 sm:col-span-2">
                  <Label htmlFor="exactUrl" className="text-xs text-muted-foreground">
                    <Link2 className="size-3 inline mr-1" />
                    URL exacta (opcional)
                  </Label>
                  <Input
                    id="exactUrl"
                    value={exactUrl}
                    onChange={(e) => setExactUrl(e.target.value)}
                    placeholder="https://listado.mercadolibre.cl/..."
                  />
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <Label htmlFor="cookies" className="text-xs text-muted-foreground">
                  <Cookie className="size-3 inline mr-1" />
                  Archivo cookies (opcional)
                </Label>
                <Input
                  id="cookies"
                  value={cookiesFile}
                  onChange={(e) => setCookiesFile(e.target.value)}
                  placeholder="cookies.txt"
                  className="sm:max-w-xs"
                />
              </div>
            </div>

            <Separator />

            {/* Section: Opciones */}
            <div className="flex flex-col gap-4">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div className="flex items-center justify-between rounded-lg border border-border/50 bg-secondary/30 px-4 py-3">
                  <Label htmlFor="searchAll" className="text-xs text-foreground cursor-pointer">
                    Buscar todas las paginas
                  </Label>
                  <Switch
                    id="searchAll"
                    checked={searchAll}
                    onCheckedChange={setSearchAll}
                  />
                </div>
                <div className="flex items-center justify-between rounded-lg border border-border/50 bg-secondary/30 px-4 py-3">
                  <Label htmlFor="sortPrice" className="text-xs text-foreground cursor-pointer">
                    Ordenar por precio
                  </Label>
                  <Switch
                    id="sortPrice"
                    checked={sortByPrice}
                    onCheckedChange={setSortByPrice}
                  />
                </div>
                <div className="flex items-center justify-between rounded-lg border border-border/50 bg-secondary/30 px-4 py-3">
                  <Label htmlFor="international" className="text-xs text-foreground cursor-pointer">
                    Incluir internacionales
                  </Label>
                  <Switch
                    id="international"
                    checked={includeInternational}
                    onCheckedChange={setIncludeInternational}
                  />
                </div>
              </div>
            </div>

            <Separator />

            {/* Results & Actions */}
            <ResultsPanel
              results={results}
              time={time}
              isCalculating={isCalculating}
              isExporting={isExporting}
              onCalculate={handleCalculate}
              onExport={handleExport}
            />
          </CardContent>
        </Card>

        <p className="text-center text-xs text-muted-foreground">
          {'MercadoLibre Export Tool v2.0 — Los datos extraidos son para uso personal.'}
        </p>
      </div>
    </div>
  )
}
