import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { CorrelationHeatmap } from "@/components/correlations/correlation-heatmap"
import { CorrelationFilters } from "@/components/correlations/correlation-filters"

export default function CorrelationsPage() {
  return (
    <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">Account Correlations</h2>
      </div>

      <CorrelationFilters />

      <Card>
        <CardHeader>
          <CardTitle>Correlation Heatmap</CardTitle>
          <CardDescription>Correlation matrix between different accounts</CardDescription>
        </CardHeader>
        <CardContent>
          <CorrelationHeatmap />
        </CardContent>
      </Card>
    </div>
  )
}
