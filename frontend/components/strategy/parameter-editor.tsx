"use client"

import { Slider } from "@/components/ui/slider"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useState } from "react"

export function ParameterEditor() {
  const [sensitivityThreshold, setSensitivityThreshold] = useState(0.75)
  const [minTransactions, setMinTransactions] = useState(50)
  const [timeWindowDays, setTimeWindowDays] = useState(30)
  const [enableAutoUpdate, setEnableAutoUpdate] = useState(true)

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor="sensitivity-threshold">Sensitivity Threshold</Label>
          <span className="text-sm text-muted-foreground">{sensitivityThreshold.toFixed(2)}</span>
        </div>
        <Slider
          id="sensitivity-threshold"
          min={0}
          max={1}
          step={0.01}
          value={[sensitivityThreshold]}
          onValueChange={(value) => setSensitivityThreshold(value[0])}
        />
        <p className="text-xs text-muted-foreground">
          Higher values increase detection sensitivity but may lead to more false positives
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="min-transactions">Minimum Transactions</Label>
        <Input
          id="min-transactions"
          type="number"
          value={minTransactions}
          onChange={(e) => setMinTransactions(Number.parseInt(e.target.value))}
        />
        <p className="text-xs text-muted-foreground">Minimum number of transactions required for anomaly detection</p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="time-window">Time Window (days)</Label>
        <Input
          id="time-window"
          type="number"
          value={timeWindowDays}
          onChange={(e) => setTimeWindowDays(Number.parseInt(e.target.value))}
        />
        <p className="text-xs text-muted-foreground">Historical time window used for establishing baseline behavior</p>
      </div>

      <div className="flex items-center space-x-2">
        <Switch id="auto-update" checked={enableAutoUpdate} onCheckedChange={setEnableAutoUpdate} />
        <Label htmlFor="auto-update">Auto-update model</Label>
      </div>

      <Button className="w-full">Save Parameters</Button>
    </div>
  )
}
