"use client"

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts"

const data = [
  { name: "ACC-4521", anomalies: 35, transactions: 420 },
  { name: "ACC-7832", anomalies: 28, transactions: 380 },
  { name: "ACC-2341", anomalies: 42, transactions: 510 },
  { name: "ACC-6543", anomalies: 15, transactions: 290 },
  { name: "ACC-9876", anomalies: 31, transactions: 450 },
]

export function GroupStatistics() {
  return (
    <ResponsiveContainer width="100%" height={350}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey="anomalies" fill="hsl(var(--destructive))" name="Anomalies" />
        <Bar dataKey="transactions" fill="hsl(var(--primary))" name="Transactions" />
      </BarChart>
    </ResponsiveContainer>
  )
}
