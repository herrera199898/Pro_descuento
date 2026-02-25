"use client"

import { X } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { useState, type KeyboardEvent } from "react"

interface TagInputProps {
  label: string
  placeholder: string
  tags: string[]
  onAddTag: (tag: string) => void
  onRemoveTag: (tag: string) => void
  variant?: "include" | "exclude"
}

export function TagInput({
  placeholder,
  tags,
  onAddTag,
  onRemoveTag,
  variant = "include",
}: TagInputProps) {
  const [value, setValue] = useState("")

  const handleAdd = () => {
    if (value.trim()) {
      onAddTag(value.trim())
      setValue("")
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault()
      handleAdd()
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <Input
          placeholder={placeholder}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          className="flex-1"
        />
        <Button
          type="button"
          onClick={handleAdd}
          size="sm"
          variant={variant === "include" ? "default" : "outline"}
          className={
            variant === "exclude"
              ? "border-destructive/30 text-destructive hover:bg-destructive/10 hover:text-destructive"
              : ""
          }
        >
          Agregar
        </Button>
      </div>
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {tags.map((tag) => (
            <Badge
              key={tag}
              variant={variant === "include" ? "default" : "outline"}
              className={`gap-1 pr-1 ${
                variant === "exclude"
                  ? "border-destructive/30 text-destructive bg-destructive/10"
                  : "bg-primary/15 text-primary border-primary/20"
              }`}
            >
              {tag}
              <button
                type="button"
                onClick={() => onRemoveTag(tag)}
                className="ml-0.5 rounded-full p-0.5 hover:bg-foreground/10 transition-colors"
                aria-label={`Eliminar ${tag}`}
              >
                <X className="size-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}
    </div>
  )
}
