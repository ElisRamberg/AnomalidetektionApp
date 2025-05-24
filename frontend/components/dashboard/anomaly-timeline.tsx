"use client"

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"

const data = [
  { date: "2024-01-01", anomalies: 12, transactions: 45000 },
  { date: "2024-01-02", anomalies: 8, transactions: 42000 },
  { date: "2024-01-03", anomalies: 15, transactions: 48000 },
  { date: "2024-01-04", anomalies: 23, transactions: 51000 },
  { date: "2024-01-05", anomalies: 18, transactions: 47000 },
  { date: "2024-01-06", anomalies: 11, transactions: 44000 },
  { date: "2024-01-07", anomalies: 25, transactions: 53000 },
]

export function AnomalyTimeline() {
  return (
    <ResponsiveContainer width="100%" height={350}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" tickFormatter={(value) => new Date(value).toLocaleDateString()} />
        <YAxis />
        <Tooltip labelFormatter={(value) => new Date(value).toLocaleDateString()} />
        <Line type="monotone" dataKey="anomalies" stroke="hsl(var(--destructive))" strokeWidth={2} name="Anomalies" />
      </LineChart>
    </ResponsiveContainer>
  )
}
