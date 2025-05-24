"use client"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { AlertTriangle, Check, Shield, Zap } from "lucide-react"

const presets = [
  {
    id: "conservative",
    name: "Conservative",
    description: "Lower sensitivity, fewer false positives",
    icon: Shield,
    sensitivity: "Low",
    falsePositives: "Low",
    coverage: "Medium",
  },
  {
    id: "balanced",
    name: "Balanced",
    description: "Moderate sensitivity and false positives",
    icon: Check,
    sensitivity: "Medium",
    falsePositives: "Medium",
    coverage: "Medium",
  },
  {
    id: "aggressive",
    name: "Aggressive",
    description: "High sensitivity, more false positives",
    icon: AlertTriangle,
    sensitivity: "High",
    falsePositives: "High",
    coverage: "High",
  },
  {
    id: "custom",
    name: "Custom",
    description: "Your custom detection strategy",
    icon: Zap,
    sensitivity: "Custom",
    falsePositives: "Custom",
    coverage: "Custom",
  },
]

export function StrategyPresets() {
  return (
    <div className="space-y-4">
      {presets.map((preset) => (
        <Card key={preset.id} className={preset.id === "balanced" ? "border-primary" : ""}>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">{preset.name}</CardTitle>
              <preset.icon className="h-5 w-5 text-muted-foreground" />
            </div>
            <CardDescription>{preset.description}</CardDescription>
          </CardHeader>
          <CardContent className="pb-2">
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div>
                <span className="text-muted-foreground">Sensitivity</span>
                <Badge variant="outline" className="mt-1 w-full justify-center">
                  {preset.sensitivity}
                </Badge>
              </div>
              <div>
                <span className="text-muted-foreground">False Positives</span>
                <Badge variant="outline" className="mt-1 w-full justify-center">
                  {preset.falsePositives}
                </Badge>
              </div>
              <div>
                <span className="text-muted-foreground">Coverage</span>
                <Badge variant="outline" className="mt-1 w-full justify-center">
                  {preset.coverage}
                </Badge>
              </div>
            </div>
          </CardContent>
          <CardFooter>
            <Button variant={preset.id === "balanced" ? "default" : "outline"} size="sm" className="w-full">
              {preset.id === "balanced" ? "Active" : "Apply"}
            </Button>
          </CardFooter>
        </Card>
      ))}
    </div>
  )
}
