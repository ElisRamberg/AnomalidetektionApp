import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import type { LucideIcon } from "lucide-react"

interface KPICardProps {
  title: string
  value: string
  change: string
  changeType: "increase" | "decrease"
  icon: LucideIcon
  description: string
}

export function KPICard({ title, value, change, changeType, icon: Icon, description }: KPICardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <div className="flex items-center space-x-2 text-xs text-muted-foreground">
          <Badge variant={changeType === "increase" ? "destructive" : "secondary"} className="text-xs">
            {change}
          </Badge>
          <span>{description}</span>
        </div>
      </CardContent>
    </Card>
  )
}
