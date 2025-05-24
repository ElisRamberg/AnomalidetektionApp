import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { AlertTriangle, TrendingUp, DollarSign, Activity } from "lucide-react"
import { KPICard } from "@/components/dashboard/kpi-card"
import { AnomalyTimeline } from "@/components/dashboard/anomaly-timeline"
import { RecentAnomalies } from "@/components/dashboard/recent-anomalies"

export default function DashboardPage() {
  return (
    <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">Anomaly Detection Dashboard</h2>
        <div className="flex items-center space-x-2">
          <Badge variant="outline">Last updated: 2 minutes ago</Badge>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KPICard
          title="Flagged Anomalies"
          value="23"
          change="+12%"
          changeType="increase"
          icon={AlertTriangle}
          description="vs. last week"
        />
        <KPICard
          title="Total Transactions"
          value="1,247,892"
          change="+5.2%"
          changeType="increase"
          icon={Activity}
          description="vs. last week"
        />
        <KPICard
          title="Risk Score"
          value="7.2"
          change="-0.8"
          changeType="decrease"
          icon={TrendingUp}
          description="vs. last week"
        />
        <KPICard
          title="Potential Loss"
          value="$45,231"
          change="+23%"
          changeType="increase"
          icon={DollarSign}
          description="vs. last week"
        />
      </div>

      {/* Charts and Timeline */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <Card className="col-span-4">
          <CardHeader>
            <CardTitle>Anomaly Timeline</CardTitle>
            <CardDescription>Anomaly detection over the last 30 days</CardDescription>
          </CardHeader>
          <CardContent className="pl-2">
            <AnomalyTimeline />
          </CardContent>
        </Card>
        <Card className="col-span-3">
          <CardHeader>
            <CardTitle>Recent Anomalies</CardTitle>
            <CardDescription>Latest flagged transactions requiring attention</CardDescription>
          </CardHeader>
          <CardContent>
            <RecentAnomalies />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
