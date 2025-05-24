import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

const recentAnomalies = [
  {
    id: "TXN-001",
    account: "ACC-4521",
    amount: "$15,420",
    score: 0.95,
    time: "2 min ago",
  },
  {
    id: "TXN-002",
    account: "ACC-7832",
    amount: "$8,750",
    score: 0.87,
    time: "5 min ago",
  },
  {
    id: "TXN-003",
    account: "ACC-2341",
    amount: "$22,100",
    score: 0.92,
    time: "8 min ago",
  },
]

export function RecentAnomalies() {
  return (
    <div className="space-y-4">
      {recentAnomalies.map((anomaly) => (
        <div key={anomaly.id} className="flex items-center justify-between p-3 border rounded-lg">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className="font-medium">{anomaly.id}</span>
              <Badge variant="outline">{anomaly.account}</Badge>
            </div>
            <div className="text-sm text-muted-foreground">
              {anomaly.amount} • Score: {anomaly.score} • {anomaly.time}
            </div>
          </div>
          <Button size="sm" variant="outline">
            Review
          </Button>
        </div>
      ))}
    </div>
  )
}
