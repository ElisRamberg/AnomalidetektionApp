import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { GroupFilters } from "@/components/group-analysis/group-filters"
import { GroupStatistics } from "@/components/group-analysis/group-statistics"
import { GroupTimeSeries } from "@/components/group-analysis/group-time-series"

export default function GroupAnalysisPage() {
  return (
    <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">Group Analysis</h2>
      </div>

      <GroupFilters />

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Group Statistics</CardTitle>
            <CardDescription>Anomaly statistics by account and cost center</CardDescription>
          </CardHeader>
          <CardContent>
            <GroupStatistics />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Time Series Analysis</CardTitle>
            <CardDescription>Anomaly trends over time by group</CardDescription>
          </CardHeader>
          <CardContent>
            <GroupTimeSeries />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
