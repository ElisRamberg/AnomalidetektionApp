"use client"

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts"
import { Badge } from "@/components/ui/badge"

const data = [
  { date: "2024-01-01", current: 12, proposed: 15 },
  { date: "2024-01-02", current: 8, proposed: 12 },
  { date: "2024-01-03", current: 15, proposed: 18 },
  { date: "2024-01-04", current: 23, proposed: 25 },
  { date: "2024-01-05", current: 18, proposed: 22 },
  { date: "2024-01-06", current: 11, proposed: 14 },
  { date: "2024-01-07", current: 25, proposed: 28 },
]

const stats = [
  { name: "Detected Anomalies", current: 142, proposed: 187, change: "+31.7%" },
  { name: "False Positives", current: 23, proposed: 35, change: "+52.2%" },
  { name: "Detection Rate", current: "78%", proposed: "92%", change: "+14%" },
]

export function StrategyPreview() {
  return (
    <div className="space-y-4">
      <div className="flex items-center space-x-2">
        <Badge variant="outline" className="bg-primary/20">
          Current
        </Badge>
        <Badge variant="outline" className="bg-destructive/20">
          Proposed
        </Badge>
      </div>

      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tickFormatter={(value) => new Date(value).toLocaleDateString()} />
          <YAxis />
          <Tooltip labelFormatter={(value) => new Date(value).toLocaleDateString()} />
          <Legend />
          <Line type="monotone" dataKey="current" stroke="hsl(var(--primary))" strokeWidth={2} name="Current" />
          <Line type="monotone" dataKey="proposed" stroke="hsl(var(--destructive))" strokeWidth={2} name="Proposed" />
        </LineChart>
      </ResponsiveContainer>

      <div className="space-y-2">
        {stats.map((stat) => (
          <div key={stat.name} className="flex items-center justify-between rounded-lg border p-2">
            <span className="font-medium">{stat.name}</span>
            <div className="flex items-center space-x-2">
              <span className="text-sm text-muted-foreground">{stat.current}</span>
              <span className="text-sm">→</span>
              <span className="text-sm font-medium">{stat.proposed}</span>
              <Badge variant={stat.name === "False Positives" ? "destructive" : "secondary"} className="text-xs">
                {stat.change}
              </Badge>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
