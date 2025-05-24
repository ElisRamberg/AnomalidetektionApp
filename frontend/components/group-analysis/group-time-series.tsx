"use client"

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts"

const data = [
  { date: "2024-01-01", "ACC-4521": 12, "ACC-7832": 8, "ACC-2341": 15 },
  { date: "2024-01-02", "ACC-4521": 8, "ACC-7832": 10, "ACC-2341": 12 },
  { date: "2024-01-03", "ACC-4521": 15, "ACC-7832": 12, "ACC-2341": 8 },
  { date: "2024-01-04", "ACC-4521": 23, "ACC-7832": 18, "ACC-2341": 10 },
  { date: "2024-01-05", "ACC-4521": 18, "ACC-7832": 15, "ACC-2341": 14 },
  { date: "2024-01-06", "ACC-4521": 11, "ACC-7832": 13, "ACC-2341": 17 },
  { date: "2024-01-07", "ACC-4521": 25, "ACC-7832": 20, "ACC-2341": 19 },
]

export function GroupTimeSeries() {
  return (
    <ResponsiveContainer width="100%" height={350}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" tickFormatter={(value) => new Date(value).toLocaleDateString()} />
        <YAxis />
        <Tooltip labelFormatter={(value) => new Date(value).toLocaleDateString()} />
        <Legend />
        <Line type="monotone" dataKey="ACC-4521" stroke="hsl(var(--destructive))" strokeWidth={2} />
        <Line type="monotone" dataKey="ACC-7832" stroke="hsl(var(--primary))" strokeWidth={2} />
        <Line type="monotone" dataKey="ACC-2341" stroke="hsl(var(--secondary))" strokeWidth={2} />
      </LineChart>
    </ResponsiveContainer>
  )
}
